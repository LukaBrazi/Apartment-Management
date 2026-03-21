from django.contrib import admin
from .models import TelegramProfile, TelegramVerificationToken


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "chat_id", "is_active", "notify_issues", "notify_passes", "notify_announcements", "created_at"]
    list_filter = ["is_active", "notify_issues", "notify_passes", "notify_announcements"]
    search_fields = ["user__email", "chat_id"]
    readonly_fields = ["created_at", "updated_at"]
    actions = ["deactivate_selected"]

    @admin.action(description="Deactivate selected profiles")
    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(TelegramVerificationToken)
class TelegramVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "token", "is_used", "expires_at", "created_at"]
    list_filter = ["is_used"]
    search_fields = ["user__email"]
    readonly_fields = ["token", "created_at"]
