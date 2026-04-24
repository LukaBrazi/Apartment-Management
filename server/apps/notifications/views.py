"""HTTP endpoints for the user-side Telegram linking flow.

PR-14 phase 3 rewire:

* ``GenerateTokenView`` now derives the target org from the caller and
  returns a deep link that points at that org's bot username (no more
  global ``TELEGRAM_BOT_USERNAME`` setting).
* ``VerifyTokenView`` (called by the bot) must confirm the token's org
  matches the bot's org before creating the profile, so a token minted
  in org A can't be redeemed against org B.
* The status / disconnect / settings endpoints are now scoped by a
  ``?organization=<slug>`` query arg; callers that omit it get the
  user's primary org's binding. Multi-org users pass the slug
  explicitly.
"""
from __future__ import annotations

import hmac
import logging

from django.conf import settings
from django.utils import timezone

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.bot_resolver import (
    TELEGRAM_FEATURE_FLAG,
    get_bot_for_org,
    resolve_org_from_user_and_context,
)
from apps.notifications.models import (
    OrganizationBot,
    TelegramProfile,
    TelegramVerificationToken,
)
from apps.notifications.permissions import IsTelegramBot
from apps.notifications.serializers import (
    GenerateTokenSerializer,
    OrganizationBotSerializer,
    OrganizationBotTestResultSerializer,
    TelegramSettingsSerializer,
    TelegramStatusSerializer,
    VerifyTokenSerializer,
)
from apps.notifications.telegram_api import (
    delete_webhook as tg_delete_webhook,
    get_me as tg_get_me,
    set_webhook as tg_set_webhook,
)
from apps.notifications.update_handlers import handle_webhook_update
from apps.organizations.models import Organization
from apps.organizations.utils import get_user_primary_organization

logger = logging.getLogger(__name__)


def _resolve_org_from_request(request) -> Organization:
    """Pick the org for a per-user endpoint.

    Resolution order:
      1. ``?organization=<slug>`` query param — explicit, for multi-org
         users. Must be an org the caller is actually a member of;
         otherwise 404.
      2. The caller's primary (first active) organization membership.

    Raises ``NotFound`` if neither yields an org — callers are
    expected to show a "link your Telegram from within a ЖК context"
    error in the UI, which is the correct UX for dangling accounts.
    """
    slug = request.query_params.get("organization")
    if slug:
        try:
            org = Organization.objects.get(slug=slug)
        except Organization.DoesNotExist:
            raise NotFound("Organization not found.")
        is_member = request.user.organization_memberships.filter(
            organization=org, is_active=True,
        ).exists()
        if not (is_member or request.user.is_superuser):
            raise NotFound("Organization not found.")
        return org

    org = get_user_primary_organization(request.user)
    if org is None:
        raise NotFound("No active organization membership.")
    return org


class GenerateTokenView(APIView):
    """Generate a one-time verification token bound to a target org."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        org = _resolve_org_from_request(request)
        bot = get_bot_for_org(org)
        if bot is None:
            # Feature is off for this org, or super_admin hasn't set up
            # a bot yet. Don't mint a token the user can't redeem.
            raise ValidationError(
                "Telegram is not configured for this organization.",
            )

        # Invalidate any prior unused token for this (user, org) pair.
        TelegramVerificationToken.objects.filter(
            user=request.user, organization=org, is_used=False,
        ).delete()

        token_obj = TelegramVerificationToken.objects.create(
            user=request.user, organization=org,
        )
        deep_link = f"https://t.me/{bot.bot_username}?start={token_obj.token}"

        data = {
            "token": token_obj.token,
            "expires_at": token_obj.expires_at,
            "bot_username": bot.bot_username,
            "deep_link": deep_link,
            "organization_slug": org.slug,
        }
        serializer = GenerateTokenSerializer(data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VerifyTokenView(APIView):
    """Called by the Telegram bot to verify a token and bind chat_id→user.

    The bot passes ``bot_id`` (its own ``OrganizationBot.id``) in the
    payload. We check that the token's ``organization_id`` matches the
    bot's ``organization_id`` and refuse the exchange otherwise — this
    is what makes cross-tenant hijack structurally impossible.
    """

    permission_classes = [IsTelegramBot]

    def post(self, request):
        serializer = VerifyTokenSerializer(
            data=request.data, context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        token_obj = serializer.context["token_obj"]
        bot = serializer.context["bot"]
        chat_id = serializer.validated_data["chat_id"]

        if token_obj.organization_id != bot.organization_id:
            # Someone tried to redeem org A's token against org B's bot.
            # Treat it as invalid — same response as a bad token so
            # attackers learn nothing from the differential.
            raise ValidationError(
                {"token": "Invalid or expired token."},
            )

        token_obj.is_used = True
        token_obj.save(update_fields=["is_used"])

        profile, created = TelegramProfile.objects.get_or_create(
            user=token_obj.user,
            organization=token_obj.organization,
            defaults={"chat_id": chat_id, "is_active": True},
        )
        if not created:
            profile.chat_id = chat_id
            profile.is_active = True
            profile.save(update_fields=["chat_id", "is_active"])

        return Response(
            {"detail": "Telegram connected successfully.", "created": created},
            status=status.HTTP_200_OK,
        )


class TelegramStatusView(generics.RetrieveAPIView):
    """Return the Telegram link status for (caller, org)."""

    permission_classes = [IsAuthenticated]
    serializer_class = TelegramStatusSerializer

    def retrieve(self, request, *args, **kwargs):
        org = _resolve_org_from_request(request)
        feature_enabled = org.is_feature_enabled(TELEGRAM_FEATURE_FLAG)
        bot = get_bot_for_org(org)
        bot_configured = bot is not None

        profile = TelegramProfile.objects.filter(
            user=request.user, organization=org,
        ).first()

        base = {
            "feature_enabled": feature_enabled,
            "bot_configured": bot_configured,
        }

        if profile is None:
            return Response({"connected": False, **base}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(profile)
        return Response({"connected": True, **base, **serializer.data})


class TelegramDisconnectView(APIView):
    """Deactivate the caller's TelegramProfile for the target org."""

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        org = _resolve_org_from_request(request)
        profile = TelegramProfile.objects.filter(
            user=request.user, organization=org,
        ).first()
        if profile is None:
            return Response(
                {"detail": "No Telegram profile found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        profile.is_active = False
        profile.save(update_fields=["is_active"])
        return Response(
            {"detail": "Telegram disconnected."},
            status=status.HTTP_200_OK,
        )


class TelegramSettingsView(generics.UpdateAPIView):
    """Update notification preferences on the (caller, org) profile."""

    permission_classes = [IsAuthenticated]
    serializer_class = TelegramSettingsSerializer
    http_method_names = ["patch"]

    def get_object(self):
        org = _resolve_org_from_request(self.request)
        profile = TelegramProfile.objects.filter(
            user=self.request.user, organization=org,
        ).first()
        if profile is None:
            raise NotFound("Telegram not connected.")
        return profile


# ── Per-org webhook endpoint ───────────────────────────────────────────────


class TelegramWebhookView(APIView):
    """Endpoint Telegram POSTs incoming updates to, per organization.

    URL shape: ``POST /api/v1/notifications/telegram/webhook/<org_slug>/``

    Authentication is by shared secret: Telegram includes the value we
    passed to ``setWebhook(secret_token=…)`` in the
    ``X-Telegram-Bot-Api-Secret-Token`` header on every update. We
    compare it to ``OrganizationBot.webhook_secret`` with
    ``hmac.compare_digest`` (constant-time). A missing, malformed, or
    wrong secret returns 403 with an opaque body — we don't leak
    whether the org slug existed or not, so scanners can't enumerate.

    Reply delivery: handler returns text; we push it back through
    ``send_message_sync`` using the bot's own token. Errors there are
    logged but do *not* surface to Telegram — we always return 200 on a
    valid request so Telegram doesn't retry us and pile up.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request, org_slug: str):
        if org_slug == "default":
            bot = (
                OrganizationBot.objects
                .filter(organization__isnull=True, is_default=True, is_active=True)
                .first()
            )
            if bot is None:
                return Response(status=status.HTTP_403_FORBIDDEN)
            # Use a sentinel for logging — there is no org slug to reference.
            _log_slug = "default"
        else:
            try:
                org = Organization.objects.get(slug=org_slug)
            except Organization.DoesNotExist:
                # Same response shape as the secret-mismatch branch — no
                # "this org doesn't exist" vs "wrong secret" differential.
                return Response(status=status.HTTP_403_FORBIDDEN)

            bot = (
                OrganizationBot.objects
                .filter(organization=org, is_primary=True, is_active=True)
                .first()
            )
            if bot is None:
                return Response(status=status.HTTP_403_FORBIDDEN)
            _log_slug = org_slug

        got_secret = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token", "",
        )
        if not (
            bot.webhook_secret
            and hmac.compare_digest(bot.webhook_secret, got_secret)
        ):
            logger.warning(
                "telegram webhook: bad secret for org=%s", _log_slug,
            )
            return Response(status=status.HTTP_403_FORBIDDEN)

        # Handle the update in-process. The handler layer does its own
        # ORM work and returns the reply text (or None for non-commands).
        try:
            result = handle_webhook_update(bot, request.data or {})
        except Exception:  # noqa: BLE001
            # Keep Telegram happy — if our handler blows up, log and
            # move on rather than sending a 500 that Telegram will
            # retry forever. The ops team gets the traceback.
            logger.exception(
                "telegram webhook: handler crash (org=%s)", _log_slug,
            )
            return Response(status=status.HTTP_200_OK)

        if result is not None:
            chat = (
                (request.data or {}).get("message")
                or (request.data or {}).get("edited_message")
                or {}
            ).get("chat") or {}
            chat_id = chat.get("id")
            if chat_id is not None:
                # Deferred import — keeps this module importable on
                # workers without python-telegram-bot installed.
                from apps.notifications.utils import send_message_sync

                try:
                    send_message_sync(
                        chat_id, result.reply_text, bot.bot_token,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "telegram webhook: reply send failed "
                        "(org=%s, chat_id=%s)", _log_slug, chat_id,
                    )

        return Response(status=status.HTTP_200_OK)


# ── Super-admin REST API for OrganizationBot (PR-14 phase 6) ──────────────
#
# Mirrors the Django admin's policy: only ``is_superuser=True`` callers
# may list, create, update, or act on these rows.  The frontend page
# at ``/admin/telegram-bot`` hits this API; the stricter Django admin
# remains available for incident recovery.


class IsSuperAdmin(BasePermission):
    """Allow only ``request.user.is_superuser``.

    The platform's role vocabulary calls this "super_admin".  Named
    here so the intent is explicit at every ``permission_classes = [
    IsSuperAdmin]`` site — reading it as ``IsAuthenticated`` at a
    glance would hide the restriction.
    """

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )


class OrganizationBotViewSet(viewsets.ModelViewSet):
    """CRUD + action endpoints for ``OrganizationBot`` (super_admin only).

    Routes provided:
      * ``GET    /api/v1/notifications/telegram-bots/``             — list
      * ``POST   /api/v1/notifications/telegram-bots/``             — create
      * ``GET    /api/v1/notifications/telegram-bots/<id>/``        — retrieve
      * ``PATCH  /api/v1/notifications/telegram-bots/<id>/``        — update
      * ``DELETE /api/v1/notifications/telegram-bots/<id>/``        — destroy
      * ``POST   /api/v1/notifications/telegram-bots/<id>/test/``   — getMe
      * ``POST   /api/v1/notifications/telegram-bots/<id>/set_webhook/``
      * ``POST   /api/v1/notifications/telegram-bots/<id>/delete_webhook/``

    Look up by the model's UUID ``id`` (not the autoincrement pkid) so
    URLs aren't guessable and don't leak row order.
    """

    queryset = OrganizationBot.objects.select_related("organization").all()
    serializer_class = OrganizationBotSerializer
    permission_classes = [IsSuperAdmin]
    lookup_field = "id"

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"], url_path="organizations")
    def organizations(self, request):
        """Return a minimal list of orgs for the create/edit dropdown.

        The super_admin UI needs ``{pkid, name, slug, is_active}`` per
        org to populate the ``organization`` picker when adding a new
        bot.  We ship this as an action on the bot viewset rather than
        reusing ``/api/v1/orgs/organizations/`` so the frontend only
        needs a single permission check (IsSuperAdmin) and a single
        cache tag (TelegramBot-adjacent), and so we don't have to
        touch the renderer shape on the orgs viewset.
        """
        orgs = Organization.objects.all().order_by("name").values(
            "pkid", "id", "name", "slug", "is_active",
        )
        return Response(list(orgs))

    @action(detail=True, methods=["post"])
    def test(self, request, id=None):
        """Call ``getMe`` and record the outcome on the row.

        Also checks that the returned ``username`` matches what's
        stored on the row — a common super_admin mistake is pasting a
        token from a different bot.  Mismatch is reported as a
        failure so the UI doesn't confidently show "OK" for a
        misconfiguration.
        """
        bot = self.get_object()
        try:
            token = bot.bot_token
        except Exception as exc:  # noqa: BLE001
            payload = {
                "ok": False,
                "error": f"Token could not be decrypted: {exc}",
                "username": "",
            }
            bot.last_tested_at = timezone.now()
            bot.last_test_ok = False
            bot.last_test_error = payload["error"]
            bot.save(
                update_fields=[
                    "last_tested_at", "last_test_ok",
                    "last_test_error", "updated_at",
                ],
            )
            return Response(
                OrganizationBotTestResultSerializer(payload).data,
            )

        result = tg_get_me(token)
        username = (result.data or {}).get("username", "") if result.ok else ""

        if result.ok and username and username.lower() != bot.bot_username.lower():
            payload = {
                "ok": False,
                "error": (
                    f"Token resolves to @{username}, not @{bot.bot_username}."
                ),
                "username": username,
            }
            bot.last_test_ok = False
            bot.last_test_error = payload["error"]
        elif result.ok:
            payload = {"ok": True, "error": "", "username": username}
            bot.last_test_ok = True
            bot.last_test_error = ""
        else:
            payload = {"ok": False, "error": result.error, "username": ""}
            bot.last_test_ok = False
            bot.last_test_error = result.error

        bot.last_tested_at = timezone.now()
        bot.save(
            update_fields=[
                "last_tested_at", "last_test_ok",
                "last_test_error", "updated_at",
            ],
        )
        return Response(OrganizationBotTestResultSerializer(payload).data)

    @action(detail=True, methods=["post"])
    def set_webhook(self, request, id=None):
        """Register the per-org webhook URL with Telegram."""
        bot = self.get_object()
        base = getattr(settings, "PLATFORM_PUBLIC_URL", "") or ""
        if not base:
            raise ValidationError(
                "PLATFORM_PUBLIC_URL is not configured — refusing to set a "
                "webhook with an empty URL.",
            )
        try:
            token = bot.bot_token
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(f"Token could not be decrypted: {exc}")

        url = bot.get_webhook_url(base)
        result = tg_set_webhook(
            token, url=url, secret_token=bot.webhook_secret,
        )
        if not result.ok:
            raise ValidationError({"detail": result.error})
        return Response({"ok": True, "webhook_url": url})

    @action(detail=True, methods=["post"])
    def delete_webhook(self, request, id=None):
        """Clear the webhook — used when flipping a bot back to polling."""
        bot = self.get_object()
        try:
            token = bot.bot_token
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(f"Token could not be decrypted: {exc}")

        result = tg_delete_webhook(token)
        if not result.ok:
            raise ValidationError({"detail": result.error})
        return Response({"ok": True})
