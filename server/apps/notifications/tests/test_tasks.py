"""Tests for ``apps.notifications.tasks`` — PR-14 phase 3 Celery wiring.

These tests pin down the behaviour that makes the multi-tenant rewrite
safe:

* Every task resolves the target org and asks
  ``bot_resolver.get_bot_for_org`` for the right bot. When that returns
  ``None`` (feature off, bot inactive, no bot at all), the task is a
  silent no-op — no exception, no "null-token" message, nothing queued.
* ``send_telegram_message`` receives a ``bot_id`` (not a token). It
  dereferences the ``OrganizationBot`` on the worker, so encrypted
  tokens never sit in the Redis payload.
* ``notify_building_tenants_announcement`` is the single most
  important regression test in this module: pre-PR-14, this task
  notified EVERY tenant profile on the platform. The test below
  proves it now fans out only to tenants of the announcement's own org.

We drive the tasks **in-process** (Celery's ``CELERY_TASK_ALWAYS_EAGER``
is on in ``config.settings.test``) and mock ``send_message_sync`` to
capture what would have been sent without touching Telegram.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from apps.apartments.models import Building
from apps.issues.models import Issue
from apps.notifications.bot_resolver import TELEGRAM_FEATURE_FLAG
from apps.notifications.models import OrganizationBot, TelegramProfile
from apps.notifications.tasks import (
    _org_of_issue,
    _site_name,
    notify_building_tenants_announcement,
    notify_dispatchers_new_issue,
    notify_tenant_issue_status_changed,
    notify_tenant_pass_status,
    notify_worker_assigned,
    send_telegram_broadcast,
    send_telegram_message,
)
from apps.organizations.models import Organization, OrganizationType
from apps.passes.models import VehiclePass
from apps.posts.models import Announcement
from apps.profiles.models import Profile

User = get_user_model()


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def org_a(db):
    return Organization.objects.create(
        name="ОСББ A",
        slug="osbb-a",
        type=OrganizationType.HOUSING_COMPLEX,
        features={TELEGRAM_FEATURE_FLAG: True},
    )


@pytest.fixture
def org_b(db):
    return Organization.objects.create(
        name="ОСББ B",
        slug="osbb-b",
        type=OrganizationType.HOUSING_COMPLEX,
        features={TELEGRAM_FEATURE_FLAG: True},
    )


@pytest.fixture
def org_a_off(db):
    """Org with feature flag disabled — same shape as org_a but muted."""
    return Organization.objects.create(
        name="ОСББ Silent",
        slug="osbb-silent",
        type=OrganizationType.HOUSING_COMPLEX,
        features={TELEGRAM_FEATURE_FLAG: False},
    )


@pytest.fixture
def bot_factory(db):
    """Create a configured, active, primary ``OrganizationBot`` for an org."""
    def _make(organization, **overrides):
        bot = OrganizationBot(
            organization=organization,
            bot_username=overrides.pop("bot_username", "AlphaOSBBBot"),
            is_active=overrides.pop("is_active", True),
            is_primary=overrides.pop("is_primary", True),
        )
        bot.bot_token = overrides.pop(
            "bot_token", "123456789:AAE-configured-token-xyz",
        )
        for k, v in overrides.items():
            setattr(bot, k, v)
        bot.save()
        return bot

    return _make


def _mk_user(
    username: str,
    email: str,
    *,
    is_staff: bool = False,
    occupation: str = "tenant",
):
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


# ── _org_of_issue helper ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestOrgOfIssue:
    def test_prefers_direct_fk_when_set(self, org_a):
        issue = Issue.objects.create(
            title="t", description="d", organization=org_a,
        )
        assert _org_of_issue(issue) == org_a

    def test_returns_none_when_neither_fk_nor_unit(self):
        issue = Issue.objects.create(title="t", description="d")
        assert _org_of_issue(issue) is None

    def test_falls_back_to_unit_organization(self, org_a):
        """Older rows with org=NULL but a unit pointing at an org
        should still resolve. This is the bridging path for issues
        created before PR-9 added the direct FK."""
        from apps.apartments.models import Entrance, Unit

        building = Building.objects.create(
            name="Дім А", address="вул. Тестова 1", organization=org_a,
        )
        entrance = Entrance.objects.create(building=building, name="1")
        unit = Unit.objects.create(entrance=entrance, number="1A")
        # Important: organization=None so the fallback path exercises.
        issue = Issue.objects.create(
            title="legacy", description="", unit=unit, organization=None,
        )
        assert _org_of_issue(issue) == org_a


# ── send_telegram_message ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestSendTelegramMessage:
    def test_drops_when_bot_id_unknown(self):
        """A stale bot_id (bot deleted after the task was queued)
        must be a silent drop — not an exception, not a retry."""
        import uuid

        with patch(
            "apps.notifications.utils.send_message_sync",
        ) as mock_send:
            send_telegram_message(str(uuid.uuid4()), 42, "hi")
            mock_send.assert_not_called()

    def test_drops_when_bot_inactive(self, org_a, bot_factory):
        bot = bot_factory(org_a, is_active=False)
        with patch(
            "apps.notifications.utils.send_message_sync",
        ) as mock_send:
            send_telegram_message(str(bot.id), 42, "hi")
            mock_send.assert_not_called()

    def test_drops_when_bot_has_no_token(self, org_a, bot_factory):
        """``is_configured`` is False when there's no token, so the
        task must not even open a Telegram connection."""
        bot = bot_factory(org_a)
        bot.bot_token = ""
        bot.save(update_fields=["encrypted_token"])
        with patch(
            "apps.notifications.utils.send_message_sync",
        ) as mock_send:
            send_telegram_message(str(bot.id), 42, "hi")
            mock_send.assert_not_called()

    def test_happy_path_dereferences_token_from_bot(self, org_a, bot_factory):
        """The token is read on the worker, never carried on the queue."""
        bot = bot_factory(org_a, bot_token="987:xyz")
        with patch(
            "apps.notifications.utils.send_message_sync", return_value=True,
        ) as mock_send:
            send_telegram_message(str(bot.id), 42, "hi")
            mock_send.assert_called_once_with(42, "hi", "987:xyz")


# ── notify_tenant_issue_status_changed ─────────────────────────────────────


@pytest.mark.django_db
class TestNotifyTenantIssueStatusChanged:
    def test_noop_when_feature_off(self, org_a_off, bot_factory):
        """Flag off → no message, even if bot + profile exist."""
        user = _mk_user("u1", "u1@demo.com")
        TelegramProfile.objects.create(
            user=user, organization=org_a_off, chat_id=111,
            is_active=True, notify_issues=True,
        )
        bot_factory(org_a_off)
        issue = Issue.objects.create(
            title="t", description="d", reported_by=user,
            organization=org_a_off,
        )

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_tenant_issue_status_changed(
                str(issue.pk), "reported", "in_progress",
            )
            mock_delay.assert_not_called()

    def test_noop_when_no_profile(self, org_a, bot_factory):
        """Tenant hasn't linked Telegram → skip, don't error."""
        user = _mk_user("u", "u@demo.com")
        bot_factory(org_a)
        issue = Issue.objects.create(
            title="t", description="d", reported_by=user, organization=org_a,
        )

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_tenant_issue_status_changed(
                str(issue.pk), "reported", "in_progress",
            )
            mock_delay.assert_not_called()

    def test_sends_to_reporter_when_active(self, org_a, bot_factory):
        user = _mk_user("u", "u@demo.com")
        TelegramProfile.objects.create(
            user=user, organization=org_a, chat_id=777,
            is_active=True, notify_issues=True,
        )
        bot = bot_factory(org_a)
        issue = Issue.objects.create(
            title="Leak in kitchen", description="d",
            reported_by=user, organization=org_a,
        )

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_tenant_issue_status_changed(
                str(issue.pk), "reported", "in_progress",
            )
            mock_delay.assert_called_once()
            args = mock_delay.call_args.args
            assert args[0] == str(bot.id)
            assert args[1] == 777
            # Message body contains the issue title and the new label.
            assert "Leak in kitchen" in args[2]
            assert "В роботі" in args[2]


# ── notify_dispatchers_new_issue ───────────────────────────────────────────


@pytest.mark.django_db
class TestNotifyDispatchersNewIssue:
    def test_does_not_send_to_dispatcher_in_other_org(
        self, org_a, org_b, bot_factory,
    ):
        """Regression: a new issue in org_a must not surface to a
        dispatcher who only belongs to org_b. This is the core
        tenant-isolation guarantee."""
        disp_b = _mk_user("disp_b", "disp_b@demo.com", is_staff=True)
        TelegramProfile.objects.create(
            user=disp_b, organization=org_b, chat_id=500,
            is_active=True, notify_issues=True,
        )
        bot_factory(org_a)
        bot_factory(org_b, bot_username="BetaOSBBBot")

        issue = Issue.objects.create(
            title="leak", description="", organization=org_a,
            reported_by=_mk_user("tenant_a", "ta@demo.com"),
        )

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_dispatchers_new_issue(str(issue.pk))
            # disp_b belongs to org_b, not org_a → no call.
            assert mock_delay.call_count == 0

    def test_fans_out_to_each_dispatcher_in_issue_org(
        self, org_a, bot_factory,
    ):
        disp1 = _mk_user("d1", "d1@demo.com", is_staff=True)
        disp2 = _mk_user("d2", "d2@demo.com", is_staff=True)
        TelegramProfile.objects.create(
            user=disp1, organization=org_a, chat_id=1001,
            is_active=True, notify_issues=True,
        )
        TelegramProfile.objects.create(
            user=disp2, organization=org_a, chat_id=1002,
            is_active=True, notify_issues=True,
        )
        bot = bot_factory(org_a)
        issue = Issue.objects.create(
            title="fire", description="", organization=org_a,
            reported_by=_mk_user("tenant", "t@demo.com"),
        )

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_dispatchers_new_issue(str(issue.pk))
            assert mock_delay.call_count == 2
            # Confirm each dispatcher's chat_id was addressed with the
            # right bot_id — ordering doesn't matter.
            addressed = {
                call.args[1] for call in mock_delay.call_args_list
            }
            assert addressed == {1001, 1002}
            for call in mock_delay.call_args_list:
                assert call.args[0] == str(bot.id)


# ── notify_worker_assigned ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestNotifyWorkerAssigned:
    def test_noop_when_no_assignee(self, org_a, bot_factory):
        bot_factory(org_a)
        issue = Issue.objects.create(
            title="t", description="", organization=org_a,
            reported_by=_mk_user("r", "r@demo.com"),
        )
        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_worker_assigned(str(issue.pk))
            mock_delay.assert_not_called()

    def test_sends_to_assignee_with_org_bot(self, org_a, bot_factory):
        worker = _mk_user("w", "w@demo.com", is_staff=True)
        TelegramProfile.objects.create(
            user=worker, organization=org_a, chat_id=404,
            is_active=True, notify_issues=True,
        )
        bot = bot_factory(org_a)
        issue = Issue.objects.create(
            title="fix_lift", description="",
            organization=org_a, assigned_to=worker,
            reported_by=_mk_user("r2", "r2@demo.com"),
        )
        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_worker_assigned(str(issue.pk))
            mock_delay.assert_called_once()
            args = mock_delay.call_args.args
            assert args[0] == str(bot.id)
            assert args[1] == 404
            assert "fix_lift" in args[2]


# ── notify_building_tenants_announcement (CROSS-TENANT REGRESSION) ─────────


@pytest.mark.django_db
class TestAnnouncementCrossTenantRegression:
    """The pre-PR-14 code sent announcements to EVERY tenant on the
    platform. These tests lock in the fix: a building's announcement
    only ever reaches its own org's tenants.

    Fan-out now goes through one ``send_telegram_broadcast`` task that
    receives all eligible chat_ids at once. Tests that check *isolation*
    mock ``send_telegram_broadcast.delay``; tests that check the
    *broadcast internals* mock ``send_telegram_message.delay``.
    """

    def test_does_not_leak_to_tenants_in_other_orgs(
        self, org_a, org_b, bot_factory,
    ):
        # Tenant in org_a — should be notified.
        tenant_a = _mk_user("ta", "ta@demo.com", occupation="tenant")
        TelegramProfile.objects.create(
            user=tenant_a, organization=org_a, chat_id=101,
            is_active=True, notify_announcements=True,
        )
        # Tenant in org_b — MUST NOT receive the org_a announcement.
        tenant_b = _mk_user("tb", "tb@demo.com", occupation="tenant")
        TelegramProfile.objects.create(
            user=tenant_b, organization=org_b, chat_id=202,
            is_active=True, notify_announcements=True,
        )
        bot_a = bot_factory(org_a, bot_username="AlphaBot")
        bot_factory(org_b, bot_username="BetaBot")

        building_a = Building.objects.create(
            name="Дім А-1", address="вул. Ринок 1", organization=org_a,
        )
        announcement = Announcement.objects.create(
            building=building_a, title="Плановий ремонт ліфта", body="—",
        )

        with patch(
            "apps.notifications.tasks.send_telegram_broadcast.delay",
        ) as mock_delay:
            notify_building_tenants_announcement(str(announcement.pk))
            # One broadcast dispatched with only org_a's tenant.
            assert mock_delay.call_count == 1
            _bot_id, chat_ids, _text = mock_delay.call_args.args
            assert _bot_id == str(bot_a.id)
            assert chat_ids == [101]

    def test_uses_target_orgs_bot_not_another(self, org_a, org_b, bot_factory):
        """Even if another org happens to have a bot, the announcement
        must be sent through the announcement org's bot. This protects
        against a silent "wrong sender" bug that would attribute the
        message to the wrong ЖК."""
        tenant = _mk_user("ta", "ta@demo.com", occupation="tenant")
        TelegramProfile.objects.create(
            user=tenant, organization=org_a, chat_id=55,
            is_active=True, notify_announcements=True,
        )
        bot_a = bot_factory(org_a, bot_username="AlphaBot")
        bot_factory(org_b, bot_username="BetaBot")

        building_a = Building.objects.create(
            name="Дім А-1", address="вул. Ринок 1", organization=org_a,
        )
        announcement = Announcement.objects.create(
            building=building_a, title="т", body="—",
        )

        with patch(
            "apps.notifications.tasks.send_telegram_broadcast.delay",
        ) as mock_delay:
            notify_building_tenants_announcement(str(announcement.pk))
            bot_id_used = mock_delay.call_args.args[0]
            assert bot_id_used == str(bot_a.id)

    def test_noop_when_target_org_has_no_bot(self, org_a, org_b, bot_factory):
        """If the announcement's org has no bot configured, nothing is
        sent — and a bot in *another* org is not repurposed."""
        tenant = _mk_user("ta", "ta@demo.com", occupation="tenant")
        TelegramProfile.objects.create(
            user=tenant, organization=org_a, chat_id=1,
            is_active=True, notify_announcements=True,
        )
        # Only org_b has a bot — org_a does NOT.
        bot_factory(org_b)

        building_a = Building.objects.create(
            name="Дім А-1", address="вул. Ринок 1", organization=org_a,
        )
        announcement = Announcement.objects.create(
            building=building_a, title="т", body="—",
        )

        with patch(
            "apps.notifications.tasks.send_telegram_broadcast.delay",
        ) as mock_delay:
            notify_building_tenants_announcement(str(announcement.pk))
            mock_delay.assert_not_called()

    def test_respects_notify_announcements_flag(self, org_a, bot_factory):
        """A tenant who opted out of announcement pings doesn't receive."""
        tenant = _mk_user("ta", "ta@demo.com", occupation="tenant")
        TelegramProfile.objects.create(
            user=tenant, organization=org_a, chat_id=9,
            is_active=True, notify_announcements=False,  # opted out
        )
        bot_factory(org_a)

        building_a = Building.objects.create(
            name="Дім А-1", address="вул. Ринок 1", organization=org_a,
        )
        announcement = Announcement.objects.create(
            building=building_a, title="т", body="—",
        )

        with patch(
            "apps.notifications.tasks.send_telegram_broadcast.delay",
        ) as mock_delay:
            notify_building_tenants_announcement(str(announcement.pk))
            mock_delay.assert_not_called()

    def test_send_telegram_broadcast_fans_out_to_send_telegram_message(
        self, org_a, bot_factory,
    ):
        """``send_telegram_broadcast`` must enqueue one
        ``send_telegram_message`` per chat_id."""
        bot = bot_factory(org_a)
        chat_ids = [111, 222, 333]

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_send:
            send_telegram_broadcast(str(bot.id), chat_ids, "hello")
            assert mock_send.call_count == 3
            addressed = {call.args[1] for call in mock_send.call_args_list}
            assert addressed == {111, 222, 333}
            for call in mock_send.call_args_list:
                assert call.args[0] == str(bot.id)


# ── notify_tenant_pass_status ──────────────────────────────────────────────


@pytest.mark.django_db
class TestNotifyTenantPassStatus:
    def test_sends_to_tenant_with_pass_org_bot(self, org_a, bot_factory):
        tenant = _mk_user("t", "t@demo.com")
        TelegramProfile.objects.create(
            user=tenant, organization=org_a, chat_id=321,
            is_active=True, notify_passes=True,
        )
        bot = bot_factory(org_a)
        vp = VehiclePass.objects.create(
            tenant=tenant, organization=org_a,
            car_number="AA1234BB", visit_date=date.today(),
        )

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_tenant_pass_status(str(vp.pk), "closed")
            mock_delay.assert_called_once()
            args = mock_delay.call_args.args
            assert args[0] == str(bot.id)
            assert args[1] == 321
            assert "AA1234BB" in args[2]

    def test_noop_when_tenant_has_no_profile(self, org_a, bot_factory):
        tenant = _mk_user("t", "t@demo.com")
        bot_factory(org_a)
        vp = VehiclePass.objects.create(
            tenant=tenant, organization=org_a,
            car_number="AA1234BB", visit_date=date.today(),
        )
        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_tenant_pass_status(str(vp.pk), "closed")
            mock_delay.assert_not_called()


# ── _site_name() fallback (БАГ 1) ─────────────────────────────────────────


class TestSiteName:
    """Verify the platform-name helper returns the correct fallback.

    BUG 1: Before the fix, _site_name() returned "EstateOS" when
    SITE_NAME was unset. After the fix it must return "ApartmentOS".
    """

    def test_fallback_returns_apartmentos_when_setting_absent(self, settings):
        """Deleting the setting entirely must yield the new default."""
        if hasattr(settings, "SITE_NAME"):
            delattr(settings, "SITE_NAME")
        assert _site_name() == "ApartmentOS"

    def test_returns_custom_value_when_setting_is_present(self, settings):
        """An explicitly configured SITE_NAME must be honoured as-is."""
        settings.SITE_NAME = "МійЖК"
        assert _site_name() == "МійЖК"

    def test_default_is_not_estateos(self, settings):
        """Regression: the old buggy default must never appear again."""
        if hasattr(settings, "SITE_NAME"):
            delattr(settings, "SITE_NAME")
        assert _site_name() != "EstateOS"


# ── notify_tenant_pass_status — status label mapping (БАГ 2) ──────────────


@pytest.mark.django_db
class TestNotifyTenantPassStatusLabels:
    """Verify that every status value produces the correct Ukrainian label
    in the notification text, and that unknown statuses don't raise KeyError.

    BUG 2: Before the fix, the dict lookup was unguarded and would raise
    KeyError for any status not explicitly listed. The fix uses .get() with
    a fallback "оновлена: <status>".
    """

    def _create_vp_and_profile(self, org, bot):
        """Helper — creates a tenant with a linked Telegram profile and pass."""
        tenant = _mk_user("tp_label", "tp_label@demo.com")
        TelegramProfile.objects.create(
            user=tenant, organization=org, chat_id=700,
            is_active=True, notify_passes=True,
        )
        vp = VehiclePass.objects.create(
            tenant=tenant, organization=org,
            car_number="BB5678CC", visit_date=date.today(),
        )
        return vp

    def test_closed_status_text_contains_зафіксовано(self, org_a, bot_factory):
        """'closed' must produce text that includes 'зафіксовано', not 'підтверджена'."""
        bot = bot_factory(org_a)
        vp = self._create_vp_and_profile(org_a, bot)

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_tenant_pass_status(str(vp.pk), "closed")
            mock_delay.assert_called_once()
            text = mock_delay.call_args.args[2]
            assert "зафіксовано" in text
            # Ensure the old wrong label is absent.
            assert "підтверджена" not in text

    def test_pending_status_text_contains_очікує(self, org_a, bot_factory):
        """'pending' must produce text that includes 'очікує'."""
        bot = bot_factory(org_a)
        vp = self._create_vp_and_profile(org_a, bot)

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_tenant_pass_status(str(vp.pk), "pending")
            mock_delay.assert_called_once()
            text = mock_delay.call_args.args[2]
            assert "очікує" in text

    def test_unknown_status_uses_fallback_without_key_error(
        self, org_a, bot_factory,
    ):
        """An unexpected status string must never raise KeyError — it must
        produce the generic 'оновлена: <status>' fallback label."""
        bot = bot_factory(org_a)
        vp = self._create_vp_and_profile(org_a, bot)

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            # Must not raise.
            notify_tenant_pass_status(str(vp.pk), "unknown_status")
            mock_delay.assert_called_once()
            text = mock_delay.call_args.args[2]
            assert "оновлена: unknown_status" in text


# ── send_telegram_broadcast (БАГ 3) ───────────────────────────────────────


@pytest.mark.django_db
class TestSendTelegramBroadcast:
    """Verify the fan-out task that replaced the per-recipient loop.

    BUG 3: Before the fix, notify_building_tenants_announcement called
    send_telegram_message.delay in a loop — one Redis task per tenant.
    The fix introduces send_telegram_broadcast which chunks the list to
    keep queue spikes manageable.
    """

    def test_60_chat_ids_produces_exactly_60_send_calls(
        self, org_a, bot_factory,
    ):
        """60 recipients → exactly 60 send_telegram_message.delay calls.

        With BROADCAST_CHUNK_SIZE=25 the internal loop runs 3 iterations
        (25 + 25 + 10), but each individual chat_id still triggers exactly
        one send call — the chunking is an implementation detail that must
        not drop or duplicate recipients.
        """
        bot = bot_factory(org_a)
        chat_ids = list(range(1, 61))  # 60 unique chat_ids

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_send:
            send_telegram_broadcast(str(bot.id), chat_ids, "hello 60")
            assert mock_send.call_count == 60
            addressed = {call.args[1] for call in mock_send.call_args_list}
            assert addressed == set(chat_ids)

    def test_empty_list_produces_zero_calls(self, org_a, bot_factory):
        """An empty chat_ids list must be a silent no-op — no tasks, no errors."""
        bot = bot_factory(org_a)

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_send:
            send_telegram_broadcast(str(bot.id), [], "nobody home")
            mock_send.assert_not_called()

    def test_single_chat_id_uses_correct_bot_id(self, org_a, bot_factory):
        """A broadcast to a single recipient must pass the correct bot_id."""
        bot = bot_factory(org_a)

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_send:
            send_telegram_broadcast(str(bot.id), [999], "one recipient")
            mock_send.assert_called_once()
            bot_id_used, chat_id_used, text_used = mock_send.call_args.args
            assert bot_id_used == str(bot.id)
            assert chat_id_used == 999
            assert "one recipient" in text_used


@pytest.mark.django_db
class TestAnnouncementUsesBroadcastTask:
    """Verify that notify_building_tenants_announcement dispatches a
    single send_telegram_broadcast.delay call — not a per-recipient loop.

    This is the observable guarantee of BUG 3's fix: no matter how many
    tenants an org has, the announcement dispatcher enqueues exactly one
    broadcast task and lets that task handle chunking internally.
    """

    def test_dispatches_single_broadcast_delay_not_per_recipient_loop(
        self, org_a, bot_factory,
    ):
        """3 tenants → send_telegram_broadcast.delay called once (not 3 times)."""
        for i in range(3):
            u = _mk_user(f"bt{i}", f"bt{i}@demo.com", occupation="tenant")
            TelegramProfile.objects.create(
                user=u, organization=org_a, chat_id=2000 + i,
                is_active=True, notify_announcements=True,
            )
        bot = bot_factory(org_a)
        building = Building.objects.create(
            name="Broadcast Дім", address="вул. Нова 5", organization=org_a,
        )
        announcement = Announcement.objects.create(
            building=building, title="Новини ЖК", body="—",
        )

        with patch(
            "apps.notifications.tasks.send_telegram_broadcast.delay",
        ) as mock_broadcast:
            notify_building_tenants_announcement(str(announcement.pk))
            # Exactly ONE broadcast task dispatched, regardless of tenant count.
            mock_broadcast.assert_called_once()
            bot_id_used, chat_ids_used, text_used = mock_broadcast.call_args.args
            assert bot_id_used == str(bot.id)
            assert set(chat_ids_used) == {2000, 2001, 2002}
            assert "Новини ЖК" in text_used

    def test_broadcast_carries_all_chat_ids_in_single_call(
        self, org_a, bot_factory,
    ):
        """All eligible tenant chat_ids must be passed to the single
        broadcast call — none dropped, none duplicated."""
        expected_ids = set()
        for i in range(5):
            u = _mk_user(f"bc{i}", f"bc{i}@demo.com", occupation="tenant")
            TelegramProfile.objects.create(
                user=u, organization=org_a, chat_id=3000 + i,
                is_active=True, notify_announcements=True,
            )
            expected_ids.add(3000 + i)
        bot_factory(org_a)
        building = Building.objects.create(
            name="Broadcast Дім 2", address="вул. Нова 6", organization=org_a,
        )
        announcement = Announcement.objects.create(
            building=building, title="Тест broadcast ids", body="—",
        )

        with patch(
            "apps.notifications.tasks.send_telegram_broadcast.delay",
        ) as mock_broadcast:
            notify_building_tenants_announcement(str(announcement.pk))
            mock_broadcast.assert_called_once()
            _, chat_ids_used, _ = mock_broadcast.call_args.args
            assert set(chat_ids_used) == expected_ids
