# Imports
from apps.common.models import ConsentLog, ContentView
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline


# Register the Content View model
@admin.register(ContentView)
class ContentViewAdmin(admin.ModelAdmin):
    """Content View Admin

    This class defines the content view admin interface.

    Extends:
        admin.ModelAdmin

    Attributes:
        list_display (list): The list of display fields.
    """

    # Attributes
    list_display = ["content_type", "user", "viewer_ip", "created_at"]


# Content View Inline
class ContentViewInline(GenericTabularInline):
    """Content View Inline

    This class defines the content view inline interface.

    Extends:
        GenericTabularInline

    Attributes:
        model (ContentView): The content view model.
        extra (int): The number of extra fields.
        readonly_fields (list): The list of read-only fields.
    """

    # Attributes
    model = ContentView
    extra = 0
    readonly_fields = ["user", "viewer_ip", "created_at"]


# Consent Log Admin
@admin.register(ConsentLog)
class ConsentLogAdmin(admin.ModelAdmin):
    """ConsentLog Admin — read-only by design.

    GDPR consent records are immutable: they are created exclusively
    through ``POST /api/v1/consent/`` and must never be edited or
    deleted via the admin (Art. 7(1) accountability requirement).
    """

    list_display = (
        "user",
        "consent_type",
        "version",
        "accepted_at",
        "ip_address",
    )
    list_filter = ("consent_type", "version", "accepted_at", "purpose")
    search_fields = ("user__email", "user__username", "version")
    readonly_fields = (
        "user",
        "consent_type",
        "version",
        "accepted_at",
        "purpose",
        "given",
        "ip_address",
        "user_agent",
        "timestamp",
    )
    ordering = ("-accepted_at",)

    def has_add_permission(self, request):
        # Consent log is append-only via API only.
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
