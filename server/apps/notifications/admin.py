"""Admin registrations for the notifications app.

The big one here is :class:`OrganizationBotAdmin` — PR-14's admin UI
for managing per-organization Telegram bot credentials.  This is the
*only* place in the platform where a super_admin enters a Telegram bot
token; every downstream consumer reads it back via the ``bot_token``
property (which decrypts on access).

Access rules
------------
Only users with ``is_superuser=True`` ("super_admin" in our role
vocabulary) may see, add, change, or delete OrganizationBot rows.
Every permission hook on the ModelAdmin re-checks this — merely hiding
the link in the sidebar is not enough; a director with a direct URL
to ``/admin/notifications/organizationbot/…`` must still 403.

Token handling
--------------
The token is write-only in the admin form:

* The rendered field is a password input.  Previously-saved tokens are
  never sent back to the browser.
* On save, a non-empty value goes through
  ``OrganizationBot.bot_token`` setter which encrypts with Fernet
  before storage.  An empty submission means "keep the existing token".
* The list view and the form's readonly ``masked_token`` both show
  ``bot_id:••••••••XYZ`` so super_admin can verify the right token
  without revealing it.

Admin actions
-------------
* **Test bot** — calls Telegram's ``getMe`` and records the outcome on
  ``last_tested_at`` / ``last_test_ok`` / ``last_test_error``.  Lets
  super_admin verify a pasted token works before any user tries to
  ``/start``.
* **Set webhook** — calls Telegram's ``setWebhook`` with the URL
  derived from ``PLATFORM_PUBLIC_URL`` + the org's slug, and the
  stored ``webhook_secret``.  Safely no-ops in dev (where
  ``PLATFORM_PUBLIC_URL`` is blank) with a clear error.
* **Delete webhook** — symmetric; for flipping a bot back to polling.
"""
from __future__ import annotations

import logging

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.notifications.models import (
    OrganizationBot,
    TelegramProfile,
    TelegramVerificationToken,
)
from apps.notifications.telegram_api import (
    delete_webhook as tg_delete_webhook,
    get_me as tg_get_me,
    set_webhook as tg_set_webhook,
)

logger = logging.getLogger(__name__)


# ── OrganizationBot (PR-14) ───────────────────────────────────────────────────


class OrganizationBotAdminForm(forms.ModelForm):
    """Admin form with a write-only ``bot_token`` field.

    The field is never populated from the instance — that way an
    existing token is never round-tripped to the browser DOM or
    appears in form-resubmits.  Leaving the field blank means "keep
    whatever's in the DB"; entering a value replaces it.
    """

    bot_token = forms.CharField(
        label=_("Bot token"),
        widget=forms.PasswordInput(render_value=False),
        required=False,
        help_text=_(
            "Paste the token from @BotFather.  Leave blank to keep the "
            "existing token.  Stored Fernet-encrypted — we never show "
            "it back."
        ),
    )

    class Meta:
        model = OrganizationBot
        fields = [
            "organization",
            "bot_username",
            "bot_token",
            "is_active",
            "is_primary",
            "is_default",
        ]

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        raw = self.cleaned_data.get("bot_token") or ""
        if raw:
            instance.bot_token = raw  # encrypts via property setter
        if commit:
            instance.save()
        return instance


@admin.register(OrganizationBot)
class OrganizationBotAdmin(admin.ModelAdmin):
    """super_admin-only ModelAdmin for ``OrganizationBot``."""

    form = OrganizationBotAdminForm
    list_display = [
        "bot_username",
        "organization",
        "masked_token",
        "is_active",
        "is_primary",
        "is_default",
        "last_tested_at",
        "last_test_ok",
    ]
    list_filter = ["is_active", "is_primary", "is_default", "organization"]
    search_fields = ["bot_username", "organization__name", "organization__slug"]
    ordering = ["organization__name", "-is_primary"]
    readonly_fields = [
        "masked_token",
        "webhook_url",
        "webhook_secret",
        "internal_secret",
        "last_tested_at",
        "last_test_ok",
        "last_test_error",
        "created_by",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        (
            _("Identity"),
            {
                "fields": (
                    "organization",
                    "bot_username",
                    "bot_token",
                    "masked_token",
                ),
            },
        ),
        (
            _("Status"),
            {
                "fields": ("is_active", "is_primary", "is_default"),
                "description": _(
                    "Set 'Default bot' only when organization is empty — "
                    "this bot becomes the platform-wide fallback for orgs "
                    "without their own bot."
                ),
            },
        ),
        (
            _("Webhook"),
            {
                "fields": ("webhook_url", "webhook_secret"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Polling (dev)"),
            {
                "fields": ("internal_secret",),
                "classes": ("collapse",),
            },
        ),
        (
            _("Health & audit"),
            {
                "fields": (
                    "last_tested_at",
                    "last_test_ok",
                    "last_test_error",
                    "created_by",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    actions = ["action_test_bot", "action_set_webhook", "action_delete_webhook"]

    # ── Permissions: super_admin only ─────────────────────────────────────

    # Every entry point — the app-index link, the changelist, the add page,
    # and each row — funnels through these. Hiding the sidebar link is not
    # enough; a director hitting the URL directly must also get 403.
    def _is_super_admin(self, request) -> bool:
        return bool(request.user.is_authenticated and request.user.is_superuser)

    def has_module_permission(self, request):
        return self._is_super_admin(request)

    def has_view_permission(self, request, obj=None):
        return self._is_super_admin(request)

    def has_add_permission(self, request):
        return self._is_super_admin(request)

    def has_change_permission(self, request, obj=None):
        return self._is_super_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self._is_super_admin(request)

    # ── Read-only helpers shown in the form ───────────────────────────────

    @admin.display(description=_("Token (masked)"))
    def masked_token(self, obj: OrganizationBot | None) -> str:
        if obj is None or not obj.encrypted_token:
            return "—"
        try:
            return obj.bot_token_masked
        except Exception:  # noqa: BLE001 — defensive; don't 500 the admin
            return "••••(unreadable)"

    @admin.display(description=_("Webhook URL"))
    def webhook_url(self, obj: OrganizationBot | None) -> str:
        if obj is None or obj.pk is None:
            return "—"
        base = getattr(settings, "PLATFORM_PUBLIC_URL", "") or ""
        if not base:
            return _("(PLATFORM_PUBLIC_URL is not set — dev polling mode)")
        return obj.get_webhook_url(base)

    # ── Save hook: record creator ─────────────────────────────────────────

    def save_model(self, request, obj, form, change):
        if not change and obj.created_by_id is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    # ── Queryset: default bot always at the top ───────────────────────────

    def get_queryset(self, request):
        """Sort so the platform default bot (is_default=True) floats to top."""
        return (
            super()
            .get_queryset(request)
            .order_by("-is_default", "organization__name", "-is_primary")
        )

    # ── Admin actions ─────────────────────────────────────────────────────

    @admin.action(description=_("Test bot (getMe)"))
    def action_test_bot(self, request, queryset):
        """Call Telegram's ``getMe`` for each selected bot.

        Writes the outcome to the bot's ``last_tested_at`` /
        ``last_test_ok`` / ``last_test_error`` fields so it stays
        visible in the list view, and flashes an admin message per bot.
        """
        for bot in queryset:
            self._test_one(request, bot)

    @admin.action(description=_("Set webhook (Telegram → us)"))
    def action_set_webhook(self, request, queryset):
        base = getattr(settings, "PLATFORM_PUBLIC_URL", "") or ""
        if not base:
            self.message_user(
                request,
                _(
                    "PLATFORM_PUBLIC_URL is not configured — refusing to set "
                    "a webhook with an empty URL. Set the env var and retry."
                ),
                level=messages.ERROR,
            )
            return
        for bot in queryset:
            self._set_webhook_one(request, bot, base)

    @admin.action(description=_("Delete webhook (switch to polling)"))
    def action_delete_webhook(self, request, queryset):
        for bot in queryset:
            self._delete_webhook_one(request, bot)

    # ── Per-bot action bodies — factored out so tests can poke them ──────

    def _test_one(self, request, bot: OrganizationBot) -> None:
        try:
            token = bot.bot_token
        except Exception as exc:  # noqa: BLE001
            self._record_test_result(
                bot, ok=False, error=f"Token could not be decrypted: {exc}",
            )
            self.message_user(
                request,
                _("@%(name)s: token unreadable — %(err)s")
                % {"name": bot.bot_username, "err": exc},
                level=messages.ERROR,
            )
            return

        result = tg_get_me(token)
        if result.ok:
            returned = (result.data or {}).get("username") or ""
            if returned and returned.lower() != bot.bot_username.lower():
                # Configured username doesn't match what the token
                # actually opens up — a common copy-paste mistake.
                err = (
                    f"Token resolves to @{returned}, not @{bot.bot_username}."
                )
                self._record_test_result(bot, ok=False, error=err)
                self.message_user(
                    request,
                    _("@%(name)s: %(err)s")
                    % {"name": bot.bot_username, "err": err},
                    level=messages.WARNING,
                )
                return
            self._record_test_result(bot, ok=True, error="")
            self.message_user(
                request,
                _("@%(name)s: getMe OK.") % {"name": bot.bot_username},
                level=messages.SUCCESS,
            )
        else:
            self._record_test_result(bot, ok=False, error=result.error)
            self.message_user(
                request,
                _("@%(name)s: %(err)s")
                % {"name": bot.bot_username, "err": result.error},
                level=messages.ERROR,
            )

    def _set_webhook_one(
        self, request, bot: OrganizationBot, base_url: str,
    ) -> None:
        try:
            token = bot.bot_token
        except Exception as exc:  # noqa: BLE001
            self.message_user(
                request,
                _("@%(name)s: token unreadable — %(err)s")
                % {"name": bot.bot_username, "err": exc},
                level=messages.ERROR,
            )
            return

        url = bot.get_webhook_url(base_url)
        result = tg_set_webhook(
            token, url=url, secret_token=bot.webhook_secret,
        )
        if result.ok:
            self.message_user(
                request,
                _("@%(name)s: webhook set → %(url)s")
                % {"name": bot.bot_username, "url": url},
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                _("@%(name)s: setWebhook failed — %(err)s")
                % {"name": bot.bot_username, "err": result.error},
                level=messages.ERROR,
            )

    def _delete_webhook_one(self, request, bot: OrganizationBot) -> None:
        try:
            token = bot.bot_token
        except Exception as exc:  # noqa: BLE001
            self.message_user(
                request,
                _("@%(name)s: token unreadable — %(err)s")
                % {"name": bot.bot_username, "err": exc},
                level=messages.ERROR,
            )
            return

        result = tg_delete_webhook(token)
        if result.ok:
            self.message_user(
                request,
                _("@%(name)s: webhook cleared.")
                % {"name": bot.bot_username},
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                _("@%(name)s: deleteWebhook failed — %(err)s")
                % {"name": bot.bot_username, "err": result.error},
                level=messages.ERROR,
            )

    @staticmethod
    def _record_test_result(
        bot: OrganizationBot, ok: bool, error: str,
    ) -> None:
        bot.last_tested_at = timezone.now()
        bot.last_test_ok = ok
        bot.last_test_error = error or ""
        bot.save(
            update_fields=[
                "last_tested_at",
                "last_test_ok",
                "last_test_error",
                "updated_at",
            ],
        )


# ── TelegramProfile + TelegramVerificationToken (existing registrations) ─────


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "organization",
        "chat_id",
        "is_active",
        "notify_issues",
        "notify_passes",
        "notify_announcements",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "notify_issues",
        "notify_passes",
        "notify_announcements",
        "organization",
    ]
    search_fields = ["user__email", "chat_id", "organization__slug"]
    readonly_fields = ["created_at", "updated_at"]
    actions = ["deactivate_selected"]

    @admin.action(description="Deactivate selected profiles")
    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(TelegramVerificationToken)
class TelegramVerificationTokenAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "organization",
        "token",
        "is_used",
        "expires_at",
        "created_at",
    ]
    list_filter = ["is_used", "organization"]
    search_fields = ["user__email", "organization__slug"]
    readonly_fields = ["token", "created_at"]
