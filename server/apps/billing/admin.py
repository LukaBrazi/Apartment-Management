"""Billing Django Admin (PR-13a, Phase 3).

Three model admins + a handful of actions:

* ``SubscriptionPlanAdmin`` / ``AddOnAdmin`` — catalog editing.
* ``OrganizationSubscriptionAdmin`` / ``OrganizationAddOnAdmin`` — per-org
  state.
* ``InvoiceAdmin`` — read-only-ish view of generated invoices with the
  ``approve_and_email_superuser`` action.

The bigger Org-level actions (``generate_monthly_invoice``,
``preview_next_invoice``, ``onboarding_invoice``) live on the existing
``OrganizationAdmin`` in ``apps.organizations.admin`` — wired up there
to keep the Org admin page as the operator's single landing point.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import admin, messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from apps.billing.models import (
    AddOn,
    Invoice,
    InvoiceLineItem,
    OrganizationAddOn,
    OrganizationSubscription,
    SubscriptionPlan,
)


# ── Catalog admins ───────────────────────────────────────────────────────────


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "monthly_price_uah", "max_apartments", "max_users", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("monthly_price_uah",)


@admin.register(AddOn)
class AddOnAdmin(admin.ModelAdmin):
    list_display = ("code", "name_uk", "price_uah", "billing_type", "is_active")
    list_filter = ("billing_type", "is_active")
    search_fields = ("code", "name_uk")
    ordering = ("billing_type", "price_uah")


# ── Per-org state ────────────────────────────────────────────────────────────


@admin.register(OrganizationSubscription)
class OrganizationSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "plan",
        "billing_period",
        "started_at",
        "next_billing_at",
        "trial_ends_at",
        "is_active",
        "is_paused",
    )
    list_filter = ("billing_period", "is_active", "is_paused", "plan")
    search_fields = ("organization__name", "organization__slug")
    raw_id_fields = ("organization",)


@admin.register(OrganizationAddOn)
class OrganizationAddOnAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "addon",
        "custom_name",
        "custom_price_monthly_uah",
        "activated_at",
        "is_active",
    )
    list_filter = ("is_active", "addon")
    search_fields = ("organization__name", "custom_name", "addon__code")
    raw_id_fields = ("organization", "addon")


# ── Invoice admin (read-mostly) ──────────────────────────────────────────────


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    readonly_fields = (
        "description",
        "quantity",
        "unit_price_uah",
        "total_uah",
        "line_type",
    )
    can_delete = False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "organization",
        "period_start",
        "period_end",
        "total_uah",
        "status",
        "issued_at",
    )
    list_filter = ("status", "issued_at", "period_start")
    search_fields = ("invoice_number", "organization__name")
    raw_id_fields = ("organization",)
    readonly_fields = (
        "invoice_number",
        "organization",
        "issued_at",
        "due_at",
        "period_start",
        "period_end",
        "subtotal_uah",
        "discount_uah",
        "total_uah",
        "payer_name_snapshot",
        "payer_tax_id_snapshot",
        "payer_iban_snapshot",
        "payer_bank_snapshot",
        "payer_tax_note_snapshot",
        "sent_to_superuser_at",
        "sent_to_superuser_email",
    )
    inlines = [InvoiceLineItemInline]
    actions = ["approve_and_email_superuser"]

    @admin.action(description="✅ Approve & email superuser")
    def approve_and_email_superuser(self, request, queryset):
        """Move selected draft invoices to ``approved`` and email the
        rendered HTML body to ``request.user.email``.

        Permission gates:
            * superuser only.
            * ``request.user.email`` must be set.

        Strictly emails the requesting superuser — never the org's
        contact email. Internal review flow only.
        """
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Тільки superuser може approve invoices.",
                level=messages.ERROR,
            )
            return
        if not request.user.email:
            self.message_user(
                request,
                "У вашого профілю не задана email-адреса. Додайте її через User Admin.",
                level=messages.ERROR,
            )
            return

        sent = 0
        for invoice in queryset:
            html_body = render_to_string(
                "billing/email/invoice_summary.html",
                {"invoice": invoice},
            )
            subject = (
                f"Invoice {invoice.invoice_number} — {invoice.organization.name}"
            )
            text_fallback = (
                "Ваш email-клієнт не підтримує HTML. "
                f"Invoice: {invoice.invoice_number}, "
                f"Total: {invoice.total_uah} UAH."
            )
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_fallback,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach_alternative(html_body, "text/html")
            email.send()

            invoice.status = Invoice.STATUS_APPROVED
            invoice.sent_to_superuser_at = timezone.now()
            invoice.sent_to_superuser_email = request.user.email
            invoice.save(update_fields=[
                "status", "sent_to_superuser_at", "sent_to_superuser_email",
            ])
            sent += 1

        self.message_user(
            request,
            f"Approved & emailed {sent} invoice(s) to {request.user.email}.",
            level=messages.SUCCESS,
        )


# ── Helpers reused by Org-level actions ──────────────────────────────────────


def fop_snapshot_kwargs() -> dict:
    """Build the ``payer_*_snapshot`` kwargs from current settings.

    Reading via ``getattr(settings, ..., "")`` so the call works on
    test / dev settings tiers that don't define the env vars at all
    (returns empty strings — invoice still saves fine).
    """
    return {
        "payer_name_snapshot": getattr(settings, "INVOICE_PAYER_LEGAL_NAME", "") or "",
        "payer_tax_id_snapshot": getattr(settings, "INVOICE_PAYER_TAX_ID", "") or "",
        "payer_iban_snapshot": getattr(settings, "INVOICE_PAYER_IBAN", "") or "",
        "payer_bank_snapshot": getattr(settings, "INVOICE_PAYER_BANK_NAME", "") or "",
        "payer_tax_note_snapshot": getattr(settings, "INVOICE_PAYER_TAX_NOTE", "") or "",
    }


def persist_calculator_result(
    *,
    organization,
    period_start: date,
    period_end: date,
    calc_result: dict,
) -> Invoice:
    """Persist a calculator-result dict to a draft Invoice + LineItems."""
    due_days = int(getattr(settings, "INVOICE_DUE_DAYS", 10) or 10)
    today = timezone.now().date()
    invoice = Invoice.objects.create(
        organization=organization,
        issued_at=today,
        due_at=today + timedelta(days=due_days),
        period_start=period_start,
        period_end=period_end,
        subtotal_uah=calc_result["subtotal"],
        discount_uah=calc_result["discount"],
        total_uah=calc_result["total"],
        status=Invoice.STATUS_DRAFT,
        **fop_snapshot_kwargs(),
    )
    for li in calc_result["line_items"]:
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description=li["description"],
            quantity=li["quantity"],
            unit_price_uah=Decimal(li["unit_price"]),
            total_uah=Decimal(li["total"]),
            line_type=li["line_type"],
        )
    return invoice
