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
    notify_building_tenants_announcement,
    notify_dispatchers_new_issue,
    notify_tenant_issue_status_changed,
    notify_tenant_pass_status,
    notify_worker_assigned,
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
    only ever reaches its own org's tenants."""

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
        bot_factory(org_a, bot_username="AlphaBot")
        bot_factory(org_b, bot_username="BetaBot")

        building_a = Building.objects.create(
            name="Дім А-1", address="вул. Ринок 1", organization=org_a,
        )
        announcement = Announcement.objects.create(
            building=building_a, title="Плановий ремонт ліфта", body="—",
        )

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_building_tenants_announcement(str(announcement.pk))
            assert mock_delay.call_count == 1
            # Only org_a's tenant was addressed.
            assert mock_delay.call_args.args[1] == 101

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
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_building_tenants_announcement(str(announcement.pk))
            assert mock_delay.call_args.args[0] == str(bot_a.id)

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
            "apps.notifications.tasks.send_telegram_message.delay",
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
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_building_tenants_announcement(str(announcement.pk))
            mock_delay.assert_not_called()


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
