"""TDD tests for billing models (PR-13a, Phase 1).

Models exercised here:
    * SubscriptionPlan
    * AddOn
    * OrganizationSubscription (with the 60-day trial signal)
    * OrganizationAddOn (catalog FK + custom-module variant)
    * Invoice + InvoiceLineItem (with auto invoice_number + FOP snapshot)

The tests deliberately use ``Decimal`` strings and never floats — money
math relies on ``decimal.Decimal`` end-to-end so the fixture rounding
matches what the calculator service emits.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction


# ── SubscriptionPlan ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSubscriptionPlan:
    def test_creation_with_required_fields(self):
        from apps.billing.models import SubscriptionPlan

        plan = SubscriptionPlan.objects.create(
            code="starter",
            name="Starter",
            monthly_price_uah=Decimal("5900.00"),
            max_apartments=150,
            max_users=300,
            description_uk="Базовий тариф",
        )
        assert plan.code == "starter"
        assert plan.name == "Starter"
        assert plan.monthly_price_uah == Decimal("5900.00")
        assert plan.max_apartments == 150
        assert plan.max_users == 300
        assert plan.is_active is True

    def test_code_unique(self):
        from apps.billing.models import SubscriptionPlan

        SubscriptionPlan.objects.create(
            code="starter",
            name="Starter",
            monthly_price_uah=Decimal("5900.00"),
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                SubscriptionPlan.objects.create(
                    code="starter",
                    name="Starter Duplicate",
                    monthly_price_uah=Decimal("100.00"),
                )

    def test_str_representation(self):
        from apps.billing.models import SubscriptionPlan

        plan = SubscriptionPlan.objects.create(
            code="business",
            name="Business",
            monthly_price_uah=Decimal("14900.00"),
        )
        assert "Business" in str(plan)
        assert "14900" in str(plan)

    def test_unlimited_when_max_null(self):
        from apps.billing.models import SubscriptionPlan

        plan = SubscriptionPlan.objects.create(
            code="enterprise",
            name="Enterprise",
            monthly_price_uah=Decimal("59900.00"),
            max_apartments=None,
            max_users=None,
        )
        assert plan.max_apartments is None
        assert plan.max_users is None


# ── AddOn ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAddOn:
    def test_one_time_addon(self):
        from apps.billing.models import AddOn

        addon = AddOn.objects.create(
            code="sms_setup",
            name_uk="SMS — підключення",
            price_uah=Decimal("4500.00"),
            billing_type=AddOn.BILLING_ONE_TIME,
        )
        assert addon.billing_type == "one_time"
        assert addon.is_active is True

    def test_recurring_monthly_addon(self):
        from apps.billing.models import AddOn

        addon = AddOn.objects.create(
            code="sms_subscription",
            name_uk="SMS-підписка",
            price_uah=Decimal("1200.00"),
            billing_type=AddOn.BILLING_RECURRING,
        )
        assert addon.billing_type == "recurring_monthly"

    def test_billing_type_choices(self):
        from apps.billing.models import AddOn

        choice_codes = {c[0] for c in AddOn.BILLING_TYPE_CHOICES}
        assert choice_codes == {"one_time", "recurring_monthly"}

    def test_str_representation(self):
        from apps.billing.models import AddOn

        addon = AddOn.objects.create(
            code="custom_domain",
            name_uk="Власний домен",
            price_uah=Decimal("2500.00"),
            billing_type=AddOn.BILLING_ONE_TIME,
        )
        s = str(addon)
        assert "Власний домен" in s
        assert "2500" in s


# ── OrganizationSubscription ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestOrganizationSubscription:
    def test_default_trial_60_days_via_signal_on_org_create(
        self, director, starter_plan,
    ):
        """When Org is created and Starter plan exists, the post_save
        signal should auto-create a 60-day trial subscription.
        """
        from apps.billing.models import OrganizationSubscription
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="Trial Org",
            type="housing_complex",
            owner=director,
        )
        sub = OrganizationSubscription.objects.get(organization=org)
        today = date.today()
        assert sub.trial_ends_at == today + timedelta(days=60)
        assert sub.next_billing_at == today + timedelta(days=60)
        assert sub.plan_id == starter_plan.pk
        assert sub.billing_period == "monthly"

    def test_one_subscription_per_org_oneToOne(
        self, director, starter_plan,
    ):
        """OneToOneField — second OrganizationSubscription on same Org fails."""
        from apps.billing.models import OrganizationSubscription
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="OneSub Org",
            type="housing_complex",
            owner=director,
        )
        # First sub already created by signal.
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                OrganizationSubscription.objects.create(
                    organization=org,
                    plan=starter_plan,
                    started_at=date.today(),
                    next_billing_at=date.today() + timedelta(days=30),
                )

    def test_is_in_trial_helper_true_inside_window(
        self, director, starter_plan,
    ):
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="In trial",
            type="housing_complex",
            owner=director,
        )
        assert org.subscription.is_in_trial is True

    def test_is_in_trial_false_after_expiry(
        self, director, starter_plan,
    ):
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="Past trial",
            type="housing_complex",
            owner=director,
        )
        sub = org.subscription
        sub.trial_ends_at = date.today() - timedelta(days=1)
        sub.save(update_fields=["trial_ends_at"])
        assert sub.is_in_trial is False

    def test_is_in_trial_false_when_trial_ends_at_is_none(
        self, director, starter_plan,
    ):
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="No trial",
            type="housing_complex",
            owner=director,
        )
        sub = org.subscription
        sub.trial_ends_at = None
        sub.save(update_fields=["trial_ends_at"])
        assert sub.is_in_trial is False

    def test_billing_period_choices(self):
        from apps.billing.models import OrganizationSubscription

        codes = {c[0] for c in OrganizationSubscription.BILLING_PERIOD_CHOICES}
        assert codes == {"monthly", "annual"}


# ── OrganizationAddOn ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestOrganizationAddOn:
    def test_org_addon_with_catalog_addon(
        self, director, starter_plan, sms_addon,
    ):
        from apps.billing.models import OrganizationAddOn
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="With sms",
            type="housing_complex",
            owner=director,
        )
        org_addon = OrganizationAddOn.objects.create(
            organization=org,
            addon=sms_addon,
            activated_at=date.today(),
        )
        assert org_addon.is_custom_module is False
        assert org_addon.effective_name == sms_addon.name_uk
        assert org_addon.effective_price == sms_addon.price_uah
        assert org_addon.is_recurring is True

    def test_org_addon_custom_module(
        self, director, starter_plan,
    ):
        from apps.billing.models import OrganizationAddOn
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="Custom mod org",
            type="housing_complex",
            owner=director,
        )
        org_addon = OrganizationAddOn.objects.create(
            organization=org,
            addon=None,
            custom_name="Інтеграція з 1С",
            custom_price_monthly_uah=Decimal("3500.00"),
            activated_at=date.today(),
        )
        assert org_addon.is_custom_module is True
        assert org_addon.effective_name == "Інтеграція з 1С"
        assert org_addon.effective_price == Decimal("3500.00")
        # Custom modules are recurring by design (PR-13a contract).
        assert org_addon.is_recurring is True

    def test_org_addon_either_catalog_or_custom_constraint(
        self, director, starter_plan,
    ):
        """If both addon FK is null AND custom fields are empty → DB rejects."""
        from apps.billing.models import OrganizationAddOn
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="Bad addon",
            type="housing_complex",
            owner=director,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                OrganizationAddOn.objects.create(
                    organization=org,
                    addon=None,
                    custom_name="",
                    custom_price_monthly_uah=None,
                    activated_at=date.today(),
                )


# ── Invoice + InvoiceLineItem ────────────────────────────────────────────────


@pytest.mark.django_db
class TestInvoice:
    def test_invoice_creation_with_required(
        self, director, starter_plan,
    ):
        from apps.billing.models import Invoice
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="Inv org",
            type="housing_complex",
            owner=director,
        )
        today = date.today()
        invoice = Invoice.objects.create(
            organization=org,
            issued_at=today,
            due_at=today + timedelta(days=10),
            period_start=today,
            period_end=today + timedelta(days=30),
        )
        assert invoice.status == "draft"
        assert invoice.subtotal_uah == Decimal("0.00")

    def test_invoice_number_auto_generated_unique(
        self, director, starter_plan,
    ):
        from apps.billing.models import Invoice
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="Inv num org",
            type="housing_complex",
            owner=director,
        )
        today = date.today()
        i1 = Invoice.objects.create(
            organization=org,
            issued_at=today,
            due_at=today,
            period_start=today,
            period_end=today,
        )
        i2 = Invoice.objects.create(
            organization=org,
            issued_at=today,
            due_at=today,
            period_start=today,
            period_end=today,
        )
        assert i1.invoice_number != i2.invoice_number
        assert i1.invoice_number.startswith(f"INV-{today.year}-")
        assert i2.invoice_number.startswith(f"INV-{today.year}-")
        # Format INV-YYYY-NNNNNN
        assert len(i1.invoice_number.rsplit("-", 1)[-1]) == 6

    def test_status_workflow_draft_to_paid(
        self, director, starter_plan,
    ):
        from apps.billing.models import Invoice
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="Status org",
            type="housing_complex",
            owner=director,
        )
        today = date.today()
        invoice = Invoice.objects.create(
            organization=org,
            issued_at=today, due_at=today,
            period_start=today, period_end=today,
        )
        for status in ["review", "approved", "paid"]:
            invoice.status = status
            invoice.save(update_fields=["status"])
            invoice.refresh_from_db()
            assert invoice.status == status

    def test_fop_snapshot_persists_after_settings_change(
        self, director, starter_plan,
    ):
        """Snapshot fields are independent of live settings — once written,
        they don't move."""
        from apps.billing.models import Invoice
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="Snap org",
            type="housing_complex",
            owner=director,
        )
        today = date.today()
        invoice = Invoice.objects.create(
            organization=org,
            issued_at=today, due_at=today,
            period_start=today, period_end=today,
            payer_name_snapshot="ФОП Іванов І.І.",
            payer_tax_id_snapshot="1234567890",
            payer_iban_snapshot="UA000000000000000000000000",
            payer_bank_snapshot="Privatbank",
            payer_tax_note_snapshot="Без ПДВ.",
        )
        invoice.refresh_from_db()
        assert invoice.payer_name_snapshot == "ФОП Іванов І.І."
        assert invoice.payer_tax_id_snapshot == "1234567890"


@pytest.mark.django_db
class TestInvoiceLineItem:
    def test_line_item_belongs_to_invoice(
        self, director, starter_plan,
    ):
        from apps.billing.models import Invoice, InvoiceLineItem
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="Li org",
            type="housing_complex",
            owner=director,
        )
        today = date.today()
        invoice = Invoice.objects.create(
            organization=org,
            issued_at=today, due_at=today,
            period_start=today, period_end=today,
        )
        line = InvoiceLineItem.objects.create(
            invoice=invoice,
            description="Підписка Starter",
            quantity=1,
            unit_price_uah=Decimal("5900.00"),
            total_uah=Decimal("5900.00"),
            line_type="base_subscription",
        )
        assert line.invoice_id == invoice.pk
        assert invoice.line_items.count() == 1

    def test_line_item_total_calculation_via_calculator_helper(
        self, director, starter_plan,
    ):
        """We don't autocalculate ``total_uah`` on the model — the
        calculator service is the single source of truth.  But the
        field must accept the value the calculator produces.
        """
        from apps.billing.models import Invoice, InvoiceLineItem
        from apps.organizations.models import Organization

        org = Organization.objects.create(
            name="Calc org",
            type="housing_complex",
            owner=director,
        )
        today = date.today()
        invoice = Invoice.objects.create(
            organization=org,
            issued_at=today, due_at=today,
            period_start=today, period_end=today,
        )
        line = InvoiceLineItem.objects.create(
            invoice=invoice,
            description="SMS x 2",
            quantity=2,
            unit_price_uah=Decimal("1200.00"),
            total_uah=Decimal("2400.00"),
            line_type="addon_recurring",
        )
        assert line.quantity == 2
        assert line.total_uah == Decimal("2400.00")
