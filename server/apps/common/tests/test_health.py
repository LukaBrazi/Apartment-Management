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

    def test_production_settings_exempts_health_from_ssl_redirect(self):
        """Regression: Railway healthcheck probes the container directly via
        plain HTTP. With SECURE_SSL_REDIRECT=True and no exempt, Django's
        SecurityMiddleware redirects to https://, Railway sees a 301 and
        marks the deploy as 'service unavailable'.

        Lock down that ``SECURE_REDIRECT_EXEMPT`` in production.py whitelists
        the health endpoint without requiring us to import production.py
        (which fails in test env because of env-required settings like
        DJANGO_SECRET_KEY, DATABASE_URL, REDIS_URL).
        """
        import re
        from pathlib import Path

        prod_path = (
            Path(__file__).resolve().parents[3]
            / "config"
            / "settings"
            / "production.py"
        )
        src = prod_path.read_text()

        # Extract the SECURE_REDIRECT_EXEMPT list literal.
        match = re.search(
            r"SECURE_REDIRECT_EXEMPT\s*=\s*(\[[^\]]*\])",
            src,
            flags=re.DOTALL,
        )
        assert match, (
            "SECURE_REDIRECT_EXEMPT not configured in production.py — "
            "Railway healthcheck will fail."
        )

        # eval is safe: source comes from our own settings file.
        exempt: list[str] = eval(match.group(1))  # noqa: S307
        assert isinstance(exempt, list) and exempt, "exempt list empty"

        # The path Django gives SecurityMiddleware has no leading slash.
        assert any(re.search(p, "api/v1/health/") for p in exempt), (
            f"Health path 'api/v1/health/' not exempt from SSL redirect. "
            f"Current SECURE_REDIRECT_EXEMPT: {exempt}"
        )
