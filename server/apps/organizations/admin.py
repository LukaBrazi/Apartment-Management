# Imports
from datetime import timedelta

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _

from apps.organizations.models import Organization, OrganizationMembership


# ── Organization Admin ─────────────────────────────────────────────────────────

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """OrganizationAdmin

    Адміністраторський інтерфейс для Organization.

    Extends:
        admin.ModelAdmin

    Attributes:
        list_display (list): Поля для відображення в списку.
        list_filter (list): Поля для фільтрування.
        search_fields (list): Поля для пошуку.
        readonly_fields (list): Поля тільки для читання.
        fieldsets (tuple): Розділи форми.
    """

    list_display = [
        "name",
        "slug",
        "type",
        "owner",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "type",
        "is_active",
        "created_at",
    ]
    search_fields = [
        "name",
        "slug",
        "email",
    ]
    readonly_fields = [
        "id",
        "slug",
        "pkid",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        (
            _("Basic Information"),
            {
                "fields": (
                    "id",
                    "pkid",
                    "name",
                    "slug",
                    "type",
                    "owner",
                )
            },
        ),
        (
            _("Contact Information"),
            {
                "fields": (
                    "email",
                    "phone",
                    "address",
                    "city",
                )
            },
        ),
        (
            _("Additional Information"),
            {
                "fields": (
                    "description",
                    "features",
                    "is_active",
                )
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    ordering = ["-created_at"]
    actions = [
        "generate_org_report_email",
        "generate_monthly_invoice_action",
        "preview_next_invoice_action",
        "create_onboarding_invoice_action",
    ]

    # ── Admin actions (PR-11) ─────────────────────────────────────────────

    @admin.action(description="📧 Згенерувати звіт і надіслати на пошту")
    def generate_org_report_email(self, request, queryset):
        """Dispatch one ``send_organization_report_task`` per selected org.

        Permission gates:
            * ``request.user`` must be a superuser — non-superusers see an
              error message and the queryset is left untouched.
            * ``request.user.email`` must be set — we send the report to
              the requesting admin, so an empty email means "ask the user
              to fix their profile first".

        Each org gets its own task / email — there is no batching. This
        keeps failure isolation per-org and keeps Celery retry semantics
        meaningful (one bad org doesn't poison the rest).
        """
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Тільки superuser може генерувати звіти організацій.",
                level=messages.ERROR,
            )
            return

        if not request.user.email:
            self.message_user(
                request,
                "У вашого профілю не задана email-адреса. "
                "Додайте її через User Admin перш ніж генерувати звіти.",
                level=messages.ERROR,
            )
            return

        # Local import — keep admin module light at import time and
        # avoid a circular dep between admin ↔ tasks ↔ apps registry.
        from apps.organizations.tasks import send_organization_report_task

        n = queryset.count()
        for org in queryset:
            send_organization_report_task.delay(org.id, request.user.email)

        self.message_user(
            request,
            f"Запит на {n} звіт(и) поставлений у чергу. "
            f"Звіт прийде на {request.user.email} за 1-2 хвилини.",
            level=messages.SUCCESS,
        )

    # ── Admin actions (PR-13a — billing) ─────────────────────────────────

    @admin.action(description="💰 Згенерувати monthly invoice (draft)")
    def generate_monthly_invoice_action(self, request, queryset):
        """Per-org calculator → save draft Invoice + InvoiceLineItems.

        Skips orgs without a subscription. Emits a SUCCESS message with
        the count.
        """
        from apps.billing.admin import persist_calculator_result
        from apps.billing.services.calculator import (
            calculate_recurring_invoice,
        )

        if not request.user.is_superuser:
            self.message_user(
                request,
                "Тільки superuser може генерувати invoices.",
                level=messages.ERROR,
            )
            return

        today = timezone.now().date()
        period_start = today.replace(day=1)
        # Naive period_end — last day of current month-ish (today + 30 is
        # close enough for the draft; CEO edits dates manually if needed).
        period_end = period_start + timedelta(days=30)

        created = 0
        skipped = 0
        for org in queryset:
            sub = getattr(org, "subscription", None)
            if sub is None:
                skipped += 1
                continue
            calc = calculate_recurring_invoice(org, period_start, period_end)
            persist_calculator_result(
                organization=org,
                period_start=period_start,
                period_end=period_end,
                calc_result=calc,
            )
            created += 1

        self.message_user(
            request,
            f"Створено {created} draft invoice(s). Пропущено: {skipped} "
            f"(без підписки).",
            level=messages.SUCCESS,
        )

    @admin.action(description="🔍 Preview next invoice (без збереження)")
    def preview_next_invoice_action(self, request, queryset):
        """Dry-run the recurring calculator and surface the totals via
        admin messages. No DB writes.
        """
        from apps.billing.services.calculator import (
            calculate_recurring_invoice,
        )

        if not request.user.is_superuser:
            self.message_user(
                request,
                "Тільки superuser може робити preview.",
                level=messages.ERROR,
            )
            return

        today = timezone.now().date()
        period_start = today.replace(day=1)
        period_end = period_start + timedelta(days=30)

        for org in queryset:
            sub = getattr(org, "subscription", None)
            if sub is None:
                self.message_user(
                    request,
                    f"{org.name}: підписки немає — preview неможливий.",
                    level=messages.WARNING,
                )
                continue
            calc = calculate_recurring_invoice(org, period_start, period_end)
            self.message_user(
                request,
                f"{org.name}: subtotal={calc['subtotal']} UAH, "
                f"discount={calc['discount']} UAH, "
                f"total={calc['total']} UAH "
                f"({len(calc['line_items'])} line items).",
                level=messages.INFO,
            )

    @admin.action(description="🆕 Створити onboarding invoice…")
    def create_onboarding_invoice_action(self, request, queryset):
        """Redirect to the intermediate page where the operator picks
        which one-time add-ons to bill. Single-org action — if the user
        selected several, we use the first one and warn.
        """
        if queryset.count() == 0:
            self.message_user(
                request,
                "Виберіть organization для onboarding invoice.",
                level=messages.ERROR,
            )
            return
        org = queryset.first()
        if queryset.count() > 1:
            self.message_user(
                request,
                f"Onboarding invoice створюється тільки для однієї org. "
                f"Використано: {org.name}.",
                level=messages.WARNING,
            )
        url = reverse(
            "admin:organizations_organization_onboarding_invoice",
            args=[org.pk],
        )
        return HttpResponseRedirect(url)

    # ── Custom URLs (PR-13a — onboarding intermediate page) ──────────────

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<path:object_id>/onboarding-invoice/",
                self.admin_site.admin_view(self.onboarding_invoice_view),
                name="organizations_organization_onboarding_invoice",
            ),
        ]
        return custom + urls

    def onboarding_invoice_view(self, request, object_id):
        """Intermediate page with checkboxes for each one-time AddOn.

        POST → create draft Invoice + LineItems and redirect back to
        the org change page.
        """
        from apps.billing.admin import persist_calculator_result
        from apps.billing.models import AddOn
        from apps.billing.services.calculator import (
            calculate_onboarding_invoice,
        )

        if not request.user.is_superuser:
            self.message_user(
                request,
                "Тільки superuser може створювати onboarding invoices.",
                level=messages.ERROR,
            )
            return HttpResponseRedirect(
                reverse("admin:organizations_organization_changelist"),
            )

        org = self.get_object(request, object_id)
        if org is None:
            self.message_user(
                request,
                "Organization не знайдено.",
                level=messages.ERROR,
            )
            return HttpResponseRedirect(
                reverse("admin:organizations_organization_changelist"),
            )

        addons = AddOn.objects.filter(
            billing_type=AddOn.BILLING_ONE_TIME,
            is_active=True,
        ).order_by("price_uah")

        if request.method == "POST":
            selected_codes = request.POST.getlist("addons")
            calc = calculate_onboarding_invoice(org, addon_codes=selected_codes)
            today = timezone.now().date()
            invoice = persist_calculator_result(
                organization=org,
                period_start=today,
                period_end=today,
                calc_result=calc,
            )
            self.message_user(
                request,
                f"Onboarding invoice створено: {invoice.invoice_number} — "
                f"{invoice.total_uah} UAH.",
                level=messages.SUCCESS,
            )
            return HttpResponseRedirect(
                reverse(
                    "admin:billing_invoice_change",
                    args=[invoice.pk],
                ),
            )

        # Minimal inline HTML — keeps the change list as the operator's
        # main entry point without a heavy template tree.
        rows = "".join(
            f'<tr><td><input type="checkbox" name="addons" value="{escape(a.code)}"></td>'
            f'<td>{escape(a.name_uk)}</td>'
            f'<td>{a.price_uah} UAH</td></tr>'
            for a in addons
        )
        html = f"""
        <h1>Onboarding Invoice — {escape(org.name)}</h1>
        <p>Виберіть one-time add-ons. Натисніть "Створити" — буде створено
        draft invoice зі статусом <code>draft</code>, після чого ви
        зможете approve & email.</p>
        <form method="post">
          <input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get('CSRF_COOKIE','')}">
          <table>
            <thead><tr><th></th><th>Add-on</th><th>Price</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
          <p><button type="submit">Створити draft invoice</button></p>
        </form>
        """
        return render(
            request,
            "admin/billing_onboarding_invoice.html",
            {"body_html": html, "title": "Onboarding invoice"},
        )


# ── Organization Membership Admin ──────────────────────────────────────────────

@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    """OrganizationMembershipAdmin

    Адміністраторський інтерфейс для OrganizationMembership.

    Extends:
        admin.ModelAdmin

    Attributes:
        list_display (list): Поля для відображення в списку.
        list_filter (list): Поля для фільтрування.
        search_fields (list): Поля для пошуку.
        readonly_fields (list): Поля тільки для читання.
        fieldsets (tuple): Розділи форми.
    """

    list_display = [
        "user",
        "organization",
        "role",
        "is_active",
        "joined_at",
    ]
    list_filter = [
        "role",
        "is_active",
        "joined_at",
        "organization",
    ]
    search_fields = [
        "user__email",
        "user__username",
        "organization__name",
    ]
    readonly_fields = [
        "id",
        "pkid",
        "created_at",
        "updated_at",
        "joined_at",
    ]
    fieldsets = (
        (
            _("Membership Information"),
            {
                "fields": (
                    "id",
                    "pkid",
                    "user",
                    "organization",
                    "role",
                )
            },
        ),
        (
            _("Additional Information"),
            {
                "fields": (
                    "staff_type",
                    "is_active",
                    "invited_by",
                )
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": (
                    "joined_at",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    ordering = ["-created_at"]
