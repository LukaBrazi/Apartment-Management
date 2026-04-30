"""Daily security counters used in the evening TG digest (PR-18).

Three buckets are tracked:

* ``failed_logins`` — bumped from the
  ``django.contrib.auth.signals.user_login_failed`` signal so admin,
  DRF basic auth, and any custom login view that emits the signal all
  funnel into the same counter.
* ``throttle_hits`` — bumped by :class:`SecurityMetricsMiddleware` on
  any HTTP response with status 429.
* ``errors_5xx`` — bumped by the same middleware on any 500-599 response.

Storage: Django cache (Redis in prod, LocMem in tests). Keys are
day-bucketed (``metrics:<name>:YYYY-MM-DD``) with a 48 h TTL — long
enough that the 21:00 read still has today's data, plus one day of
slack for retries / clock-skew. Yesterday's bucket falls off the cache
naturally; we never need to roll over by hand.

The middleware never raises — counter failures are swallowed so a
broken Redis won't take down request handling.
"""
from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

DAY_FORMAT = "%Y-%m-%d"
TTL_SECONDS = 48 * 3600  # 48h — covers same-day reads + slight clock skew

# Public metric names — shared with the digest builder.
METRIC_FAILED_LOGINS = "failed_logins"
METRIC_THROTTLE_HITS = "throttle_hits"
METRIC_ERRORS_5XX = "errors_5xx"


def _today_key(metric: str) -> str:
    today = timezone.localdate().strftime(DAY_FORMAT)
    return f"metrics:{metric}:{today}"


def incr_today(metric: str) -> None:
    """Increment today's bucket for ``metric``. Creates the key if missing.

    ``cache.incr`` raises ``ValueError`` when the key does not exist;
    we fall back to ``cache.set(..., 1)`` in that case so the first
    write of the day still lands.
    """
    key = _today_key(metric)
    try:
        cache.incr(key)
    except ValueError:
        # First write of the day — seed with 1 + TTL.
        cache.set(key, 1, TTL_SECONDS)


def read_today(metric: str) -> int:
    """Return today's bucket count (``0`` if missing)."""
    return int(cache.get(_today_key(metric)) or 0)


# ── Signal handler ──────────────────────────────────────────────────────────


def record_failed_login(sender: Any, credentials: Any, request: Any, **kwargs) -> None:
    """Receiver for ``django.contrib.auth.signals.user_login_failed``.

    Connected in ``apps.common.apps.CommonConfig.ready()`` at app-load
    time. We never log the credentials — Django itself avoids leaking
    them and so do we.
    """
    incr_today(METRIC_FAILED_LOGINS)


# ── Digest builder ──────────────────────────────────────────────────────────


def build_security_digest() -> dict:
    """Return today's security snapshot for the evening TG digest.

    Returns
    -------
    dict
        ``{"failed_logins": int, "throttle_hits": int, "errors_5xx": int}``
    """
    return {
        METRIC_FAILED_LOGINS: read_today(METRIC_FAILED_LOGINS),
        METRIC_THROTTLE_HITS: read_today(METRIC_THROTTLE_HITS),
        METRIC_ERRORS_5XX: read_today(METRIC_ERRORS_5XX),
    }


# ── Middleware ──────────────────────────────────────────────────────────────


class SecurityMetricsMiddleware:
    """Increment the rate-limit / 5xx counters once per request.

    Lightweight — only inspects ``response.status_code`` after the view
    has run. Any failure inside the counter path is swallowed so a
    flaky cache backend can't return a 500 to a healthy view.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            status = getattr(response, "status_code", None)
            if status == 429:
                incr_today(METRIC_THROTTLE_HITS)
            elif status is not None and 500 <= status < 600:
                incr_today(METRIC_ERRORS_5XX)
        except Exception as exc:  # noqa: BLE001
            logger.warning("security_metrics middleware failed: %s", exc)
        return response
