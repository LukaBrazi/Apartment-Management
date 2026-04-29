"""TDD tests for the billing calculator service (PR-13a, Phase 2).

The calculator is split into three pure-ish functions:

* ``calculate_recurring_invoice(org, period_start, period_end)`` —
  monthly / annual subscription invoice. Returns ``{line_items,
  subtotal, discount, total}``. Trial → all zeros + a ``trial_credit``
  row so the recipient sees what's happening.
* ``calculate_onboarding_invoice(org, addon_codes)`` — sum of selected
  ``billing_type=one_time`` add-ons.
* ``calculate_proration_on_plan_change(org, new_plan, change_date)`` —
  refund of the unused portion of the old plan plus prorated charge
  of the new plan from change_date through ``next_billing_at``.

All money math goes through ``Decimal`` and rounds with
``quantize(Decimal("0.01"))``. No floats anywhere.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest


# ── calculate_recurring_invoice ──────────────────────────────────────────────


@pytest.mark.django_db
class TestRecurringInvoice:
    def test_starter_no_addons_no_discount(self, org_with_starter):
        from apps.billing.services.calculator import calculate_recurring_invoice

        period_start = date(2026, 5, 1)
        period_end = date(2026, 5, 31)
        result = calculate_recurring_invoice(
            org_with_starter, period_start, period_end,
        )
        assert result["subtotal"] == Decimal("5900.00")
        assert result["discount"] == Decimal("0.00")
        assert result["total"] == Decimal("5900.00")
        assert len(result["line_items"]) == 1
        assert result["line_items"][0]["line_type"] == "base_subscription"
        assert result["line_items"][0]["unit_price"] == Decimal("5900.00")

    def test_with_recurring_addon(self, org_with_starter, sms_addon):
        from apps.billing.models import OrganizationAddOn
        from apps.billing.services.calculator import calculate_recurring_invoice

        OrganizationAddOn.objects.create(
            organization=org_with_starter,
            addon=sms_addon,
            activated_at=date.today(),
        )
        result = calculate_recurring_invoice(
            org_with_starter, date(2026, 5, 1), date(2026, 5, 31),
        )
        # 5900 base + 1200 SMS
        assert result["subtotal"] == Decimal("7100.00")
        assert result["total"] == Decimal("7100.00")
        types = [li["line_type"] for li in result["line_items"]]
        assert "base_subscription" in types
        assert "addon_recurring" in types

    def test_one_time_addon_excluded_from_recurring(
        self, org_with_starter, sms_setup_addon,
    ):
        """One-time add-ons must NOT show up in recurring invoices."""
        from apps.billing.models import OrganizationAddOn
        from apps.billing.services.calculator import calculate_recurring_invoice

        OrganizationAddOn.objects.create(
            organization=org_with_starter,
            addon=sms_setup_addon,
            activated_at=date.today(),
        )
        result = calculate_recurring_invoice(
            org_with_starter, date(2026, 5, 1), date(2026, 5, 31),
        )
        types = [li["line_type"] for li in result["line_items"]]
        assert "addon_one_time" not in types
        assert result["subtotal"] == Decimal("5900.00")

    def test_inactive_addons_excluded(self, org_with_starter, sms_addon):
        from apps.billing.models import OrganizationAddOn
        from apps.billing.services.calculator import calculate_recurring_invoice

        OrganizationAddOn.objects.create(
            organization=org_with_starter,
            addon=sms_addon,
            activated_at=date.today(),
            is_active=False,
        )
        result = calculate_recurring_invoice(
            org_with_starter, date(2026, 5, 1), date(2026, 5, 31),
        )
        # SMS not added
        assert result["subtotal"] == Decimal("5900.00")

    def test_annual_discount_15_percent(self, org_with_annual_billing):
        from apps.billing.services.calculator import calculate_recurring_invoice

        result = calculate_recurring_invoice(
            org_with_annual_billing,
            date(2026, 5, 1),
            date(2027, 4, 30),
        )
        # Subtotal = 5900 (base, monthly basis)
        # Annual discount = 5900 * 0.15 = 885
        # Total = 5900 - 885 = 5015
        assert result["subtotal"] == Decimal("5900.00")
        assert result["discount"] == Decimal("885.00")
        assert result["total"] == Decimal("5015.00")
        types = [li["line_type"] for li in result["line_items"]]
        assert "annual_discount" in types

    def test_during_trial_returns_zero(self, org_in_trial):
        from apps.billing.services.calculator import calculate_recurring_invoice

        result = calculate_recurring_invoice(
            org_in_trial, date(2026, 5, 1), date(2026, 5, 31),
        )
        assert result["subtotal"] == Decimal("0.00")
        assert result["total"] == Decimal("0.00")
        assert len(result["line_items"]) == 1
        assert result["line_items"][0]["line_type"] == "trial_credit"

    def test_custom_module_in_recurring(self, org_with_starter):
        from apps.billing.models import OrganizationAddOn
        from apps.billing.services.calculator import calculate_recurring_invoice

        OrganizationAddOn.objects.create(
            organization=org_with_starter,
            addon=None,
            custom_name="Інтеграція з 1С",
            custom_price_monthly_uah=Decimal("3500.00"),
            activated_at=date.today(),
        )
        result = calculate_recurring_invoice(
            org_with_starter, date(2026, 5, 1), date(2026, 5, 31),
        )
        # 5900 + 3500 = 9400
        assert result["subtotal"] == Decimal("9400.00")
        types = [li["line_type"] for li in result["line_items"]]
        assert "custom_module" in types


# ── calculate_onboarding_invoice ─────────────────────────────────────────────


@pytest.mark.django_db
class TestOnboardingInvoice:
    def test_single_one_time_addon(
        self, org_with_starter, sms_setup_addon,
    ):
        from apps.billing.services.calculator import (
            calculate_onboarding_invoice,
        )

        result = calculate_onboarding_invoice(
            org_with_starter, addon_codes=["sms_setup"],
        )
        assert result["subtotal"] == Decimal("4500.00")
        assert result["total"] == Decimal("4500.00")
        assert len(result["line_items"]) == 1
        assert result["line_items"][0]["line_type"] == "addon_one_time"

    def test_multiple_one_time_addons(
        self, org_with_starter, sms_setup_addon,
    ):
        from apps.billing.models import AddOn
        from apps.billing.services.calculator import (
            calculate_onboarding_invoice,
        )

        AddOn.objects.create(
            code="custom_domain",
            name_uk="Власний домен",
            price_uah=Decimal("2500.00"),
            billing_type=AddOn.BILLING_ONE_TIME,
        )
        result = calculate_onboarding_invoice(
            org_with_starter, addon_codes=["sms_setup", "custom_domain"],
        )
        # 4500 + 2500 = 7000
        assert result["subtotal"] == Decimal("7000.00")
        assert result["total"] == Decimal("7000.00")
        assert len(result["line_items"]) == 2

    def test_recurring_addon_codes_ignored(
        self, org_with_starter, sms_addon,
    ):
        """Passing a recurring addon code shouldn't add it to onboarding."""
        from apps.billing.services.calculator import (
            calculate_onboarding_invoice,
        )

        result = calculate_onboarding_invoice(
            org_with_starter, addon_codes=["sms_subscription"],
        )
        assert result["subtotal"] == Decimal("0.00")
        assert result["line_items"] == []

    def test_unknown_codes_silently_skipped(self, org_with_starter):
        from apps.billing.services.calculator import (
            calculate_onboarding_invoice,
        )

        result = calculate_onboarding_invoice(
            org_with_starter, addon_codes=["nonexistent"],
        )
        assert result["subtotal"] == Decimal("0.00")
        assert result["line_items"] == []

    def test_empty_addon_codes(self, org_with_starter):
        from apps.billing.services.calculator import (
            calculate_onboarding_invoice,
        )

        result = calculate_onboarding_invoice(
            org_with_starter, addon_codes=[],
        )
        assert result["subtotal"] == Decimal("0.00")
        assert result["total"] == Decimal("0.00")
        assert result["line_items"] == []


# ── calculate_proration_on_plan_change ───────────────────────────────────────


@pytest.mark.django_db
class TestProration:
    def test_upgrade_mid_period_charges_extra(
        self, org_with_starter, business_plan,
    ):
        """Switching Starter (5900) → Business (14900) at midpoint
        should refund half of the old (~2950) and charge half of the
        new (~7450). Net = -4500 (org owes).
        """
        from apps.billing.services.calculator import (
            calculate_proration_on_plan_change,
        )

        sub = org_with_starter.subscription
        sub.billing_period = "monthly"
        sub.next_billing_at = date.today() + timedelta(days=15)
        sub.save(update_fields=["billing_period", "next_billing_at"])
        change_date = date.today()

        result = calculate_proration_on_plan_change(
            org_with_starter, business_plan, change_date,
        )
        # 15 days remaining of a 30-day period.
        # refund_old  = 5900  * 15 / 30 = 2950.00
        # charge_new  = 14900 * 15 / 30 = 7450.00
        # net = refund - charge = -4500 (negative means org pays)
        assert result["refund_old"] == Decimal("2950.00")
        assert result["charge_new"] == Decimal("7450.00")
        assert result["net"] == Decimal("-4500.00")

    def test_downgrade_refunds_more_than_charged(
        self, director, business_plan, starter_plan,
    ):
        """Business → Starter mid-period: refund > charge → org gets credit."""
        from apps.billing.models import OrganizationSubscription
        from apps.billing.services.calculator import (
            calculate_proration_on_plan_change,
        )
        from apps.organizations.models import Organization

        # Use the plan-on-create signal then upgrade to business.
        org = Organization.objects.create(
            name="Downgrade org",
            type="housing_complex",
            owner=director,
        )
        sub = org.subscription
        sub.plan = business_plan
        sub.billing_period = "monthly"
        sub.next_billing_at = date.today() + timedelta(days=15)
        sub.trial_ends_at = date.today() - timedelta(days=1)
        sub.save(update_fields=[
            "plan", "billing_period", "next_billing_at", "trial_ends_at",
        ])

        result = calculate_proration_on_plan_change(
            org, starter_plan, date.today(),
        )
        # refund_old = 14900 * 15/30 = 7450
        # charge_new = 5900  * 15/30 = 2950
        # net = +4500 (org gets credit)
        assert result["refund_old"] == Decimal("7450.00")
        assert result["charge_new"] == Decimal("2950.00")
        assert result["net"] == Decimal("4500.00")

    def test_end_of_period_zero_proration(
        self, org_with_starter, business_plan,
    ):
        """Change date == next_billing_at → no proration."""
        from apps.billing.services.calculator import (
            calculate_proration_on_plan_change,
        )

        sub = org_with_starter.subscription
        sub.next_billing_at = date.today()
        sub.save(update_fields=["next_billing_at"])

        result = calculate_proration_on_plan_change(
            org_with_starter, business_plan, date.today(),
        )
        assert result["refund_old"] == Decimal("0.00")
        assert result["charge_new"] == Decimal("0.00")
        assert result["net"] == Decimal("0.00")
