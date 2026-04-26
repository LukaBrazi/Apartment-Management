"""TDD: password reset endpoint must be rate-limited per settings (PR-7).

Background
----------
``settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`` defines the rate
``"password_reset": "3/hour"`` but until PR-7 no view actually bound that
scope, so the rate sat dead and the endpoint was vulnerable to email
bombing / user enumeration. The fix routes ``/auth/users/reset_password/``
and ``/auth/users/reset_password_confirm/`` through a Djoser
``UserViewSet`` subclass that applies ``ScopedRateThrottle`` for the
``password_reset`` scope on those two actions only.

Test settings disable throttling globally (``test.py`` overrides
``DEFAULT_THROTTLE_CLASSES`` and ``DEFAULT_THROTTLE_RATES`` to empty).
DRF caches its api_settings on import, so ``override_settings`` alone
does not flush them — we additionally call
``rest_framework.settings.api_settings.reload`` via the
``setting_changed`` signal which DRF listens to. This is the
canonical pattern from DRF's own test suite.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
import pytest
from rest_framework.settings import api_settings
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def reset_throttle_cache():
    """Clear DRF's throttle counters before AND after the test.

    DRF's SimpleRateThrottle stores per-scope counters in the default
    cache. Test isolation requires wiping them so previous tests can't
    burn through the 3/hour budget before we even start.
    """
    cache.clear()
    yield
    cache.clear()


_THROTTLED_REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.common.cookie_auth.CookieAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "1000/day",
        "user": "1000/day",
        "password_reset": "3/hour",
    },
}


@pytest.mark.django_db
class TestPasswordResetThrottle:
    """Rate-limit contract for /api/v1/auth/users/reset_password/."""

    URL = "/api/v1/auth/users/reset_password/"

    def test_throttle_scope_attached_to_view(self):
        """Sanity: the subclass binds ``password_reset`` scope on the
        right action and uses ``ScopedRateThrottle``.

        This catches regressions where the override is silently dropped
        — even if the integration test below stops running, this check
        keeps the contract pinned at unit level.
        """
        from rest_framework.throttling import ScopedRateThrottle

        from apps.users.views import ThrottledPasswordResetUserViewSet

        view = ThrottledPasswordResetUserViewSet()
        view.action = "reset_password"
        throttles = view.get_throttles()
        assert any(isinstance(t, ScopedRateThrottle) for t in throttles)
        assert view.throttle_scope == "password_reset"

        view2 = ThrottledPasswordResetUserViewSet()
        view2.action = "reset_password_confirm"
        throttles2 = view2.get_throttles()
        assert any(isinstance(t, ScopedRateThrottle) for t in throttles2)

    def test_password_reset_returns_429_after_third_request(
        self, reset_throttle_cache
    ):
        """4th POST inside the same hour must hit the 3/hour cap."""
        # User existence does not matter — Djoser intentionally returns
        # 204 even for unknown emails to avoid leaking which addresses
        # are registered. The throttle fires on the *attempt*, not the
        # outcome.
        User.objects.create_user(
            email="reset-target@example.com",
            username="resetuser",
            first_name="Reset",
            last_name="User",
            password="StrongPwd123!",
        )

        # ``SimpleRateThrottle.THROTTLE_RATES`` is a class-level attribute
        # populated at import time from ``api_settings.DEFAULT_THROTTLE_RATES``.
        # ``override_settings`` does not retro-patch it because the class
        # body has already executed. The pragmatic, surgical fix used by
        # DRF's own test suite is to patch the dict in place for the
        # duration of the test.
        from rest_framework.throttling import SimpleRateThrottle

        original_rates = dict(SimpleRateThrottle.THROTTLE_RATES)
        SimpleRateThrottle.THROTTLE_RATES = {
            **original_rates,
            "password_reset": "3/hour",
        }
        try:
            with override_settings(REST_FRAMEWORK=_THROTTLED_REST_FRAMEWORK):
                api_settings.reload()
                client = APIClient()
                statuses = []
                for _ in range(4):
                    resp = client.post(
                        self.URL,
                        {"email": "reset-target@example.com"},
                        format="json",
                    )
                    statuses.append(resp.status_code)
        finally:
            SimpleRateThrottle.THROTTLE_RATES = original_rates
            api_settings.reload()

        # Djoser returns 204 on success (or 400 if email is mandatory and
        # missing — not our case). The 4th call must be 429.
        assert statuses[3] == 429, (
            f"Expected 4th request to be throttled (429), got {statuses}"
        )
        # First three may legitimately be 204 / 400 / 200 depending on
        # Djoser version, but never 429.
        assert all(s != 429 for s in statuses[:3]), (
            f"None of the first 3 requests should be throttled, got {statuses}"
        )
