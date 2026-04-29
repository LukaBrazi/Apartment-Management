# Imports
from django.contrib import admin, messages
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
    actions = ["generate_org_report_email"]

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
