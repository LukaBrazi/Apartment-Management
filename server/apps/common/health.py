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
"""
from __future__ import annotations

import logging

from django.core.cache import cache
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckAPIView(APIView):
    """GET /api/v1/health/ — load balancer liveness/readiness probe."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes: list = []

    def get(self, request, *args, **kwargs) -> Response:
        checks: dict[str, str] = {}
        all_ok = True

        # ── DB ping ───────────────────────────────────────────────────
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["db"] = "ok"
        except Exception as exc:  # noqa: BLE001 — broad catch is intentional
            logger.error("Health check DB failure: %s", exc)
            checks["db"] = "fail"
            all_ok = False

        # ── Cache (Redis) round-trip ─────────────────────────────────
        try:
            cache.set("_healthcheck", "ok", 5)
            if cache.get("_healthcheck") != "ok":
                raise RuntimeError("cache miss after write")
            checks["cache"] = "ok"
        except Exception as exc:  # noqa: BLE001
            logger.error("Health check cache failure: %s", exc)
            checks["cache"] = "fail"
            all_ok = False

        return Response(
            {
                "status": "healthy" if all_ok else "unhealthy",
                "checks": checks,
            },
            status=200 if all_ok else 503,
        )
