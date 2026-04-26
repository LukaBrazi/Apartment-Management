"""TDD tests for /api/v1/health/ liveness/readiness probe (PR-7).

The health endpoint serves Railway's deploy gate: a failing probe causes
the platform to roll back to the previous slot. Behaviours under test:

1. Healthy state returns ``200`` and ``"healthy"``.
2. The endpoint requires no auth or session — Railway probes with no
   cookies, so 401/403 here would brick deploys.
3. A DB outage flips the response to ``503`` ``"unhealthy"`` with
   ``checks.db == "fail"``.
4. A cache (Redis) outage does the same with ``checks.cache == "fail"``.
5. The response shape is closed: only the documented keys leak out, no
   DB version / Redis URL / hostname etc.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

HEALTH_URL = "/api/v1/health/"


@pytest.mark.django_db
class TestHealthCheck:
    def test_healthy_returns_200(self):
        client = APIClient()
        response = client.get(HEALTH_URL)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["checks"]["db"] == "ok"
        assert body["checks"]["cache"] == "ok"

    def test_no_authentication_required(self):
        """Probe must work without auth or session — Railway may probe
        before any user has a session cookie."""
        client = APIClient()
        response = client.get(HEALTH_URL)
        assert response.status_code in (200, 503), (
            f"Health endpoint must never return 401/403, got {response.status_code}"
        )

    def test_unhealthy_db_returns_503(self):
        """Patch the health view's DB ping to raise — endpoint must
        report unhealthy + 503.

        Note: we intentionally patch the view's own ``connection`` /
        cursor pathway rather than the global ``django.db.connection``,
        because ATOMIC_REQUESTS opens a savepoint via the same cursor
        before our view code runs and a global mock would crash the
        request inside Django's transaction middleware (yielding a 500,
        not a 503). Patching at the view-module level is the right
        granularity for testing the "DB down → 503" branch.
        """
        from apps.common import health as health_module

        # Build a connection stand-in whose ``cursor()`` context manager
        # raises at __enter__; this matches "Postgres unreachable / no
        # available connection" in production.
        fake_connection = type(
            "FakeBrokenConnection",
            (),
            {"cursor": staticmethod(lambda *a, **kw: (_ for _ in ()).throw(Exception("DB down")))},
        )()

        with patch.object(health_module, "connection", fake_connection):
            client = APIClient()
            response = client.get(HEALTH_URL)
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unhealthy"
        assert body["checks"]["db"] == "fail"

    def test_unhealthy_cache_returns_503(self):
        from django.core.cache import cache

        with patch.object(cache, "set", side_effect=Exception("Redis down")):
            client = APIClient()
            response = client.get(HEALTH_URL)
        assert response.status_code == 503
        assert response.json()["checks"]["cache"] == "fail"

    def test_response_does_not_leak_internals(self):
        """Health response must not leak DB version, Redis URL, etc."""
        client = APIClient()
        response = client.get(HEALTH_URL)
        body = response.json()
        # Whitelist allowed top-level keys.
        assert set(body.keys()) <= {"status", "checks"}, body.keys()
        assert set(body["checks"].keys()) <= {"db", "cache"}, body["checks"].keys()
        # Values are constrained tokens, not free text.
        for v in body["checks"].values():
            assert v in ("ok", "fail"), v
