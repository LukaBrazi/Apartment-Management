"""GDPR consent endpoints (PR-5).

Two views:

* ``ConsentCreateAPIView`` — ``POST /api/v1/consent/`` records that the
  authenticated user has accepted the latest ToS or Privacy document.
  IP address and User-Agent are pulled off the request server-side so
  the client cannot lie about them.

* ``ConsentMeAPIView`` — ``GET /api/v1/consent/me/`` returns the latest
  ``tos`` / ``privacy`` consent for the current user, each annotated with
  ``current: bool`` (computed against ``settings.TOS_VERSION`` /
  ``settings.PRIVACY_VERSION``) so the frontend ConsentGate can decide
  whether to block UI on a re-accept modal.

The log is append-only: there is no UPDATE / DELETE endpoint by design
(GDPR Art. 7(1) — controllers must be able to demonstrate consent over
time).  Bumping either version setting flips every previous row to
``current=False`` without touching the data.
"""
from __future__ import annotations

from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import ConsentLog
from apps.common.serializers import ConsentCreateSerializer


def _client_ip(request) -> str | None:
    """Best-effort client IP extraction.

    ``X-Forwarded-For`` may carry a comma-separated chain when the request
    has crossed multiple proxies — the left-most entry is the original
    client.  Fall back to ``REMOTE_ADDR`` if the header is absent.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


class ConsentCreateAPIView(generics.CreateAPIView):
    """``POST /api/v1/consent/`` — record a consent acceptance."""

    permission_classes = [IsAuthenticated]
    serializer_class = ConsentCreateSerializer

    def perform_create(self, serializer) -> None:
        serializer.save(
            user=self.request.user,
            ip_address=_client_ip(self.request),
            user_agent=self.request.META.get("HTTP_USER_AGENT", "") or "",
        )


class ConsentMeAPIView(APIView):
    """``GET /api/v1/consent/me/`` — the user's latest ToS + Privacy state."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        latest = {
            ct: ConsentLog.objects
            .filter(user=request.user, consent_type=ct)
            .order_by("-accepted_at")
            .first()
            for ct in (ConsentLog.ConsentType.TOS, ConsentLog.ConsentType.PRIVACY)
        }
        current_versions = {
            ConsentLog.ConsentType.TOS: getattr(settings, "TOS_VERSION", ""),
            ConsentLog.ConsentType.PRIVACY: getattr(settings, "PRIVACY_VERSION", ""),
        }

        def _shape(ct: str):
            log = latest[ct]
            if log is None:
                return None
            return {
                "version": log.version,
                "accepted_at": log.accepted_at.isoformat() if log.accepted_at else None,
                "current": log.version == current_versions[ct],
            }

        # current_versions exposed so the frontend ConsentGate knows which
        # version string to send back in POST /consent/. Without this, the
        # client had to use a "current" sentinel which the server stored
        # verbatim, never matching the configured versions on next GET —
        # the modal would never dismiss. (Hotfix 2026-04-26.)
        return Response(
            {
                "tos": _shape(ConsentLog.ConsentType.TOS),
                "privacy": _shape(ConsentLog.ConsentType.PRIVACY),
                "tos_current_version": current_versions[ConsentLog.ConsentType.TOS],
                "privacy_current_version": current_versions[ConsentLog.ConsentType.PRIVACY],
            },
            status=status.HTTP_200_OK,
        )
