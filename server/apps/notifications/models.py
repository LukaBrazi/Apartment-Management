"""Notifications models.

PR-14 introduces per-organization Telegram bots. See
``docs/ADR-014-multi-tenant-telegram-bots.md`` for the full rationale.

This module holds three models:

* ``OrganizationBot`` — PR-14; the encrypted bot credentials for an
  organization. One active primary bot per org (enforced by a partial
  unique constraint) so future failover-bot work is a clean add.
* ``TelegramProfile`` — links a user to a chat_id in the context of
  one bot. Rescoped in PR-14 to be per-(user, organization).
* ``TelegramVerificationToken`` — one-time token that the frontend
  generates and the bot exchanges for a chat_id binding. Also rescoped
  to carry the target organization so cross-tenant hijack is impossible.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.notifications.encryption import decrypt_token, encrypt_token, mask_token


# ── Secret helpers ────────────────────────────────────────────────────────────


def _make_webhook_secret() -> str:
    """Generate a webhook secret for Telegram's ``setWebhook(secret_token=…)``.

    Telegram restricts this to 1–256 chars of ``[A-Za-z0-9_-]``.
    ``token_urlsafe(32)`` gives ~43 chars from that alphabet — well
    within limits and with 256 bits of entropy.
    """
    return secrets.token_urlsafe(32)


def _make_internal_secret() -> str:
    """Shared secret for bot→Django API calls (polling mode only).

    Webhook mode uses ``webhook_secret`` instead; this is kept for the
    dev polling path where the ``run_bot`` process POSTs back to
    ``/verify/`` from the same host.
    """
    return secrets.token_urlsafe(32)


# ── OrganizationBot (PR-14) ───────────────────────────────────────────────────


class OrganizationBot(models.Model):
    """Per-organization Telegram bot credentials.

    Token is stored Fernet-encrypted. Access it via the ``bot_token``
    property, which decrypts on read and encrypts on write — callers
    never touch ``encrypted_token`` directly.

    White-labelling: each ЖК / management company brings their own
    ``@…Bot`` via BotFather and pastes the token here. The platform
    never ships a default — if this row is missing or inactive, the
    org simply receives no Telegram notifications (silent fallback;
    see ADR-014 §7).
    """

    pkid = models.BigAutoField(primary_key=True, editable=False)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="telegram_bots",
        verbose_name=_("Organization"),
    )

    bot_username = models.CharField(
        _("Bot username"),
        max_length=100,
        help_text=_(
            "Telegram bot username without the leading @ — e.g. 'ZelenyiKvartalBot'. "
            "Used to build the /start deep link."
        ),
    )
    # Fernet ciphertext. Always accessed via the bot_token property.
    encrypted_token = models.TextField(
        _("Encrypted bot token"),
        blank=True,
        default="",
        help_text=_("Fernet-encrypted. Never exposed via API."),
    )

    # ── Telegram webhook auth: Telegram → us ──
    webhook_secret = models.CharField(
        _("Webhook secret"),
        max_length=128,
        default=_make_webhook_secret,
        help_text=_(
            "Value passed to setWebhook(secret_token=…); Telegram sends it "
            "back on every update in the X-Telegram-Bot-Api-Secret-Token header."
        ),
    )
    # ── Internal-network auth for polling mode: bot process → Django API ──
    internal_secret = models.CharField(
        _("Internal secret"),
        max_length=128,
        default=_make_internal_secret,
        help_text=_(
            "Shared secret the polling bot passes in X-Telegram-Internal-Secret "
            "when calling our /verify/ endpoint. Only used in DEV polling mode."
        ),
    )

    is_active = models.BooleanField(
        _("Active"),
        default=True,
        db_index=True,
        help_text=_(
            "Per-org kill-switch. Disabling stops all sends for this org — "
            "tokens stay encrypted at rest for later re-activation."
        ),
    )
    is_primary = models.BooleanField(
        _("Primary"),
        default=True,
        help_text=_(
            "Future-proofing for a primary+backup setup. A partial unique "
            "constraint enforces at most one primary bot per organization."
        ),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_bots_created",
        verbose_name=_("Created by"),
    )

    # ── Health / audit fields updated by the "Test bot" admin action ──
    last_tested_at = models.DateTimeField(
        _("Last tested at"),
        null=True,
        blank=True,
        help_text=_("Updated when super_admin runs 'Test bot' in admin."),
    )
    last_test_ok = models.BooleanField(
        _("Last test ok"),
        null=True,
        blank=True,
    )
    last_test_error = models.TextField(
        _("Last test error"),
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Organization Bot")
        verbose_name_plural = _("Organization Bots")
        ordering = ["organization", "-is_primary", "-created_at"]
        constraints = [
            # Only one primary bot per org — but non-primary (backup)
            # bots are allowed to proliferate. Partial unique keeps the
            # schema simple: no need to pre-create "slots".
            models.UniqueConstraint(
                fields=["organization"],
                condition=models.Q(is_primary=True),
                name="unique_primary_telegram_bot_per_org",
            ),
            # Usernames are globally unique on Telegram's side — enforce
            # the same in our DB so two orgs can't both claim the same
            # bot by mistake (which would cause hilarious routing bugs).
            models.UniqueConstraint(
                fields=["bot_username"],
                name="unique_bot_username",
            ),
        ]

    def __str__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"@{self.bot_username} → {self.organization.name} ({status})"

    # ── Token accessors ──────────────────────────────────────────────────────

    @property
    def bot_token(self) -> str:
        """Decrypt and return the raw Telegram bot token.

        Raises :class:`cryptography.fernet.InvalidToken` if the
        encryption key was rotated without re-encrypting this row.
        The webhook / Celery task paths catch that and treat the bot
        as unusable instead of crashing the worker.
        """
        return decrypt_token(self.encrypted_token)

    @bot_token.setter
    def bot_token(self, value: str) -> None:
        """Encrypt ``value`` and store it. Empty value wipes the field."""
        self.encrypted_token = encrypt_token(value) if value else ""

    @property
    def bot_token_masked(self) -> str:
        """Safe-to-display preview — used in admin list and in API responses."""
        try:
            plaintext = self.bot_token
        except Exception:
            return "••••(unreadable)"
        return mask_token(plaintext)

    @property
    def is_configured(self) -> bool:
        """True iff we have everything needed to actually send a message."""
        return bool(self.encrypted_token and self.bot_username and self.is_active)

    # ── Webhook URL helper ──────────────────────────────────────────────────

    def get_webhook_url(self, base_url: str) -> str:
        """Build the HTTPS URL Telegram should POST updates to.

        ``base_url`` is the public origin (e.g. ``https://apartmentos.org``).
        The path uses the org slug so routing stays readable in logs.
        """
        base = base_url.rstrip("/")
        return f"{base}/api/v1/notifications/telegram/webhook/{self.organization.slug}/"


# ── Per-(user, organization) profile + verification token (PR-14 phase 2) ──
#
# Rescoped in phase 2 so the same human can link Telegram separately to each
# ЖК they belong to. Each link carries its own notification preferences and
# is bound to that org's bot — cross-org hijack is structurally impossible.


class TelegramProfile(models.Model):
    """Per-(user, organization) Telegram chat binding.

    Phase 2 rescope: what used to be one profile per user globally is now
    one profile per (user, organization) pair. The same physical person
    with two ЖК memberships ends up with two rows — one per bot — and
    each row's notification preferences are independent.

    Uniqueness:
    - ``(user, organization)`` — at most one profile per user per org.
    - ``(organization, chat_id)`` — within a single bot, a chat_id maps
      to exactly one user. Telegram already enforces this on their side;
      duplicating it in the DB makes bad states unrepresentable.
    Global chat_id uniqueness is gone: the same Telegram account can
    hold bindings under different org bots, with different chat_ids
    assigned per bot by Telegram.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_profiles",
        verbose_name=_("User"),
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="telegram_profiles",
        verbose_name=_("Organization"),
        help_text=_(
            "Which ЖК this binding belongs to — the org whose bot owns the chat_id."
        ),
    )
    chat_id = models.BigIntegerField(
        _("Chat ID"),
        db_index=True,
        help_text=_(
            "Telegram chat_id the org's bot will DM. Unique per organization, "
            "not globally — one person can link the same Telegram account to "
            "multiple orgs (Telegram assigns a separate chat_id per bot)."
        ),
    )
    is_active = models.BooleanField(_("Active"), default=True)
    # Per-profile notification preferences — toggled from the user's profile UI.
    notify_issues = models.BooleanField(default=True, verbose_name=_("Issue updates"))
    notify_passes = models.BooleanField(default=True, verbose_name=_("Pass updates"))
    notify_announcements = models.BooleanField(
        default=True, verbose_name=_("Announcements"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Telegram Profile")
        verbose_name_plural = _("Telegram Profiles")
        ordering = ["organization", "user_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="unique_tg_profile_per_user_and_org",
            ),
            models.UniqueConstraint(
                fields=["organization", "chat_id"],
                name="unique_tg_chat_id_per_org",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"TelegramProfile(user={self.user.email}, "
            f"org={self.organization.slug}, chat_id={self.chat_id})"
        )


def token_expires_at():
    return timezone.now() + timedelta(minutes=15)


class TelegramVerificationToken(models.Model):
    """One-time token exchanged via ``/start <token>`` in the org's bot.

    Phase-2 rescope: the token now carries the target ``organization`` so
    the bot can refuse a token that belongs to a different ЖК. Without
    this field, someone could lift a token from org A's frontend and
    redeem it against org B's bot, ending up with a chat binding to the
    wrong tenant scope.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_tokens",
        verbose_name=_("User"),
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="telegram_verification_tokens",
        verbose_name=_("Organization"),
        help_text=_(
            "Target org — /verify/ rejects the exchange unless this matches "
            "the bot that received /start."
        ),
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField(default=token_expires_at)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Telegram Verification Token")
        verbose_name_plural = _("Telegram Verification Tokens")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"Token({self.user.email} → {self.organization.slug}, used={self.is_used})"
        )

    @property
    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at
