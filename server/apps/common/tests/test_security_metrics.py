"""TDD for the daily security metrics counters used in the evening TG
digest (PR-18, Phase 2).

The counters tracked:

* ``failed_logins`` — wired via Django's ``user_login_failed`` signal,
  so the same counter fires for failed admin login, DRF basic auth,
  and any custom login views that emit the signal.
* ``throttle_hits`` — incremented by ``SecurityMetricsMiddleware`` on
  any HTTP response with status code 429.
* ``errors_5xx`` — incremented by the same middleware on any response
  with a 500-599 status code.

Storage is the Django cache with day-bucketed keys (``metrics:<name>:<date>``)
and a 48 h TTL — ample room for a same-day read at 21:00 plus next-day
sanity checks.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.signals import user_login_failed
from django.core.cache import cache
from django.http import HttpResponse


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


# ── Counter primitives ──────────────────────────────────────────────────────


class TestCounterPrimitives:
    def test_incr_today_creates_key_and_increments(self):
        from apps.common.security_metrics import incr_today, read_today

        assert read_today("failed_logins") == 0
        incr_today("failed_logins")
        assert read_today("failed_logins") == 1
        incr_today("failed_logins")
        incr_today("failed_logins")
        assert read_today("failed_logins") == 3

    def test_read_today_returns_int_zero_for_missing_key(self):
        from apps.common.security_metrics import read_today

        assert read_today("never_seen") == 0

    def test_incr_today_isolates_between_metrics(self):
        from apps.common.security_metrics import incr_today, read_today

        incr_today("failed_logins")
        incr_today("throttle_hits")
        incr_today("throttle_hits")
        assert read_today("failed_logins") == 1
        assert read_today("throttle_hits") == 2


# ── user_login_failed signal handler ────────────────────────────────────────


class TestFailedLoginSignal:
    def test_signal_fires_increment(self):
        from apps.common.security_metrics import read_today, record_failed_login

        # Direct call (mirrors what the signal would do).
        record_failed_login(sender=None, credentials={"username": "x"}, request=None)
        record_failed_login(sender=None, credentials={"username": "y"}, request=None)
        assert read_today("failed_logins") == 2

    def test_user_login_failed_signal_wired(self):
        """Smoke test that emitting ``user_login_failed`` reaches our counter.

        ``CommonConfig.ready()`` connects the receiver at app-load time, so
        sending the signal here exercises the real wiring.
        """
        from apps.common.security_metrics import read_today

        before = read_today("failed_logins")
        user_login_failed.send(
            sender=__name__,
            credentials={"username": "alice"},
            request=None,
        )
        assert read_today("failed_logins") == before + 1


# ── SecurityMetricsMiddleware ───────────────────────────────────────────────


class TestSecurityMetricsMiddleware:
    def _run(self, status_code: int):
        from apps.common.security_metrics import SecurityMetricsMiddleware

        get_response = MagicMock(return_value=HttpResponse(status=status_code))
        middleware = SecurityMetricsMiddleware(get_response)
        # Plain dummy request — middleware never inspects it on the success path.
        request = MagicMock()
        return middleware(request)

    def test_429_increments_throttle_hits(self):
        from apps.common.security_metrics import read_today

        self._run(429)
        assert read_today("throttle_hits") == 1
        assert read_today("errors_5xx") == 0

    def test_500_increments_errors_5xx(self):
        from apps.common.security_metrics import read_today

        self._run(500)
        assert read_today("errors_5xx") == 1
        assert read_today("throttle_hits") == 0

    def test_503_increments_errors_5xx(self):
        from apps.common.security_metrics import read_today

        self._run(503)
        assert read_today("errors_5xx") == 1

    def test_2xx_3xx_4xx_other_than_429_do_not_increment(self):
        from apps.common.security_metrics import read_today

        for code in (200, 201, 301, 302, 400, 401, 403, 404):
            self._run(code)
        assert read_today("throttle_hits") == 0
        assert read_today("errors_5xx") == 0

    def test_middleware_does_not_break_when_counter_fails(self):
        """Counter exceptions must not bubble up — the request still completes."""
        from apps.common.security_metrics import SecurityMetricsMiddleware

        get_response = MagicMock(return_value=HttpResponse(status=500))
        middleware = SecurityMetricsMiddleware(get_response)
        with patch(
            "apps.common.security_metrics.incr_today",
            side_effect=RuntimeError("boom"),
        ):
            response = middleware(MagicMock())
        assert response.status_code == 500


# ── build_security_digest ───────────────────────────────────────────────────


class TestSecurityDigest:
    def test_returns_today_counts_for_all_three_metrics(self):
        from apps.common.security_metrics import (
            build_security_digest,
            incr_today,
        )

        for _ in range(7):
            incr_today("failed_logins")
        for _ in range(3):
            incr_today("throttle_hits")
        incr_today("errors_5xx")

        digest = build_security_digest()
        assert digest == {
            "failed_logins": 7,
            "throttle_hits": 3,
            "errors_5xx": 1,
        }

    def test_returns_zero_counts_when_no_activity(self):
        from apps.common.security_metrics import build_security_digest

        digest = build_security_digest()
        assert digest == {
            "failed_logins": 0,
            "throttle_hits": 0,
            "errors_5xx": 0,
        }
