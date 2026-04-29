"""Tests for billing limit-warning signals (PR-13a, Phase 4).

Two signals:
    * post_save on apartments.Unit — warns when count > plan.max_apartments
    * post_save on organizations.OrganizationMembership — warns when
      distinct active users > plan.max_users

Both are soft-warn: ``send_telegram_message_task.delay(text)``. We mock
that task and assert the call (or non-call) plus the message format.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest


def _ensure_subscription(org, plan):
    """Helper: ensure ``org`` has a subscription with ``plan``.

    Used by the limit-warning signal tests where the trial auto-create
    signal exited silently (no Starter plan seeded). Attaches a fresh
    subscription with the provided plan.
    """
    from apps.billing.models import OrganizationSubscription
    today = date.today()
    sub, _ = OrganizationSubscription.objects.get_or_create(
        organization=org,
        defaults={
            "plan": plan,
            "billing_period": OrganizationSubscription.BILLING_MONTHLY,
            "started_at": today,
            "next_billing_at": today + timedelta(days=30),
        },
    )
    if sub.plan_id != plan.pk:
        sub.plan = plan
        sub.save(update_fields=["plan"])
    return sub


@pytest.mark.django_db
class TestApartmentLimitSignal:
    def test_warns_when_unit_count_exceeds_max_apartments(
        self, director,
    ):
        """Tiny limit (max_apartments=1) → 2nd unit triggers warn."""
        from apps.apartments.models import Building, Entrance, Unit
        from apps.billing.models import OrganizationSubscription, SubscriptionPlan
        from apps.organizations.models import Organization

        tiny_plan = SubscriptionPlan.objects.create(
            code="tiny", name="Tiny",
            monthly_price_uah=Decimal("100.00"),
            max_apartments=1, max_users=1,
        )
        org = Organization.objects.create(
            name="Tiny org", type="housing_complex", owner=director,
        )
        # No "starter" plan in DB yet → trial signal exited silently.
        # Manually attach a tiny plan so the limit check has something
        # to compare against.
        sub = _ensure_subscription(org, tiny_plan)

        building = Building.objects.create(
            name="B", address="A", organization=org,
        )
        entrance = Entrance.objects.create(building=building, name="E")
        # First unit — at limit, no warn.
        with patch(
            "apps.notifications.tasks.send_telegram_message_task.delay"
        ) as mock_send:
            Unit.objects.create(entrance=entrance, number="1")
            mock_send.assert_not_called()

        # Second unit — over limit, must warn.
        with patch(
            "apps.notifications.tasks.send_telegram_message_task.delay"
        ) as mock_send:
            Unit.objects.create(entrance=entrance, number="2")
            mock_send.assert_called_once()
            text = mock_send.call_args[0][0]
            assert "квартир" in text
            assert "Tiny" in text  # plan name
            assert "2/1" in text

    def test_no_warn_when_limit_unlimited(self, director):
        from apps.apartments.models import Building, Entrance, Unit
        from apps.billing.models import SubscriptionPlan
        from apps.organizations.models import Organization

        unlimited_plan = SubscriptionPlan.objects.create(
            code="unl", name="Unlimited",
            monthly_price_uah=Decimal("999.00"),
            max_apartments=None, max_users=None,
        )
        org = Organization.objects.create(
            name="Unl org", type="housing_complex", owner=director,
        )
        _ensure_subscription(org, unlimited_plan)

        building = Building.objects.create(
            name="B", address="A", organization=org,
        )
        entrance = Entrance.objects.create(building=building, name="E")

        with patch(
            "apps.notifications.tasks.send_telegram_message_task.delay"
        ) as mock_send:
            for n in range(5):
                Unit.objects.create(entrance=entrance, number=str(n))
            mock_send.assert_not_called()


@pytest.mark.django_db
class TestUserLimitSignal:
    def test_warns_when_distinct_active_users_exceed_max_users(
        self, director,
    ):
        from apps.billing.models import SubscriptionPlan
        from apps.organizations.models import (
            Organization,
            OrganizationMembership,
            OrgRole,
        )
        from django.contrib.auth import get_user_model

        User = get_user_model()
        tiny_plan = SubscriptionPlan.objects.create(
            code="usrtiny", name="UsrTiny",
            monthly_price_uah=Decimal("100.00"),
            max_apartments=10, max_users=1,
        )
        org = Organization.objects.create(
            name="Usr lim org", type="housing_complex", owner=director,
        )
        _ensure_subscription(org, tiny_plan)

        u1 = User.objects.create_user(username="u1", email="u1@x.com", password="x")
        u2 = User.objects.create_user(username="u2", email="u2@x.com", password="x")

        with patch(
            "apps.notifications.tasks.send_telegram_message_task.delay"
        ) as mock_send:
            # First active membership — at limit (1/1), no warn.
            OrganizationMembership.objects.create(
                user=u1, organization=org, role=OrgRole.RESIDENT, is_active=True,
            )
            mock_send.assert_not_called()

            # Second distinct user — over limit.
            OrganizationMembership.objects.create(
                user=u2, organization=org, role=OrgRole.RESIDENT, is_active=True,
            )
            mock_send.assert_called_once()
            text = mock_send.call_args[0][0]
            assert "користувачів" in text
            assert "2/1" in text

    def test_no_warn_for_inactive_membership(self, director):
        from apps.billing.models import SubscriptionPlan
        from apps.organizations.models import (
            Organization,
            OrganizationMembership,
            OrgRole,
        )
        from django.contrib.auth import get_user_model

        User = get_user_model()
        plan = SubscriptionPlan.objects.create(
            code="usrtiny2", name="UsrTiny2",
            monthly_price_uah=Decimal("100.00"),
            max_apartments=10, max_users=0,
        )
        org = Organization.objects.create(
            name="Inactive org", type="housing_complex", owner=director,
        )
        _ensure_subscription(org, plan)

        u1 = User.objects.create_user(username="ui1", email="ui1@x.com", password="x")

        with patch(
            "apps.notifications.tasks.send_telegram_message_task.delay"
        ) as mock_send:
            OrganizationMembership.objects.create(
                user=u1, organization=org, role=OrgRole.RESIDENT, is_active=False,
            )
            mock_send.assert_not_called()


@pytest.mark.django_db
class TestTrialAutoCreateSignal:
    def test_no_subscription_when_starter_plan_missing(self, director):
        """Without a Starter plan in DB, the signal silently exits."""
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="Pre-seed org", type="housing_complex", owner=director,
        )
        assert not hasattr(org, "subscription") or \
            not org.__class__._meta.model.objects.filter(pk=org.pk).exists() or \
            not hasattr(org, "subscription") or org.subscription is None or \
            getattr(org, "subscription", None) is None or True
        # Above is safe-guard noise; the meaningful assertion:
        from apps.billing.models import OrganizationSubscription
        assert not OrganizationSubscription.objects.filter(organization=org).exists()

    def test_subscription_created_when_starter_exists(
        self, director, starter_plan,
    ):
        from apps.billing.models import OrganizationSubscription
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="Auto-trial org", type="housing_complex", owner=director,
        )
        sub = OrganizationSubscription.objects.get(organization=org)
        assert sub.trial_ends_at == date.today() + timedelta(days=60)
        assert sub.is_in_trial is True
