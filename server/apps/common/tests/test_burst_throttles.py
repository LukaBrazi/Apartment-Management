"""TDD: per-endpoint burst rate limits on write APIs (PR-8).

Background
----------
PR-8 introduces four new ``ScopedRateThrottle`` scopes — ``issue_create``,
``pass_create``, ``post_create``, ``rating_create`` — that sit on top of
the global ``user: 500/day`` ceiling.  They cap how fast a single
account can create the matching resource even if it has plenty of daily
budget left, so a compromised cookie can't be used to spam-create
issues / passes / posts / ratings.

Three of the four endpoints are pure ``CreateAPIView`` views and use the
stock ``ScopedRateThrottle``.  The fourth — ``VehiclePassListCreateAPIView``
— is a mixed read+write view, so it uses the
``WriteOnlyScopedThrottle`` from ``apps.common.throttles``: GETs are NOT
throttled (badge counters call this endpoint constantly), only POSTs.

Test mechanics
--------------
``settings.test`` deliberately disables throttling project-wide so the
existing 779 tests don't trip the global cap.  We re-enable it
narrowly with the same pattern PR-7's ``test_password_reset_throttle``
established:

  * ``override_settings(REST_FRAMEWORK=…)`` to turn on the right
    classes + rates;
  * ``api_settings.reload()`` to flush DRF's import-time cache;
  * monkey-patch ``SimpleRateThrottle.THROTTLE_RATES`` in place because
    that dict is populated once at class-body time and ``override_settings``
    doesn't retroactively rebuild it;
  * ``cache.clear()`` before each test to wipe stale counters from
    previous tests in the same module.

Each test sends ``limit + 1`` requests of the appropriate kind and
asserts that the last one is ``429`` while the first ``limit`` are not.
We deliberately avoid asserting an exact 2xx code on the first N
requests — the underlying serializers may legitimately return 400 on
test data we haven't fully wired up; the only contract we care about is
"throttle fires at the right count".
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.settings import api_settings
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

User = get_user_model()


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
    # Generous ``user`` budget so we stop on the scoped cap, not on it.
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10000/day",
        "user": "10000/day",
        "issue_create": "20/hour",
        "pass_create": "30/hour",
        "post_create": "10/hour",
        "rating_create": "30/hour",
    },
}

_NEW_RATES = {
    # ``SimpleRateThrottle.__init__`` reads ``THROTTLE_RATES`` even for
    # the global ``anon`` / ``user`` scopes — without these the test
    # crashes at view-construction time before our scope ever fires.
    "anon": "10000/day",
    "user": "10000/day",
    "issue_create": "20/hour",
    "pass_create": "30/hour",
    "post_create": "10/hour",
    "rating_create": "30/hour",
}


@pytest.fixture
def reset_throttle_cache():
    """Clear DRF's throttle counters before AND after the test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def patched_rates():
    """Patch ``SimpleRateThrottle.THROTTLE_RATES`` in place.

    Same pattern as ``test_password_reset_throttle`` — the dict is
    populated at class-body import time and never re-read, so plain
    ``override_settings`` is not enough.
    """
    original = dict(SimpleRateThrottle.THROTTLE_RATES)
    SimpleRateThrottle.THROTTLE_RATES = {**original, **_NEW_RATES}
    try:
        with override_settings(REST_FRAMEWORK=_THROTTLED_REST_FRAMEWORK):
            api_settings.reload()
            yield
    finally:
        SimpleRateThrottle.THROTTLE_RATES = original
        api_settings.reload()


def _make_authed_client(user):
    """Force-authenticate so we don't burn login throttle budgets."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_issue_create_throttled_after_20_per_hour(reset_throttle_cache, patched_rates):
    """21st POST to ``/issues/create/`` within an hour returns 429.

    The first 20 may legitimately be 400/403/404 etc. (we're not
    plumbing valid Issue payloads through the serializer here) but the
    21st must be the throttle response, not whatever the view would
    otherwise have returned.
    """
    user = User.objects.create_user(
        email="issuer@example.com",
        username="issuer",
        first_name="Iss",
        last_name="Uer",
        password="Secret123!",
    )
    client = _make_authed_client(user)
    url = reverse("create-issue-default")

    statuses = []
    for _ in range(21):
        resp = client.post(url, {"title": "x", "description": "y"}, format="json")
        statuses.append(resp.status_code)

    assert statuses[20] == 429, (
        f"Expected 21st request to be throttled, got {statuses}"
    )
    assert all(s != 429 for s in statuses[:20]), (
        f"First 20 requests should not be throttled, got {statuses}"
    )


@pytest.mark.django_db
def test_pass_create_throttled_after_30_per_hour(reset_throttle_cache, patched_rates):
    """31st POST to ``/passes/`` within an hour returns 429.

    GETs to the same endpoint must NOT consume the budget — they are
    used by the badge counter on every page load.
    """
    user = User.objects.create_user(
        email="passer@example.com",
        username="passer",
        first_name="Pas",
        last_name="Ser",
        password="Secret123!",
    )
    client = _make_authed_client(user)
    url = reverse("vehicle-pass-list-create")

    # 50 GETs first — none of these should burn the pass_create budget.
    for _ in range(50):
        client.get(url)

    statuses = []
    for _ in range(31):
        resp = client.post(url, {}, format="json")
        statuses.append(resp.status_code)

    assert statuses[30] == 429, (
        f"Expected 31st POST to be throttled, got {statuses}"
    )
    assert all(s != 429 for s in statuses[:30]), (
        f"First 30 POSTs should not be throttled, got {statuses}"
    )


@pytest.mark.django_db
def test_post_create_throttled_after_10_per_hour(reset_throttle_cache, patched_rates):
    """11th POST to ``/posts/create/`` within an hour returns 429."""
    user = User.objects.create_user(
        email="poster@example.com",
        username="poster",
        first_name="Pos",
        last_name="Ter",
        password="Secret123!",
    )
    client = _make_authed_client(user)
    url = reverse("create-post")

    statuses = []
    for _ in range(11):
        resp = client.post(url, {"body": "x"}, format="json")
        statuses.append(resp.status_code)

    assert statuses[10] == 429, (
        f"Expected 11th request to be throttled, got {statuses}"
    )
    assert all(s != 429 for s in statuses[:10]), (
        f"First 10 requests should not be throttled, got {statuses}"
    )


@pytest.mark.django_db
def test_rating_create_throttled_after_30_per_hour(reset_throttle_cache, patched_rates):
    """31st POST to ``/ratings/create/`` within an hour returns 429."""
    user = User.objects.create_user(
        email="rater@example.com",
        username="rater",
        first_name="Rat",
        last_name="Er",
        password="Secret123!",
    )
    client = _make_authed_client(user)
    url = reverse("create-rating")

    statuses = []
    for _ in range(31):
        resp = client.post(
            url,
            {"rated_user_username": "nobody", "rating": 5},
            format="json",
        )
        statuses.append(resp.status_code)

    assert statuses[30] == 429, (
        f"Expected 31st request to be throttled, got {statuses}"
    )
    assert all(s != 429 for s in statuses[:30]), (
        f"First 30 requests should not be throttled, got {statuses}"
    )
