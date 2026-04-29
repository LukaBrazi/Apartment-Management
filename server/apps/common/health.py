"""Health check endpoint for load balancer probes (PR-7 Quick Wins).

Returns 200 if the app is healthy, 503 if any critical dependency is
down. Both DB and cache (Redis) are critical — a failure of either
flips the response to 503 so Railway's deploy gate rolls back.

Notes
-----
- ``AllowAny`` + ``authentication_classes = []`` so Railway can probe
  before any user has a session/cookies. We also explicitly set
  ``throttle_classes = []`` because login throttle (5/min anon by IP)
  would otherwise lock out a chatty load balancer.
- Cache check writes a short-lived key (5s TTL) and reads it back —
  failure to round-trip indicates Redis is unavailable.
- Response shape is fixed and minimal; we never expose DB version or
  Redis URL — info leakage / fingerprinting risk for an unauthenticated
  endpoint.
- Errors from dependency probes are caught broadly (``Exception``)
  because we don't care which specific exception fired — what matters
  is that the dependency is reporting unhealthy.

PR-10 refactor
--------------
The DB+cache probe logic was extracted into :func:`run_health_checks`
so scheduled monitoring tasks (``apps.common.tasks.daily_health_status_task``
and ``hourly_health_monitor_task``) reuse the EXACT same checks the
load balancer probe runs. One source of truth for "what does healthy
mean" — when we add a new dependency probe, both the HTTP endpoint
AND the Telegram health pings pick it up automatically.
"""
from __future__ import annotations

import logging

from django.core.cache import cache
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def run_health_checks() -> dict[str, str]:
    """Run DB + cache pings. Returns ``{"db": "ok"|"fail", "cache": "ok"|"fail"}``.

    Reusable by both the HTTP health endpoint (Railway probe) and
    scheduled health monitoring tasks (Telegram pings). Never raises —
    failures are logged and surface as ``"fail"`` in the returned dict.
    """
    checks: dict[str, str] = {}

    # ── DB ping ──────────────────────────────────────────────────────────
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["db"] = "ok"
    except Exception as exc:  # noqa: BLE001 — broad catch is intentional
        logger.error("Health check DB failure: %s", exc)
        checks["db"] = "fail"

    # ── Cache (Redis) round-trip ────────────────────────────────────────
    try:
        cache.set("_healthcheck", "ok", 5)
        if cache.get("_healthcheck") != "ok":
            raise RuntimeError("cache miss after write")
        checks["cache"] = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.error("Health check cache failure: %s", exc)
        checks["cache"] = "fail"

    return checks


class HealthCheckAPIView(APIView):
    """GET /api/v1/health/ — load balancer liveness/readiness probe."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes: list = []

    def get(self, request, *args, **kwargs) -> Response:
        checks = run_health_checks()
        all_ok = all(v == "ok" for v in checks.values())
        return Response(
            {
                "status": "healthy" if all_ok else "unhealthy",
                "checks": checks,
            },
            status=200 if all_ok else 503,
        )
