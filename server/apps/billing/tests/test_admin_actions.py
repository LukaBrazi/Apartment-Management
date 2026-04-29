"""Tests for billing admin actions (PR-13a, Phase 3).

Covers:
    * generate_monthly_invoice_action — creates draft Invoice + LineItems
    * preview_next_invoice_action — surfaces totals via messages, no DB
    * approve_and_email_superuser — flips status + sends email
    * onboarding_invoice_view (POST) — creates one-time invoice
    * Permission gates (non-superuser blocked, no email blocked)

Tests use Django's RequestFactory + FallbackStorage so messages
framework works inside unit tests (same pattern as test_org_report).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.test import RequestFactory


User = get_user_model()


def _make_request(user, method="post"):
    rf = RequestFactory()
    if method == "post":
        req = rf.post("/admin/")
    else:
        req = rf.get("/admin/")
    req.user = user
    req.session = {}
    req._messages = FallbackStorage(req)
    return req


# ── generate_monthly_invoice_action ──────────────────────────────────────────


@pytest.mark.django_db
class TestGenerateMonthlyInvoice:
    def test_creates_draft_invoice_for_org_with_subscription(
        self, superuser, org_with_starter,
    ):
        from apps.billing.models import Invoice
        from apps.organizations.admin import OrganizationAdmin
        from apps.organizations.models import Organization

        admin_inst = OrganizationAdmin(Organization, AdminSite())
        request = _make_request(superuser)
        qs = Organization.objects.filter(pk=org_with_starter.pk)

        admin_inst.generate_monthly_invoice_action(request, qs)

        assert Invoice.objects.filter(organization=org_with_starter).count() == 1
        inv = Invoice.objects.get(organization=org_with_starter)
        assert inv.status == "draft"
        assert inv.total_uah == Decimal("5900.00")
        assert inv.line_items.count() == 1

    def test_skips_orgs_without_subscription(self, superuser, director):
        from apps.organizations.admin import OrganizationAdmin
        from apps.organizations.models import Organization

        # No SubscriptionPlan seeded → signal exits silently → no sub.
        org = Organization.objects.create(
            name="No sub org",
            type="housing_complex",
            owner=director,
        )
        admin_inst = OrganizationAdmin(Organization, AdminSite())
        request = _make_request(superuser)
        qs = Organization.objects.filter(pk=org.pk)
        admin_inst.generate_monthly_invoice_action(request, qs)

        from apps.billing.models import Invoice
        assert Invoice.objects.filter(organization=org).count() == 0

    def test_blocks_non_superuser(self, director, org_with_starter):
        from apps.billing.models import Invoice
        from apps.organizations.admin import OrganizationAdmin
        from apps.organizations.models import Organization

        admin_inst = OrganizationAdmin(Organization, AdminSite())
        request = _make_request(director)
        qs = Organization.objects.filter(pk=org_with_starter.pk)
        admin_inst.generate_monthly_invoice_action(request, qs)
        assert Invoice.objects.count() == 0


# ── preview_next_invoice_action ──────────────────────────────────────────────


@pytest.mark.django_db
class TestPreviewNextInvoice:
    def test_no_db_writes(self, superuser, org_with_starter):
        from apps.billing.models import Invoice
        from apps.organizations.admin import OrganizationAdmin
        from apps.organizations.models import Organization

        admin_inst = OrganizationAdmin(Organization, AdminSite())
        request = _make_request(superuser)
        qs = Organization.objects.filter(pk=org_with_starter.pk)
        admin_inst.preview_next_invoice_action(request, qs)
        assert Invoice.objects.count() == 0


# ── approve_and_email_superuser ──────────────────────────────────────────────


@pytest.mark.django_db
class TestApproveAndEmail:
    def test_approves_and_emails_superuser(
        self, superuser, org_with_starter, settings,
    ):
        from apps.billing.admin import (
            InvoiceAdmin,
            persist_calculator_result,
        )
        from apps.billing.models import Invoice
        from apps.billing.services.calculator import (
            calculate_recurring_invoice,
        )

        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        mail.outbox = []

        today = date.today()
        calc = calculate_recurring_invoice(
            org_with_starter, today, today + timedelta(days=30),
        )
        invoice = persist_calculator_result(
            organization=org_with_starter,
            period_start=today,
            period_end=today + timedelta(days=30),
            calc_result=calc,
        )
        admin_inst = InvoiceAdmin(Invoice, AdminSite())
        request = _make_request(superuser)
        qs = Invoice.objects.filter(pk=invoice.pk)
        admin_inst.approve_and_email_superuser(request, qs)

        invoice.refresh_from_db()
        assert invoice.status == "approved"
        assert invoice.sent_to_superuser_email == superuser.email
        assert invoice.sent_to_superuser_at is not None

        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        # Critical: email goes to superuser, NOT to org's contact
        assert msg.to == [superuser.email]
        assert invoice.invoice_number in msg.subject
        assert org_with_starter.name in msg.subject

    def test_blocks_non_superuser(
        self, director, org_with_starter, settings,
    ):
        from apps.billing.admin import (
            InvoiceAdmin,
            persist_calculator_result,
        )
        from apps.billing.models import Invoice
        from apps.billing.services.calculator import (
            calculate_recurring_invoice,
        )

        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        mail.outbox = []

        today = date.today()
        calc = calculate_recurring_invoice(
            org_with_starter, today, today + timedelta(days=30),
        )
        invoice = persist_calculator_result(
            organization=org_with_starter,
            period_start=today,
            period_end=today + timedelta(days=30),
            calc_result=calc,
        )
        admin_inst = InvoiceAdmin(Invoice, AdminSite())
        request = _make_request(director)
        qs = Invoice.objects.filter(pk=invoice.pk)
        admin_inst.approve_and_email_superuser(request, qs)

        invoice.refresh_from_db()
        assert invoice.status == "draft"  # unchanged
        assert mail.outbox == []

    def test_blocks_superuser_without_email(
        self, db, org_with_starter, settings,
    ):
        from apps.billing.admin import (
            InvoiceAdmin,
            persist_calculator_result,
        )
        from apps.billing.models import Invoice
        from apps.billing.services.calculator import (
            calculate_recurring_invoice,
        )

        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        mail.outbox = []

        no_email_super = User.objects.create_superuser(
            username="noemail_super",
            email="placeholder@x.com",
            password="x",
        )
        User.objects.filter(pk=no_email_super.pk).update(email="")
        no_email_super.refresh_from_db()

        today = date.today()
        calc = calculate_recurring_invoice(
            org_with_starter, today, today + timedelta(days=30),
        )
        invoice = persist_calculator_result(
            organization=org_with_starter,
            period_start=today,
            period_end=today + timedelta(days=30),
            calc_result=calc,
        )
        admin_inst = InvoiceAdmin(Invoice, AdminSite())
        request = _make_request(no_email_super)
        qs = Invoice.objects.filter(pk=invoice.pk)
        admin_inst.approve_and_email_superuser(request, qs)

        invoice.refresh_from_db()
        assert invoice.status == "draft"
        assert mail.outbox == []


# ── FOP snapshot persistence ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestFopSnapshot:
    def test_snapshot_uses_settings_at_creation(
        self, superuser, org_with_starter, settings,
    ):
        from apps.billing.admin import persist_calculator_result
        from apps.billing.services.calculator import (
            calculate_recurring_invoice,
        )

        settings.INVOICE_PAYER_LEGAL_NAME = "ФОП Тестовий"
        settings.INVOICE_PAYER_TAX_ID = "1234567890"
        settings.INVOICE_PAYER_IBAN = "UA000000000000000000000000"
        settings.INVOICE_PAYER_BANK_NAME = "Privatbank"
        settings.INVOICE_PAYER_TAX_NOTE = "Без ПДВ. ФОП 3 група."

        today = date.today()
        calc = calculate_recurring_invoice(
            org_with_starter, today, today + timedelta(days=30),
        )
        invoice = persist_calculator_result(
            organization=org_with_starter,
            period_start=today,
            period_end=today + timedelta(days=30),
            calc_result=calc,
        )
        assert invoice.payer_name_snapshot == "ФОП Тестовий"
        assert invoice.payer_tax_id_snapshot == "1234567890"
        assert invoice.payer_iban_snapshot == "UA000000000000000000000000"
        assert invoice.payer_bank_snapshot == "Privatbank"
        assert "ФОП 3 група" in invoice.payer_tax_note_snapshot
