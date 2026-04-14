# Imports
from django.contrib import admin
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
