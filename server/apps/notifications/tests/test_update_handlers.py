"""Tests for ``apps.notifications.update_handlers`` — pure dispatch layer.

These tests cover the ORM-touching handlers the webhook and polling
paths share. The plumbing that actually speaks to Telegram is tested
separately (the webhook view in ``test_webhook.py``, the polling
command by direct integration).

Security invariant worth calling out: every query filters by
``bot.organization``, so the webhook/polling handlers are incapable of
reaching into another tenant's data even if Telegram delivered us a
chat_id that exists under another org.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.notifications.models import (
    OrganizationBot,
    TelegramProfile,
    TelegramVerificationToken,
)
from apps.notifications.update_handlers import (
    MSG_START_INVALID,
    MSG_START_OK,
    MSG_START_WELCOME,
    MSG_STATUS_NOT_LINKED,
    MSG_STOP_NO_PROFILE,
    MSG_STOP_OK,
    dispatch_command,
    handle_start,
    handle_status,
    handle_stop,
    handle_webhook_update,
    parse_command_text,
)
from apps.organizations.models import Organization, OrganizationType

User = get_user_model()


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def org_a(db):
    return Organization.objects.create(
        name="ОСББ A",
        slug="osbb-a",
        type=OrganizationType.HOUSING_COMPLEX,
    )


@pytest.fixture
def org_b(db):
    return Organization.objects.create(
        name="ОСББ B",
        slug="osbb-b",
        type=OrganizationType.HOUSING_COMPLEX,
    )


@pytest.fixture
def bot_a(db, org_a):
    bot = OrganizationBot(
        organization=org_a,
        bot_username="AlphaBot",
        is_active=True,
        is_primary=True,
    )
    bot.bot_token = "123456789:AAE-bot-a"
    bot.save()
    return bot


@pytest.fixture
def bot_b(db, org_b):
    bot = OrganizationBot(
        organization=org_b,
        bot_username="BetaBot",
        is_active=True,
        is_primary=True,
    )
    bot.bot_token = "987654321:AAE-bot-b"
    bot.save()
    return bot


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="resident",
        email="r@demo.com",
        password="Demo1234!",
        first_name="R", last_name="User",
    )


# ── parse_command_text ─────────────────────────────────────────────────────


class TestParseCommandText:
    def test_simple_slash_command(self):
        assert parse_command_text("/start") == ("start", [])

    def test_command_with_args(self):
        assert parse_command_text("/start abcd-1234") == (
            "start", ["abcd-1234"],
        )

    def test_strips_bot_suffix(self):
        """Group-chat mentions come as ``/start@AlphaBot``."""
        assert parse_command_text("/start@AlphaBot abc") == (
            "start", ["abc"],
        )

    def test_non_command_returns_none(self):
        assert parse_command_text("hello") is None

    def test_empty_returns_none(self):
        assert parse_command_text("") is None

    def test_just_slash_returns_none(self):
        assert parse_command_text("/") is None


# ── handle_start ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHandleStart:
    def test_no_args_shows_welcome(self, bot_a):
        result = handle_start(bot_a, chat_id=42, args=[])
        assert result.reply_text == MSG_START_WELCOME

    def test_unknown_token_rejected(self, bot_a):
        result = handle_start(bot_a, chat_id=42, args=["not-a-real-token"])
        assert result.reply_text == MSG_START_INVALID

    def test_expired_token_rejected(self, bot_a, user, org_a):
        from datetime import timedelta
        from django.utils import timezone

        token = TelegramVerificationToken.objects.create(
            user=user, organization=org_a,
        )
        # Force expired.
        TelegramVerificationToken.objects.filter(pk=token.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        result = handle_start(bot_a, chat_id=42, args=[str(token.token)])
        assert result.reply_text == MSG_START_INVALID

    def test_used_token_rejected(self, bot_a, user, org_a):
        token = TelegramVerificationToken.objects.create(
            user=user, organization=org_a, is_used=True,
        )
        result = handle_start(bot_a, chat_id=42, args=[str(token.token)])
        assert result.reply_text == MSG_START_INVALID

    def test_cross_org_token_rejected_with_generic_copy(
        self, bot_a, bot_b, user, org_b,
    ):
        """A token minted for org B must not be redeemable on org A's
        bot, AND the error copy must be indistinguishable from
        'invalid token' so a probe can't learn the failure reason."""
        token = TelegramVerificationToken.objects.create(
            user=user, organization=org_b,  # different org!
        )
        result = handle_start(bot_a, chat_id=42, args=[str(token.token)])
        assert result.reply_text == MSG_START_INVALID
        # The token must not be consumed or bound.
        token.refresh_from_db()
        assert token.is_used is False
        assert not TelegramProfile.objects.filter(chat_id=42).exists()

    def test_valid_token_creates_profile_and_marks_token_used(
        self, bot_a, user, org_a,
    ):
        token = TelegramVerificationToken.objects.create(
            user=user, organization=org_a,
        )
        result = handle_start(bot_a, chat_id=9999, args=[str(token.token)])
        assert result.reply_text == MSG_START_OK

        token.refresh_from_db()
        assert token.is_used is True

        profile = TelegramProfile.objects.get(
            user=user, organization=org_a,
        )
        assert profile.chat_id == 9999
        assert profile.is_active is True

    def test_relink_updates_chat_id_and_reactivates(
        self, bot_a, user, org_a,
    ):
        """User re-runs /start <new_token> → existing row is flipped back on."""
        TelegramProfile.objects.create(
            user=user, organization=org_a, chat_id=111,
            is_active=False,
        )
        token = TelegramVerificationToken.objects.create(
            user=user, organization=org_a,
        )
        handle_start(bot_a, chat_id=222, args=[str(token.token)])
        profile = TelegramProfile.objects.get(user=user, organization=org_a)
        assert profile.chat_id == 222
        assert profile.is_active is True


# ── handle_stop ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHandleStop:
    def test_deactivates_only_this_orgs_binding(
        self, bot_a, user, org_a, org_b,
    ):
        """A user with two bindings (org_a and org_b under the same
        chat_id) must keep org_b's binding alive when /stop hits org_a."""
        TelegramProfile.objects.create(
            user=user, organization=org_a, chat_id=55, is_active=True,
        )
        other = User.objects.create_user(
            username="u2", email="u2@demo.com", password="Demo1234!",
            first_name="U", last_name="Two",
        )
        TelegramProfile.objects.create(
            user=other, organization=org_b, chat_id=55, is_active=True,
        )

        result = handle_stop(bot_a, chat_id=55)
        assert result.reply_text == MSG_STOP_OK

        a_binding = TelegramProfile.objects.get(organization=org_a)
        b_binding = TelegramProfile.objects.get(organization=org_b)
        assert a_binding.is_active is False
        assert b_binding.is_active is True

    def test_no_profile_returns_informational(self, bot_a):
        result = handle_stop(bot_a, chat_id=999999)
        assert result.reply_text == MSG_STOP_NO_PROFILE


# ── handle_status ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHandleStatus:
    def test_not_linked_returns_hint(self, bot_a):
        result = handle_status(bot_a, chat_id=42)
        assert result.reply_text == MSG_STATUS_NOT_LINKED

    def test_active_profile_reports_on(self, bot_a, user, org_a):
        TelegramProfile.objects.create(
            user=user, organization=org_a, chat_id=42, is_active=True,
        )
        result = handle_status(bot_a, chat_id=42)
        assert "активні" in result.reply_text
        assert "r@demo.com" in result.reply_text

    def test_inactive_profile_reports_off(self, bot_a, user, org_a):
        TelegramProfile.objects.create(
            user=user, organization=org_a, chat_id=42, is_active=False,
        )
        result = handle_status(bot_a, chat_id=42)
        assert "вимкнені" in result.reply_text

    def test_status_scoped_to_bot_org(
        self, bot_a, bot_b, user, org_a, org_b,
    ):
        """Same chat_id under two orgs → /status on bot_a reflects
        only org_a's row."""
        TelegramProfile.objects.create(
            user=user, organization=org_a, chat_id=77, is_active=False,
        )
        other = User.objects.create_user(
            username="u2", email="u2@demo.com", password="Demo1234!",
            first_name="U", last_name="Two",
        )
        TelegramProfile.objects.create(
            user=other, organization=org_b, chat_id=77, is_active=True,
        )
        result = handle_status(bot_a, chat_id=77)
        assert "вимкнені" in result.reply_text
        # And the user shown must be org_a's user, not org_b's.
        assert "r@demo.com" in result.reply_text
        assert "u2@demo.com" not in result.reply_text


# ── dispatch_command + handle_webhook_update ───────────────────────────────


@pytest.mark.django_db
class TestDispatch:
    def test_unknown_command_returns_none(self, bot_a):
        assert dispatch_command(bot_a, 42, "unknown_cmd", []) is None

    def test_case_insensitive(self, bot_a):
        # /Start should still dispatch.
        result = dispatch_command(bot_a, 42, "START", [])
        assert result is not None


@pytest.mark.django_db
class TestHandleWebhookUpdate:
    def test_non_message_update_returns_none(self, bot_a):
        """Telegram sends many update kinds — we only care about message
        commands. Everything else is silently ignored."""
        assert handle_webhook_update(bot_a, {}) is None
        assert handle_webhook_update(bot_a, {"callback_query": {}}) is None

    def test_text_message_without_command_returns_none(self, bot_a):
        update = {
            "message": {
                "chat": {"id": 42},
                "text": "hello there",
            },
        }
        assert handle_webhook_update(bot_a, update) is None

    def test_start_command_dispatches(self, bot_a):
        update = {
            "message": {
                "chat": {"id": 42},
                "text": "/start",
            },
        }
        result = handle_webhook_update(bot_a, update)
        assert result is not None
        assert result.reply_text == MSG_START_WELCOME

    def test_start_with_token_arg_dispatches(self, bot_a, user, org_a):
        token = TelegramVerificationToken.objects.create(
            user=user, organization=org_a,
        )
        update = {
            "message": {
                "chat": {"id": 123},
                "text": f"/start {token.token}",
            },
        }
        result = handle_webhook_update(bot_a, update)
        assert result.reply_text == MSG_START_OK
        assert TelegramProfile.objects.filter(chat_id=123).exists()

    def test_edited_message_also_dispatches(self, bot_a):
        """Telegram retries delivery by resending as ``edited_message``
        when the user edits their original command. We honour that."""
        update = {
            "edited_message": {
                "chat": {"id": 42},
                "text": "/status",
            },
        }
        result = handle_webhook_update(bot_a, update)
        assert result is not None
        assert result.reply_text == MSG_STATUS_NOT_LINKED

    def test_missing_chat_id_returns_none(self, bot_a):
        update = {"message": {"text": "/start"}}
        assert handle_webhook_update(bot_a, update) is None
