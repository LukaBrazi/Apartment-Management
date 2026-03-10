from django.contrib import admin

from .models import SiteLink, SiteSettings


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
            "Hero section",
            {
                "fields": [
                    "hero_image",
                    "hero_title",
                    "hero_subtitle",
                ]
            },
        ),
        (
            "Call-to-action button",
            {
                "fields": ["cta_text", "cta_url"],
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
