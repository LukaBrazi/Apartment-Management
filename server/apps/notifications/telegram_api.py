"""Sync helpers for Telegram Bot API calls used by the admin UI.

The admin "Test bot" and "Set webhook" actions run inside a sync Django
request/response cycle.  The full ``python-telegram-bot`` client is
async-first (v20+) and driving an event loop from inside an admin view
is awkward — these operations are small REST calls, so we use ``httpx``
directly.

The two functions here are split out (instead of inlined into admin
actions) so the admin layer stays focused on UI concerns and so the
actual HTTP round-trip can be mocked in one place during tests.

Return shape
------------
Both helpers return a :class:`TelegramAPIResult` dataclass with a
boolean ``ok`` and an optional ``error`` string.  Admin actions write
the outcome to ``OrganizationBot.last_test_ok`` / ``last_test_error``,
and use ``error`` verbatim in the admin message banner.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


TELEGRAM_API_BASE = "https://api.telegram.org"
DEFAULT_TIMEOUT = 10.0  # seconds


@dataclass(frozen=True)
class TelegramAPIResult:
    """Outcome of a Telegram Bot API call.

    ``ok`` is True only when the HTTP call succeeded *and* Telegram's
    response body set ``ok: true``.  ``error`` holds a short, human-
    readable message suitable for showing to a super_admin in the
    Django admin; ``data`` is Telegram's ``result`` payload on success.
    """

    ok: bool
    error: str = ""
    data: dict[str, Any] | None = None


def _post(
    bot_token: str, method: str, payload: dict[str, Any] | None = None,
) -> TelegramAPIResult:
    """Call ``https://api.telegram.org/bot<token>/<method>`` with JSON body.

    Wraps all error paths (network failure, bad JSON, Telegram-level
    ``ok: false``) into a single :class:`TelegramAPIResult` so callers
    don't need to care about the layer the failure came from.
    """
    if not bot_token:
        return TelegramAPIResult(ok=False, error="Bot token is empty.")

    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/{method}"
    try:
        resp = httpx.post(url, json=payload or {}, timeout=DEFAULT_TIMEOUT)
    except httpx.HTTPError as exc:
        logger.warning("telegram api %s network error: %s", method, exc)
        return TelegramAPIResult(ok=False, error=f"Network error: {exc}")

    try:
        body = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "telegram api %s: non-JSON response (status=%s)", method, resp.status_code,
        )
        return TelegramAPIResult(
            ok=False, error=f"Non-JSON response (HTTP {resp.status_code}).",
        )

    if not body.get("ok"):
        # Telegram returns helpful error messages here — surface them
        # verbatim to the super_admin so they can fix the token / URL.
        desc = body.get("description") or f"HTTP {resp.status_code}"
        return TelegramAPIResult(ok=False, error=desc, data=body)
    return TelegramAPIResult(ok=True, data=body.get("result") or {})


def get_me(bot_token: str) -> TelegramAPIResult:
    """Call ``getMe`` — the canonical "is this token valid?" check.

    On success ``result.data`` contains Telegram's bot identity:
    ``{"id": ..., "username": ..., "first_name": ..., ...}``.
    The admin action uses ``username`` to verify that what was pasted
    actually matches the configured ``bot_username``.
    """
    return _post(bot_token, "getMe")


def set_webhook(
    bot_token: str, url: str, secret_token: str,
    allowed_updates: list[str] | None = None,
) -> TelegramAPIResult:
    """Register the webhook URL with Telegram for this bot.

    Telegram expects HTTPS on port 443/80/88/8443, a non-empty URL, and
    a secret token of 1–256 chars from ``[A-Za-z0-9_-]``.  The URL is
    what Telegram will POST each update to; the secret is echoed back
    in ``X-Telegram-Bot-Api-Secret-Token`` on every request so our
    webhook view can authenticate Telegram.

    ``allowed_updates`` defaults to ``["message"]`` — we only act on
    ``/start``, ``/stop``, ``/status`` so receiving every update type
    just wastes Telegram's bandwidth.
    """
    payload = {
        "url": url,
        "secret_token": secret_token,
        "allowed_updates": allowed_updates or ["message"],
    }
    return _post(bot_token, "setWebhook", payload)


def delete_webhook(bot_token: str) -> TelegramAPIResult:
    """Clear the webhook — used when flipping back to polling mode.

    Safe to call even when no webhook is set; Telegram returns
    ``ok: true`` either way.
    """
    return _post(bot_token, "deleteWebhook", {"drop_pending_updates": False})
