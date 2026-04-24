"""DRF serializers for the Telegram linking API.

PR-14 phase 3:

* ``GenerateTokenSerializer`` now also surfaces the target org slug so
  the frontend knows which ЖК the token is bound to (relevant for
  users with multiple memberships).
* ``VerifyTokenSerializer`` resolves the token and confirms the bot
  making the call (via ``request.telegram_bot`` set by
  :class:`~apps.notifications.permissions.IsTelegramBot`) is authorised
  for that token's organization.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.notifications.models import (
    OrganizationBot,
    TelegramProfile,
    TelegramVerificationToken,
)


class GenerateTokenSerializer(serializers.Serializer):
    """Response payload for ``POST /generate-token/``."""

    token = serializers.UUIDField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    bot_username = serializers.CharField(read_only=True)
    deep_link = serializers.CharField(read_only=True)
    organization_slug = serializers.CharField(read_only=True)


class VerifyTokenSerializer(serializers.Serializer):
    """Request payload for ``POST /verify/`` — called by the bot.

    ``token`` resolution is done in ``validate_token`` so the view can
    rely on ``context["token_obj"]`` being set. The bot identity was
    already resolved by the permission layer; we just re-expose it
    here as ``context["bot"]`` for the view.
    """

    token = serializers.UUIDField()
    chat_id = serializers.IntegerField()

    def validate_token(self, value):
        try:
            token_obj = (
                TelegramVerificationToken.objects
                .select_related("user", "organization")
                .get(token=value)
            )
        except TelegramVerificationToken.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired token.")
        if not token_obj.is_valid:
            raise serializers.ValidationError(
                "Token has expired or already been used.",
            )
        self.context["token_obj"] = token_obj
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        bot = getattr(request, "telegram_bot", None) if request else None
        if bot is None:
            # Normally the permission layer rejects this earlier, but
            # keep a defensive check so a misconfigured urls.py can't
            # silently let requests slip past.
            raise serializers.ValidationError("Bot not authenticated.")
        self.context["bot"] = bot
        return attrs


class TelegramStatusSerializer(serializers.ModelSerializer):
    """Response for ``GET /status/`` — exposes the binding's public fields."""

    organization_slug = serializers.CharField(
        source="organization.slug", read_only=True,
    )

    class Meta:
        model = TelegramProfile
        fields = [
            "chat_id",
            "is_active",
            "notify_issues",
            "notify_passes",
            "notify_announcements",
            "notify_emergency",
            "notify_visits",
            "telegram_username",
            "organization_slug",
            "created_at",
        ]
        read_only_fields = [
            "chat_id",
            "organization_slug",
            "created_at",
            "telegram_username",
        ]


class TelegramSettingsSerializer(serializers.ModelSerializer):
    """Patch payload for ``PATCH /settings/`` — notification preferences only.

    ``telegram_username`` is intentionally absent: it is derived data written
    by the Telegram bot's ``/start`` handler, not a user preference.  Exposing
    it here would allow clients to spoof their @handle.  The field is surfaced
    *read-only* on ``TelegramStatusSerializer`` for display purposes.
    """

    class Meta:
        model = TelegramProfile
        fields = [
            "notify_issues",
            "notify_passes",
            "notify_announcements",
            "notify_emergency",
            "notify_visits",
        ]


# ── Super-admin OrganizationBot API (PR-14 phase 6) ────────────────────────
#
# The rules of engagement are strict — see views.py::IsSuperAdmin and the
# matching Django-admin policy: ONLY ``is_superuser=True`` may see or
# mutate rows.  These serializers are what that API speaks.
#
# The raw ``bot_token`` is write-only: we never echo it back.  Reads
# receive a masked preview (``bot_id:••••XYZ``) that's safe to show in
# the browser DOM, audit logs, and screenshots.


class OrganizationBotSerializer(serializers.ModelSerializer):
    """Read/write payload for the super_admin OrganizationBot API.

    ``bot_token`` is write-only; on read, ``bot_token_masked`` and
    ``is_configured`` carry enough information for the UI without
    exposing the raw secret.
    """

    # Write-only: the Fernet setter on the model encrypts this before save.
    bot_token = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text=(
            "Paste the token from @BotFather. Leave blank on update to "
            "keep the existing token."
        ),
    )
    bot_token_masked = serializers.CharField(read_only=True)
    is_configured = serializers.BooleanField(read_only=True)
    organization_slug = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    webhook_url = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationBot
        fields = [
            "id",
            "organization",
            "organization_slug",
            "organization_name",
            "bot_username",
            "bot_token",
            "bot_token_masked",
            "is_configured",
            "is_active",
            "is_primary",
            "webhook_url",
            "webhook_secret",
            "last_tested_at",
            "last_test_ok",
            "last_test_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization_slug",
            "organization_name",
            "bot_token_masked",
            "is_configured",
            "webhook_url",
            "webhook_secret",
            "last_tested_at",
            "last_test_ok",
            "last_test_error",
            "created_at",
            "updated_at",
        ]

    def get_organization_slug(self, obj: OrganizationBot) -> str | None:
        return obj.organization.slug if obj.organization_id else None

    def get_organization_name(self, obj: OrganizationBot) -> str | None:
        return obj.organization.name if obj.organization_id else None

    def get_webhook_url(self, obj: OrganizationBot) -> str:
        from django.conf import settings

        base = getattr(settings, "PLATFORM_PUBLIC_URL", "") or ""
        if not base:
            return ""
        return obj.get_webhook_url(base)

    def create(self, validated_data):
        raw = validated_data.pop("bot_token", "") or ""
        instance = OrganizationBot(**validated_data)
        if raw:
            instance.bot_token = raw  # encrypts
        instance.save()
        return instance

    def update(self, instance, validated_data):
        raw = validated_data.pop("bot_token", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if raw:
            instance.bot_token = raw
        instance.save()
        return instance


class OrganizationBotTestResultSerializer(serializers.Serializer):
    """Result of the ``POST /telegram-bots/<id>/test/`` action."""

    ok = serializers.BooleanField(read_only=True)
    error = serializers.CharField(read_only=True, allow_blank=True)
    username = serializers.CharField(read_only=True, allow_blank=True)
