from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import ContactPerson, SiteLink, SiteSettings


class SiteLinkInline(admin.TabularInline):
    model = SiteLink
    extra = 1
    fields = ["label", "url", "order", "is_active", "open_in_new_tab"]


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Singleton admin — hides the object list, opens the single record directly."""

    inlines = [SiteLinkInline]
    fieldsets = [
        (
            _("Residential Complex (ЖК)"),
            {
                "fields": ["current_complex"],
                "description": _("The active ЖК for this installation. "
                "Buildings are scoped to this complex."),
            },
        ),
        (
            _("Hero Section"),
            {
                "fields": [
                    "hero_image",
                    "hero_title",
                    "hero_subtitle",
                    "cta_text",
                    "cta_url",
                ]
            },
        ),
        (
            _("Platform Identity (White-Label)"),
            {
                "fields": [
                    "platform_name",
                    "platform_tagline",
                    "logo_url",
                    "favicon_url",
                ],
                "description": _("Customize the platform branding for white-label deployments."),
            },
        ),
        (
            _("Branding Colors"),
            {
                "fields": ["primary_color", "secondary_color"],
                "description": _("Hex color codes for primary and secondary branding."),
            },
        ),
        (
            _("Complex Information"),
            {
                "fields": ["complex_name", "complex_address", "complex_description"],
                "description": _("Override current_complex info or provide additional context."),
            },
        ),
        (
            _("Support Contact Information"),
            {
                "fields": [
                    "support_email",
                    "support_phone",
                    "support_hours",
                    "telegram_url",
                    "viber_url",
                ],
            },
        ),
        (
            _("Footer & Legal"),
            {
                "fields": ["footer_text", "terms_url", "privacy_url"],
            },
        ),
        (
            _("SEO"),
            {
                "fields": ["meta_title", "meta_description"],
                "classes": ["collapse"],
            },
        ),
    ]

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom = [
            path(
                "",
                self.admin_site.admin_view(self.redirect_to_object),
                name="site_settings_sitesettings_changelist",
            ),
        ]
        return custom + urls

    def redirect_to_object(self, request):
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        obj = SiteSettings.get()
        return HttpResponseRedirect(
            reverse("admin:site_settings_sitesettings_change", args=[obj.pk])
        )


@admin.register(ContactPerson)
class ContactPersonAdmin(admin.ModelAdmin):
    """Admin for contact persons displayed on the contacts page."""

    list_display = ["name", "role", "position", "phone", "is_active", "order"]
    list_filter = ["role", "is_active", "is_emergency"]
    search_fields = ["name", "position", "email", "phone"]
    ordering = ["order", "name"]

    fieldsets = [
        (
            _("Contact Information"),
            {
                "fields": ["name", "position", "phone", "email", "telegram", "photo"],
            },
        ),
        (
            _("Role & Classification"),
            {
                "fields": ["role", "is_emergency"],
                "description": _("Assign a role and mark as emergency contact if applicable."),
            },
        ),
        (
            _("Availability"),
            {
                "fields": ["working_hours", "is_active"],
            },
        ),
        (
            _("Display Settings"),
            {
                "fields": ["order"],
                "description": _("Control display order on the contacts page."),
            },
        ),
    ]

    readonly_fields = []
