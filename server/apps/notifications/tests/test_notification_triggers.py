"""TDD red-phase tests for new notification trigger behaviours.

These tests are intentionally written BEFORE the production code changes
and are expected to FAIL until the following features are implemented:

Issue tasks:
  * notify_tenant_issue_status_changed  — also notifies assigned_to
  * notify_worker_assigned              — message body contains a deep-link

Announcement task:
  * notify_building_tenants_announcement — respects announcement.notify_subscribers
  * notify_building_tenants_announcement — scoped to entrance / building / org-wide
                                           (no occupation="tenant" hard-filter)

Run with:
    pytest server/apps/notifications/tests/test_notification_triggers.py -v
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.apartments.models import Building, Entrance
from apps.issues.models import Issue
from apps.notifications.bot_resolver import TELEGRAM_FEATURE_FLAG
from apps.notifications.models import OrganizationBot, TelegramProfile
from apps.notifications.tasks import (
    notify_building_tenants_announcement,
    notify_tenant_issue_status_changed,
    notify_worker_assigned,
)
from apps.organizations.models import Organization, OrganizationType
from apps.posts.models import Announcement
from apps.profiles.models import Profile

User = get_user_model()


# ── Helpers ────────────────────────────────────────────────────────────────


def _mk_user(
    username: str,
    email: str,
    *,
    is_staff: bool = False,
    occupation: str = "tenant",
):
    """Create a user with the given params and set their profile occupation."""
    user = User.objects.create_user(
        username=username,
        email=email,
        password="Demo1234!",
        first_name="Test",
        last_name="User",
        is_staff=is_staff,
    )
    profile = Profile.objects.get(user=user)
    profile.occupation = occupation
    profile.save(update_fields=["occupation"])
    return user


# ── Fixtures ───────────────────────────────────────────────────────────────

# NEW FIXTURE: org_trigger — separate fixture so these tests don't depend on
# test_tasks.py fixtures. Marked as "NEW" below.


@pytest.fixture
def org_trigger(db):
    """NEW fixture — org with Telegram feature enabled for trigger tests."""
    return Organization.objects.create(
        name="ОСББ Trigger",
        slug="osbb-trigger",
        type=OrganizationType.HOUSING_COMPLEX,
        features={TELEGRAM_FEATURE_FLAG: True},
    )


@pytest.fixture
def org_trigger_b(db):
    """NEW fixture — second org used for isolation checks in trigger tests."""
    return Organization.objects.create(
        name="ОСББ Trigger B",
        slug="osbb-trigger-b",
        type=OrganizationType.HOUSING_COMPLEX,
        features={TELEGRAM_FEATURE_FLAG: True},
    )


@pytest.fixture
def bot_trigger(db, org_trigger):
    """NEW fixture — configured primary bot for org_trigger."""
    bot = OrganizationBot(
        organization=org_trigger,
        bot_username="TriggerTestBot",
        is_active=True,
        is_primary=True,
    )
    bot.bot_token = "111111111:AAF-trigger-test-token"
    bot.save()
    return bot


@pytest.fixture
def building_trigger(db, org_trigger):
    """NEW fixture — building belonging to org_trigger."""
    return Building.objects.create(
        name="Trigger Building",
        address="вул. Тригер 1",
        organization=org_trigger,
    )


@pytest.fixture
def entrance_trigger(db, building_trigger):
    """NEW fixture — entrance inside building_trigger."""
    return Entrance.objects.create(
        building=building_trigger,
        name="1",
    )


# ══════════════════════════════════════════════════════════════════════════════
# ISSUE TASKS
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestStatusChangeNotifiesAssignedTo:
    """Test 1: notify_tenant_issue_status_changed должен уведомлять assigned_to.

    RED PHASE: fails because the current implementation only notifies
    issue.reported_by and ignores assigned_to entirely.
    """

    def test_status_change_also_notifies_assigned_to(
        self, org_trigger, bot_trigger,
    ):
        """When status changes and assigned_to has an active profile with
        notify_issues=True, send_telegram_message.delay must be called
        TWICE — once for reporter, once for assigned_to.
        """
        reporter = _mk_user("reporter_1", "reporter1@demo.com")
        worker = _mk_user("worker_1", "worker1@demo.com", is_staff=True)

        TelegramProfile.objects.create(
            user=reporter, organization=org_trigger, chat_id=1001,
            is_active=True, notify_issues=True,
        )
        TelegramProfile.objects.create(
            user=worker, organization=org_trigger, chat_id=1002,
            is_active=True, notify_issues=True,
        )

        issue = Issue.objects.create(
            title="Leak in bathroom",
            description="Water everywhere",
            reported_by=reporter,
            assigned_to=worker,
            organization=org_trigger,
        )

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_tenant_issue_status_changed(
                str(issue.pk), "reported", "in_progress",
            )
            # Must notify BOTH reporter and assigned_to.
            assert mock_delay.call_count == 2, (
                f"Expected 2 calls (reporter + assigned_to), "
                f"got {mock_delay.call_count}. "
                f"Task currently only notifies the reporter."
            )
            chat_ids_called = {call.args[1] for call in mock_delay.call_args_list}
            assert 1001 in chat_ids_called, "Reporter (chat_id=1001) not notified"
            assert 1002 in chat_ids_called, "Assigned worker (chat_id=1002) not notified"


@pytest.mark.django_db
class TestStatusChangeNoDuplicateIfReporterIsAssignee:
    """Test 2: no duplicate notification when reporter == assigned_to.

    RED PHASE: fails because assigned_to notification logic doesn't exist yet.
    Once added naively, it might duplicate. This test pins the dedup guarantee.
    """

    def test_status_change_no_duplicate_if_reporter_is_assignee(
        self, org_trigger, bot_trigger,
    ):
        """When reporter and assigned_to are the same user, only ONE message
        must be sent — not two.
        """
        user = _mk_user("reporter_assignee", "ra@demo.com", is_staff=True)
        TelegramProfile.objects.create(
            user=user, organization=org_trigger, chat_id=2001,
            is_active=True, notify_issues=True,
        )

        issue = Issue.objects.create(
            title="Self-assigned issue",
            description="I found it, I fix it",
            reported_by=user,
            assigned_to=user,
            organization=org_trigger,
        )

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_tenant_issue_status_changed(
                str(issue.pk), "reported", "accepted",
            )
            assert mock_delay.call_count == 1, (
                f"Expected exactly 1 call when reporter == assigned_to, "
                f"got {mock_delay.call_count}."
            )


@pytest.mark.django_db
class TestWorkerAssignedMessageContainsLink:
    """Test 3: notify_worker_assigned message must include a deep-link URL.

    RED PHASE: fails because the current task body builds a text without
    any PLATFORM_PUBLIC_URL link to the issue.
    """

    @override_settings(PLATFORM_PUBLIC_URL="https://apartmentos.org")
    def test_worker_assigned_message_contains_link(
        self, org_trigger, bot_trigger,
    ):
        """With PLATFORM_PUBLIC_URL set, the notification text must contain
        the canonical deep-link ``https://apartmentos.org/issue/<id>``.
        """
        worker = _mk_user("worker_link", "wlink@demo.com", is_staff=True)
        TelegramProfile.objects.create(
            user=worker, organization=org_trigger, chat_id=3001,
            is_active=True, notify_issues=True,
        )

        reporter = _mk_user("reporter_link", "rlink@demo.com")
        issue = Issue.objects.create(
            title="Broken elevator",
            description="Stuck on floor 5",
            reported_by=reporter,
            assigned_to=worker,
            organization=org_trigger,
        )

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            notify_worker_assigned(str(issue.pk))
            mock_delay.assert_called_once()
            text = mock_delay.call_args.args[2]
            expected_link = f"https://apartmentos.org/issue/{issue.id}"
            assert expected_link in text, (
                f"Expected deep-link '{expected_link}' in message text.\n"
                f"Got: {text!r}\n"
                "Task currently does not include PLATFORM_PUBLIC_URL links."
            )


@pytest.mark.django_db
class TestWorkerAssignedNoLinkIfNoPlatformUrl:
    """Test 4: notify_worker_assigned must not crash when PLATFORM_PUBLIC_URL is unset.

    RED PHASE: This test may pass today IF the task doesn't read
    PLATFORM_PUBLIC_URL at all — but once Test 3 is implemented the
    no-URL path must be explicitly guarded. Included here so the guard
    is tested from day one.
    """

    @override_settings(PLATFORM_PUBLIC_URL="")
    def test_worker_assigned_no_link_if_no_platform_url(
        self, org_trigger, bot_trigger,
    ):
        """With an empty PLATFORM_PUBLIC_URL the task must still fire the
        notification (no exception) but the text must NOT contain a URL
        starting with 'http'.

        NOTE: this test intentionally passes if PLATFORM_PUBLIC_URL is
        simply not read — but will catch regressions once the link logic
        is added without a proper guard.
        """
        worker = _mk_user("worker_nourl", "wnourl@demo.com", is_staff=True)
        TelegramProfile.objects.create(
            user=worker, organization=org_trigger, chat_id=4001,
            is_active=True, notify_issues=True,
        )

        reporter = _mk_user("reporter_nourl", "rnourl@demo.com")
        issue = Issue.objects.create(
            title="No URL issue",
            description="Test",
            reported_by=reporter,
            assigned_to=worker,
            organization=org_trigger,
        )

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            # Must NOT raise even without PLATFORM_PUBLIC_URL.
            notify_worker_assigned(str(issue.pk))
            mock_delay.assert_called_once(), (
                "Task must still send a message even without PLATFORM_PUBLIC_URL."
            )
            text = mock_delay.call_args.args[2]
            # When URL is absent, the text must not contain a broken link.
            assert f"/issue/{issue.id}" not in text, (
                "Message must not include a partial/broken link when "
                "PLATFORM_PUBLIC_URL is empty."
            )


# ══════════════════════════════════════════════════════════════════════════════
# ANNOUNCEMENT TASKS
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestAnnouncementNotifyFalse:
    """Test 5: When announcement.notify_subscribers=False, no task is fired.

    RED PHASE: fails because Announcement model doesn't have a
    ``notify_subscribers`` field yet. The task also ignores this flag.
    """

    def test_announcement_notify_false_no_task_fired(
        self, org_trigger, bot_trigger, building_trigger,
    ):
        """Creating an announcement with notify_subscribers=False must result
        in send_telegram_message.delay never being called.

        This test will raise AttributeError / FieldError until:
          1. Announcement.notify_subscribers BooleanField is added via migration.
          2. notify_building_tenants_announcement checks the flag and returns early.
        """
        tenant = _mk_user("tenant_nosub", "nosub@demo.com", occupation="tenant")
        TelegramProfile.objects.create(
            user=tenant, organization=org_trigger, chat_id=5001,
            is_active=True, notify_announcements=True,
        )

        # This line will fail until the migration adds notify_subscribers.
        announcement = Announcement.objects.create(
            building=building_trigger,
            title="Silent announcement",
            body="No one should see this",
            notify_subscribers=False,  # NEW FIELD — does not exist yet
        )

        with patch(
            "apps.notifications.tasks.send_telegram_message.delay",
        ) as mock_delay:
            with patch(
                "apps.notifications.tasks.send_telegram_broadcast.delay",
            ) as mock_broadcast:
                notify_building_tenants_announcement(str(announcement.pk))
                mock_delay.assert_not_called()
                mock_broadcast.assert_not_called()


@pytest.mark.django_db
class TestAnnouncementScopeEntrance:
    """Test 6: Entrance-scoped announcement reaches only that entrance's residents.

    RED PHASE: fails because Announcement model has no ``entrance`` FK and
    the task has no entrance-scoping logic.
    """

    def test_announcement_scope_entrance(
        self, org_trigger, bot_trigger, building_trigger, entrance_trigger,
    ):
        """When announcement.entrance is set, only TelegramProfiles whose
        users live in that entrance receive the notification.

        Two entrances exist; tenant_in is linked to the target entrance,
        tenant_out to a different one. Only tenant_in's chat_id must appear
        in the broadcast call.

        This test will fail until:
          1. Announcement.entrance ForeignKey is added (nullable).
          2. notify_building_tenants_announcement filters by entrance when set.
        """
        # Second entrance in the same building.
        entrance_other = Entrance.objects.create(
            building=building_trigger,
            name="2",
        )

        # Tenant inside the target entrance — should receive.
        tenant_in = _mk_user("tenant_in_entr", "tin@demo.com", occupation="tenant")
        TelegramProfile.objects.create(
            user=tenant_in, organization=org_trigger, chat_id=6001,
            is_active=True, notify_announcements=True,
        )

        # Tenant in the OTHER entrance — must NOT receive.
        tenant_out = _mk_user("tenant_out_entr", "tout@demo.com", occupation="tenant")
        TelegramProfile.objects.create(
            user=tenant_out, organization=org_trigger, chat_id=6002,
            is_active=True, notify_announcements=True,
        )

        # Link tenants to entrances via Residency (Profile.unit FK was removed in PR-11).
        from apps.apartments.models import Residency, Unit

        # Create units in respective entrances
        unit_in = Unit.objects.create(entrance=entrance_trigger, number="11")
        unit_out = Unit.objects.create(entrance=entrance_other, number="21")

        # Link tenant_in to entrance_trigger via Residency
        Residency.objects.create(user=tenant_in, unit=unit_in, is_primary=True)
        # Link tenant_out to entrance_other via Residency
        Residency.objects.create(user=tenant_out, unit=unit_out, is_primary=True)

        # This constructor call FAILS until Announcement.entrance exists.
        announcement = Announcement.objects.create(
            building=building_trigger,
            title="Entrance 1 only",
            body="For your entrance only",
            entrance=entrance_trigger,  # NEW FIELD — does not exist yet
            notify_subscribers=True,
        )

        with patch(
            "apps.notifications.tasks.send_telegram_broadcast.delay",
        ) as mock_broadcast:
            notify_building_tenants_announcement(str(announcement.pk))
            mock_broadcast.assert_called_once()
            _bot_id, chat_ids, _text = mock_broadcast.call_args.args
            assert 6001 in chat_ids, "tenant_in should receive entrance-scoped announcement"
            assert 6002 not in chat_ids, (
                "tenant_out (different entrance) must NOT receive "
                "an entrance-scoped announcement"
            )


@pytest.mark.django_db
class TestAnnouncementScopeBuilding:
    """Test 7: Building-scoped announcement (entrance=None) reaches all building residents.

    RED PHASE: This test may partially pass today since the current task
    already filters by building's org — but it will fail once the entrance
    field is introduced and the task incorrectly requires it to be set.
    More importantly this test documents the expected behaviour.
    """

    def test_announcement_scope_building(
        self, org_trigger, org_trigger_b, building_trigger,
    ):
        """When announcement.building is set and announcement.entrance is None,
        every subscriber in that building's org receives the broadcast.
        Subscribers of a *different* org (org_trigger_b) must not receive.

        Two bots are created — one per org.
        """
        from apps.notifications.models import OrganizationBot as OrgBot

        # Bot for org_trigger.
        bot_a = OrgBot(
            organization=org_trigger,
            bot_username="ScopeBuildingBotA",
            is_active=True,
            is_primary=True,
        )
        bot_a.bot_token = "222:AAG-building-scope-a"
        bot_a.save()

        # Bot for org_trigger_b.
        bot_b = OrgBot(
            organization=org_trigger_b,
            bot_username="ScopeBuildingBotB",
            is_active=True,
            is_primary=True,
        )
        bot_b.bot_token = "333:AAH-building-scope-b"
        bot_b.save()

        # Two tenants in org_trigger (same building).
        for i in range(2):
            u = _mk_user(f"bld_t{i}", f"bld_t{i}@demo.com", occupation="tenant")
            TelegramProfile.objects.create(
                user=u, organization=org_trigger, chat_id=7000 + i,
                is_active=True, notify_announcements=True,
            )

        # One tenant in org_trigger_b — must NOT receive.
        other = _mk_user("bld_other", "bld_other@demo.com", occupation="tenant")
        TelegramProfile.objects.create(
            user=other, organization=org_trigger_b, chat_id=7099,
            is_active=True, notify_announcements=True,
        )

        # Building-scoped announcement (entrance=None, or field absent).
        # The Announcement.entrance field may not exist yet, so we fall back
        # to the current constructor. If entrance field exists it defaults None.
        announcement = Announcement.objects.create(
            building=building_trigger,
            title="Building-wide notice",
            body="Everybody in this building",
            notify_subscribers=True,
        )

        with patch(
            "apps.notifications.tasks.send_telegram_broadcast.delay",
        ) as mock_broadcast:
            notify_building_tenants_announcement(str(announcement.pk))
            mock_broadcast.assert_called_once()
            _bot_id, chat_ids, _text = mock_broadcast.call_args.args
            assert _bot_id == str(bot_a.id), "Must use org_trigger's bot"
            assert set(chat_ids) == {7000, 7001}, (
                "Must reach exactly the two org_trigger tenants "
                f"(got {chat_ids!r})"
            )
            assert 7099 not in chat_ids, "Tenant from org_trigger_b must not receive"


@pytest.mark.django_db
class TestAnnouncementScopeOrgWide:
    """Test 8: Org-wide announcement (no building, no entrance) reaches all org subscribers.

    RED PHASE: fails because:
      1. Announcement.building is currently non-nullable — an org-wide
         announcement (building=None) cannot be created.
      2. The task derives org from announcement.building.organization — if
         building is None this lookup crashes.
      3. The current task hard-filters by occupation="tenant", which would
         silently exclude staff subscribers. The new behaviour removes that filter.
    """

    def test_announcement_scope_org_wide(self, org_trigger, bot_trigger):
        """An announcement without building and entrance must reach ALL active
        notify_announcements=True subscribers of the org — regardless of
        their occupation (tenant, staff, etc.).

        This tests that the occupation="tenant" filter is removed for
        org-wide announcements.
        """
        # Tenant subscriber.
        tenant = _mk_user("ow_tenant", "ow_tenant@demo.com", occupation="tenant")
        TelegramProfile.objects.create(
            user=tenant, organization=org_trigger, chat_id=8001,
            is_active=True, notify_announcements=True,
        )
        # Staff subscriber (should also receive org-wide announcements).
        staff = _mk_user("ow_staff", "ow_staff@demo.com", is_staff=True, occupation="staff")
        TelegramProfile.objects.create(
            user=staff, organization=org_trigger, chat_id=8002,
            is_active=True, notify_announcements=True,
        )
        # Opted-out tenant — must NOT receive.
        opted_out = _mk_user("ow_optout", "ow_optout@demo.com", occupation="tenant")
        TelegramProfile.objects.create(
            user=opted_out, organization=org_trigger, chat_id=8003,
            is_active=True, notify_announcements=False,
        )

        # Org-wide announcement: building=None (NEW — field must become nullable).
        # This will raise IntegrityError / ValueError until the migration
        # makes Announcement.building nullable and adds the org FK.
        announcement = Announcement.objects.create(
            organization=org_trigger,   # NEW FIELD — org-level scoping
            building=None,              # NULL = org-wide
            title="Org-wide update",
            body="This goes to everyone in the org",
            notify_subscribers=True,
        )

        with patch(
            "apps.notifications.tasks.send_telegram_broadcast.delay",
        ) as mock_broadcast:
            notify_building_tenants_announcement(str(announcement.pk))
            mock_broadcast.assert_called_once()
            _bot_id, chat_ids, _text = mock_broadcast.call_args.args
            assert _bot_id == str(bot_trigger.id)
            # Both tenant AND staff must be included (no occupation filter).
            assert set(chat_ids) == {8001, 8002}, (
                f"Org-wide announcement must reach all subscribers "
                f"regardless of occupation. Got: {chat_ids!r}"
            )
            # Opted-out user excluded.
            assert 8003 not in chat_ids
