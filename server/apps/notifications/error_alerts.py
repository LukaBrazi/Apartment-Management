"""Telegram error alerts for 5xx exceptions (PR-9).

Cheap-tier replacement for Sentry. Hooks into Django's ``django.request``
logger (where unhandled 5xx exceptions are logged at ERROR level) and
forwards a sanitized one-shot message to a private Telegram channel.

Architecture
------------
- ``TelegramErrorHandler(logging.Handler)`` formats + dedups + dispatches
  via Celery so the request thread is never blocked on the Telegram API.
- Dedup uses a Redis cache key per fingerprint with a 5-minute TTL.
  Fingerprint = sha1 hash of (exception_class, path, message_head).
  During an outage you get ~one message per error type, not 1000.
- PII rules: NEVER include request body, query string, Authorization
  header, Cookie header, or user.email/username. Only user.id.
- Telegram limit is 4096 chars; we cap at 4000 with head+tail traceback
  trimming.

Setup (manual)
--------------
1. @BotFather → /newbot → save TOKEN
2. Create a private Telegram channel
3. Add bot as admin (Send Messages permission)
4. Get chat_id from https://api.telegram.org/bot<TOKEN>/getUpdates
5. Set Railway env vars (Web service AND Celery Worker):
     ERROR_ALERTS_TG_BOT_TOKEN=<token>
     ERROR_ALERTS_TG_CHAT_ID=-100xxxxxxxxxx
6. Without these env vars, the handler silently no-ops (works in dev/CI).

See docs/ERROR_ALERTS_SETUP.md for the step-by-step guide.
"""
from __future__ import annotations

import hashlib
import html
import logging
import traceback
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# ── PII filtering ────────────────────────────────────────────────────────────
# Header names we'd redact if we ever started passing headers around. Kept
# here as a single source of truth — _safe_request_summary deliberately
# does NOT touch headers, but if a future version adds them, redact via
# this set first.
_REDACT_HEADERS = {"authorization", "cookie", "x-api-key", "x-csrftoken"}


def _safe_request_summary(request: Any) -> dict[str, str]:
    """Return a {method, path, user_id} dict — NO body, NO query, NO PII.

    ``request.path`` already strips the query string in Django, so the
    "secret=hunter2" query param never leaks. ``user.id`` only — no email,
    no username, no full_name.
    """
    if request is None:
        return {}
    out: dict[str, str] = {
        "method": getattr(request, "method", "") or "",
        "path": getattr(request, "path", "") or "",  # path = no querystring
    }
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        user_id = getattr(user, "id", None) or getattr(user, "pk", None)
        if user_id is not None:
            out["user_id"] = str(user_id)
    return out


def _fingerprint(record: logging.LogRecord) -> str:
    """Stable hash that groups identical errors. Used to rate-limit alerts.

    Inputs: exception class name + request path + first 100 chars of msg.
    Output: first 16 hex chars of sha1 (collision-safe enough for
    cache-key rate limiting; we don't need cryptographic strength).
    """
    parts: list[str] = []
    if record.exc_info and record.exc_info[0] is not None:
        parts.append(record.exc_info[0].__name__)
    request = getattr(record, "request", None)
    if request is not None:
        parts.append(str(getattr(request, "path", "")))
    parts.append((record.getMessage() or "")[:100])
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _format_traceback(exc_info: Any, max_chars: int = 3500) -> str:
    """Format and trim a traceback for Telegram (head + tail with marker).

    Long Python tracebacks (deep stacks, recursion, big SQL errors) blow
    past Telegram's 4096-char limit. We keep the head (where the user
    code lives) and the tail (where the actual exception fires) and
    drop the middle, which is usually framework noise.
    """
    if not exc_info or exc_info[0] is None:
        return ""
    tb = "".join(traceback.format_exception(*exc_info))
    if len(tb) <= max_chars:
        return tb
    head_size = max_chars // 2
    tail_size = max_chars - head_size - 30  # 30 chars for marker
    return f"{tb[:head_size]}\n\n... [truncated] ...\n\n{tb[-tail_size:]}"


def format_message(record: logging.LogRecord) -> str:
    """Build the Telegram message body (≤4000 chars, HTML-safe).

    Output is HTML-escaped end-to-end — exception messages from
    user-controlled input (URL params, JSON bodies) can contain
    ``<script>`` etc., and Telegram's HTML parse_mode would render those
    if we didn't escape. The 4000-char cap is below Telegram's 4096
    hard limit to leave headroom for any tail-end formatting.
    """
    parts = ["🚨 <b>5xx Production Error</b>", ""]

    summary = _safe_request_summary(getattr(record, "request", None))
    if summary:
        if "method" in summary or "path" in summary:
            parts.append(
                f"<b>Path:</b> {html.escape(summary.get('method', ''))} "
                f"{html.escape(summary.get('path', ''))}"
            )
        if "user_id" in summary:
            parts.append(f"<b>User:</b> id={html.escape(summary['user_id'])}")

    if record.exc_info and record.exc_info[0] is not None:
        parts.append(
            f"<b>Exception:</b> {html.escape(record.exc_info[0].__name__)}",
        )

    msg = (record.getMessage() or "")[:300]
    if msg:
        parts.append(f"<b>Message:</b> {html.escape(msg)}")

    parts.append(f"<b>Fingerprint:</b> <code>{_fingerprint(record)}</code>")

    tb = _format_traceback(record.exc_info)
    if tb:
        parts.append("")
        parts.append(f"<pre>{html.escape(tb)}</pre>")

    text = "\n".join(parts)
    return text[:4000]  # safety cap (Telegram's hard limit is 4096)


# ── Logging handler ──────────────────────────────────────────────────────────


class TelegramErrorHandler(logging.Handler):
    """Forward ERROR-level records (5xx) to a Telegram channel.

    Reads ``ERROR_ALERTS_TG_BOT_TOKEN`` and ``ERROR_ALERTS_TG_CHAT_ID``
    from settings (env-backed). When either is missing/empty, ``emit``
    is a no-op — keeps dev/CI clean without requiring per-environment
    LOGGING overrides.

    The actual HTTP call to Telegram happens in a Celery task so the
    request thread never waits on a third-party API. If the task module
    can't be imported (e.g. during a teardown race), the handler swallows
    the error — a logging handler that crashes Django mid-request is
    worse than a missed alert.
    """

    def __init__(self, level: int = logging.ERROR, dedup_window_sec: int = 300):
        super().__init__(level)
        self.dedup_window_sec = dedup_window_sec

    def emit(self, record: logging.LogRecord) -> None:
        try:
            token = getattr(settings, "ERROR_ALERTS_TG_BOT_TOKEN", "") or ""
            chat_id = getattr(settings, "ERROR_ALERTS_TG_CHAT_ID", "") or ""
            if not token or not chat_id:
                return  # alerts disabled — silent no-op

            fp = _fingerprint(record)
            cache_key = f"error_alert:{fp}"
            if cache.get(cache_key):
                return  # already alerted within dedup_window
            cache.set(cache_key, "1", self.dedup_window_sec)

            text = format_message(record)

            # Async via Celery — never block the request thread on a
            # third-party HTTP call. ``send_telegram_error_alert_task``
            # is bound at module level (see import below) so tests can
            # patch ``apps.notifications.error_alerts.send_telegram_error_alert_task``
            # without reaching into the tasks module.
            send_telegram_error_alert_task.delay(text)
        except Exception:  # noqa: BLE001 — handler must never raise
            self.handleError(record)


# Module-level binding for the Celery task used by the handler.
# Imported at the bottom to side-step the circular import between
# error_alerts (handler) and tasks (which imports nothing from this
# module). Bound at module level so tests can patch this name directly.
from apps.notifications.tasks import send_telegram_error_alert_task  # noqa: E402
