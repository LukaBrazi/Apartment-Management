"""Serializers for the common app — currently scoped to GDPR consent (PR-5).

ConsentCreateSerializer is the input contract for ``POST /api/v1/consent/``.
The view layer is responsible for stamping ``user``, ``ip_address`` and
``user_agent`` from the request — the client cannot spoof them.
"""
from rest_framework import serializers

from apps.common.models import ConsentLog


class ConsentCreateSerializer(serializers.ModelSerializer):
    """Validates consent payload and creates an immutable ConsentLog row.

    Accepts ``consent_type`` (must be one of ConsentLog.ConsentType.choices)
    and ``version`` (non-empty string).  Everything else (user, ip, ua) is
    injected by ``ConsentCreateAPIView.perform_create``.
    """

    consent_type = serializers.ChoiceField(choices=ConsentLog.ConsentType.choices)
    version = serializers.CharField(max_length=20, allow_blank=False)

    class Meta:
        model = ConsentLog
        fields = ("consent_type", "version")
