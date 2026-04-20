"""Tests for ``apps.notifications.utils`` — low-level send helpers.

Phase-3 scope: chat-ID listing helpers must filter by organization,
and ``_deactivate_profile`` must flip the right profiles. The actual
HTTP call to Telegram is mocked; we're not testing python-telegram-bot.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.notifications.models import TelegramProfile
from apps.notifications.utils import (
    _deactivate_profile,
    get_active_dispatcher_chat_ids,
    get_active_guard_chat_ids,
    send_message_sync,
)
from apps.organizations.models import Organization, OrganizationType
from apps.profiles.models import Profile

User = get_user_model()


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


def _mk_user(username, email, is_staff=False, occupation="tenant"):
    user = User.objects.create_user(
        username=username,
        email=email,
        password="Demo1234!",
        first_name="T",
        last_name="User",
        is_staff=is_staff,
    )
    profile = Profile.objects.get(user=user)
    profile.occupation = occupation
    profile.save(update_fields=["occupation"])
    return user


# ── Chat-ID listings ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDispatcherChatIds:
    def test_returns_only_target_org_dispatchers(self, org_a, org_b):
        disp_a = _mk_user("disp_a", "disp_a@demo.com", is_staff=True)
        disp_b = _mk_user("disp_b", "disp_b@demo.com", is_staff=True)
        TelegramProfile.objects.create(
            user=disp_a, organization=org_a, chat_id=1001,
            is_active=True, notify_issues=True,
        )
        TelegramProfile.objects.create(
            user=disp_b, organization=org_b, chat_id=2002,
            is_active=True, notify_issues=True,
        )
        chat_ids = get_active_dispatcher_chat_ids(org_a)
        assert chat_ids == [1001]

    def test_excludes_non_staff_even_if_notify_issues(self, org_a):
        tenant = _mk_user("tenant", "tenant@demo.com", is_staff=False)
        TelegramProfile.objects.create(
            user=tenant, organization=org_a, chat_id=77,
            is_active=True, notify_issues=True,
        )
        assert get_active_dispatcher_chat_ids(org_a) == []

    def test_excludes_inactive(self, org_a):
        disp = _mk_user("disp", "disp@demo.com", is_staff=True)
        TelegramProfile.objects.create(
            user=disp, organization=org_a, chat_id=33,
            is_active=False, notify_issues=True,
        )
        assert get_active_dispatcher_chat_ids(org_a) == []

    def test_excludes_notify_issues_off(self, org_a):
        disp = _mk_user("disp", "disp@demo.com", is_staff=True)
        TelegramProfile.objects.create(
            user=disp, organization=org_a, chat_id=44,
            is_active=True, notify_issues=False,
        )
        assert get_active_dispatcher_chat_ids(org_a) == []


@pytest.mark.django_db
class TestGuardChatIds:
    def test_returns_only_guards_in_target_org(self, org_a, org_b):
        guard_a = _mk_user(
            "guard_a", "guard_a@demo.com", occupation="guard",
        )
        guard_b = _mk_user(
            "guard_b", "guard_b@demo.com", occupation="guard",
        )
        TelegramProfile.objects.create(
            user=guard_a, organization=org_a, chat_id=501,
            is_active=True, notify_passes=True,
        )
        TelegramProfile.objects.create(
            user=guard_b, organization=org_b, chat_id=502,
            is_active=True, notify_passes=True,
        )
        assert get_active_guard_chat_ids(org_a) == [501]

    def test_excludes_non_guard_profession(self, org_a):
        tenant = _mk_user("t", "t@demo.com", occupation="tenant")
        TelegramProfile.objects.create(
            user=tenant, organization=org_a, chat_id=999,
            is_active=True, notify_passes=True,
        )
        assert get_active_guard_chat_ids(org_a) == []


# ── _deactivate_profile ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDeactivateProfile:
    def test_sets_is_active_false(self, org_a):
        user = _mk_user("u", "u@demo.com")
        profile = TelegramProfile.objects.create(
            user=user, organization=org_a, chat_id=123, is_active=True,
        )
        _deactivate_profile(123)
        profile.refresh_from_db()
        assert profile.is_active is False

    def test_noop_when_chat_id_unknown(self, org_a):
        """Never raises; just does nothing when nobody matches."""
        _deactivate_profile(9999999)  # no row exists


# ── send helpers ───────────────────────────────────────────────────────────
# Tests drive ``send_message_sync`` because it's a straight sync wrapper
# around ``send_message_async`` — covering the sync path exercises both
# without needing a pytest async plugin we don't ship.


@pytest.mark.django_db
class TestSendMessageSync:
    def test_empty_token_returns_false_without_calling_telegram(self):
        with patch("telegram.Bot") as mock_bot_cls:
            assert send_message_sync(123, "hi", "") is False
            mock_bot_cls.assert_not_called()

    def test_happy_path_sends_with_token_and_markdown(self):
        """Success path: bot is constructed with the token, send_message
        is awaited with chat_id/text/parse_mode, result is True."""
        with patch("telegram.Bot") as mock_bot_cls:
            bot_instance = MagicMock()
            bot_instance.send_message = AsyncMock(return_value=MagicMock())
            mock_bot_cls.return_value = bot_instance

            ok = send_message_sync(42, "hello", "123:xyz")

            assert ok is True
            mock_bot_cls.assert_called_once_with(token="123:xyz")
            bot_instance.send_message.assert_awaited_once()
            call_kwargs = bot_instance.send_message.await_args.kwargs
            assert call_kwargs["chat_id"] == 42
            assert call_kwargs["text"] == "hello"
            assert call_kwargs["parse_mode"] == "Markdown"

    def test_forbidden_deactivates_profile(self, org_a):
        """When Telegram returns Forbidden (user blocked the bot), the
        matching profile is marked inactive and the call returns False."""
        from telegram.error import Forbidden

        user = _mk_user("blk", "blk@demo.com")
        profile = TelegramProfile.objects.create(
            user=user, organization=org_a, chat_id=555,
            is_active=True,
        )

        with patch("telegram.Bot") as mock_bot_cls:
            bot_instance = MagicMock()
            bot_instance.send_message = AsyncMock(
                side_effect=Forbidden("user blocked bot"),
            )
            mock_bot_cls.return_value = bot_instance

            ok = send_message_sync(555, "hi", "123:xyz")

        assert ok is False
        profile.refresh_from_db()
        assert profile.is_active is False
