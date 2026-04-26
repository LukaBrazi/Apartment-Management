from django.contrib import admin

from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ["get_user_email", "get_message_preview", "created_at", "is_reviewed"]
    list_filter = ["is_reviewed", "created_at"]
    search_fields = ["user__email", "message"]
    readonly_fields = ["user", "message", "created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_user_email(self, obj):
        return obj.user.email

    get_user_email.short_description = "Email"
    get_user_email.admin_order_field = "user__email"

    def get_message_preview(self, obj):
        return obj.message[:80] + "…" if len(obj.message) > 80 else obj.message

    get_message_preview.short_description = "Повідомлення"
