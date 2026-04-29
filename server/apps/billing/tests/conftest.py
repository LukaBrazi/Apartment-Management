"""Shared fixtures for billing app tests (PR-13a).

The fixtures here intentionally avoid pulling in the broader
``organizations/tests/conftest.py`` so the billing test suite can be
run in isolation. Where org / user instances are needed we create
slim ones inline — the focus is billing behavior, not org plumbing.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


# ── Plan + AddOn fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def starter_plan(db):
    from apps.billing.models import SubscriptionPlan

    return SubscriptionPlan.objects.create(
        code="starter",
        name="Starter",
        monthly_price_uah=Decimal("5900.00"),
        max_apartments=150,
        max_users=300,
        description_uk="Базовий тариф",
    )


@pytest.fixture
def business_plan(db):
    from apps.billing.models import SubscriptionPlan

    return SubscriptionPlan.objects.create(
        code="business",
        name="Business",
        monthly_price_uah=Decimal("14900.00"),
        max_apartments=500,
        max_users=1000,
        description_uk="Бізнес тариф",
    )


@pytest.fixture
def sms_addon(db):
    from apps.billing.models import AddOn

    return AddOn.objects.create(
        code="sms_subscription",
        name_uk="SMS-підписка",
        price_uah=Decimal("1200.00"),
        billing_type=AddOn.BILLING_RECURRING,
        description_uk="Щомісячна SMS-послуга",
    )


@pytest.fixture
def sms_setup_addon(db):
    from apps.billing.models import AddOn

    return AddOn.objects.create(
        code="sms_setup",
        name_uk="SMS — підключення",
        price_uah=Decimal("4500.00"),
        billing_type=AddOn.BILLING_ONE_TIME,
        description_uk="Одноразова активація SMS",
    )


# ── Organization + subscription helpers ───────────────────────────────────────


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="billing_super",
        email="billing_super@apartmentos.org",
        password="testpass",
    )


@pytest.fixture
def director(db):
    return User.objects.create_user(
        username="billing_dir",
        email="billing_dir@apartmentos.org",
        password="testpass",
    )


@pytest.fixture
def org_no_signal(db, director):
    """Fresh Organization. Trial signal will fire — but if Starter plan
    is not seeded yet (no fixture pulled in), the signal exits early
    so the org has no subscription. Use ``org_with_starter`` when you
    need a plan attached.
    """
    from apps.organizations.models import Organization

    return Organization.objects.create(
        name="Billing Test Org",
        type="housing_complex",
        owner=director,
    )


@pytest.fixture
def org_with_starter(db, director, starter_plan):
    """Org + Starter subscription, NOT in trial.

    The post_save signal would put it on a 60-day trial; we explicitly
    push ``trial_ends_at`` into the past so calculator tests exercise
    the live-billing path.
    """
    from apps.billing.models import OrganizationSubscription
    from apps.organizations.models import Organization

    org = Organization.objects.create(
        name="Org with Starter",
        type="housing_complex",
        owner=director,
    )
    sub = org.subscription
    sub.trial_ends_at = date.today() - timedelta(days=1)
    sub.save(update_fields=["trial_ends_at"])
    return org


@pytest.fixture
def org_in_trial(db, director, starter_plan):
    """Org currently in its 60-day Starter trial."""
    from apps.organizations.models import Organization

    return Organization.objects.create(
        name="Org in trial",
        type="housing_complex",
        owner=director,
    )


@pytest.fixture
def org_with_annual_billing(db, director, starter_plan):
    from apps.billing.models import OrganizationSubscription
    from apps.organizations.models import Organization

    org = Organization.objects.create(
        name="Org annual",
        type="housing_complex",
        owner=director,
    )
    sub = org.subscription
    sub.billing_period = OrganizationSubscription.BILLING_ANNUAL
    sub.trial_ends_at = date.today() - timedelta(days=1)
    sub.save(update_fields=["billing_period", "trial_ends_at"])
    return org
