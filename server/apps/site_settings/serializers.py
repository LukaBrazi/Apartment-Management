from rest_framework import serializers

from .models import ContactPerson, SiteLink, SiteSettings


class SiteLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteLink
        fields = ["id", "label", "url", "order", "open_in_new_tab"]


class ContactPersonSerializer(serializers.ModelSerializer):
    """Serializer for contact persons displayed on the contacts page."""

    role_display = serializers.CharField(source="get_role_display", read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ContactPerson
        fields = [
            "id",
            "name",
            "role",
            "role_display",
            "position",
            "phone",
            "email",
            "telegram",
            "photo_url",
            "is_emergency",
            "working_hours",
            "order",
        ]

    def get_photo_url(self, obj):
        request = self.context.get("request")
        if obj.photo:
            url = obj.photo.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class AdminContactPersonSerializer(serializers.ModelSerializer):
    """Admin-facing CRUD serializer for ``ContactPerson``.

    PR-15: ``organization`` is intentionally NOT in ``fields`` so staff
    cannot spoof the FK and park a contact in another tenant's org.
    The view's ``perform_create`` pins the org server-side via
    ``_resolve_caller_organization`` (same pattern as PR-14 Buildings).

    The lock-down regex test in
    ``apps/site_settings/tests/test_admin_contacts_api.py`` enforces
    this invariant — do not add ``organization`` here.
    """

    role_display = serializers.CharField(source="get_role_display", read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ContactPerson
        fields = [
            "id",
            "name",
            "role",
            "role_display",
            "position",
            "phone",
            "email",
            "telegram",
            "photo_url",
            "is_emergency",
            "working_hours",
            "order",
            "is_active",
        ]
        read_only_fields = ["id", "role_display", "photo_url"]

    def get_photo_url(self, obj):
        request = self.context.get("request")
        if obj.photo:
            url = obj.photo.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class SiteSettingsSerializer(serializers.ModelSerializer):
    """Public site settings serializer for homepage and initial page load."""

    links = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
    # PR-8 removed the ``current_complex`` FK — these are now straight
    # aliases for the text fields on the model (kept as method fields so
    # the wire shape stays stable for clients that already read the
    # ``display_*`` keys).
    display_complex_name = serializers.ReadOnlyField(source="complex_name")
    display_complex_address = serializers.ReadOnlyField(source="complex_address")

    class Meta:
        model = SiteSettings
        fields = [
            # Hero section
            "hero_title",
            "hero_subtitle",
            "hero_image_url",
            "cta_text",
            "cta_url",
            # Platform branding
            "platform_name",
            "platform_tagline",
            "logo_url",
            "favicon_url",
            "primary_color",
            "secondary_color",
            # Complex info
            "display_complex_name",
            "display_complex_address",
            "complex_description",
            # Support
            "support_email",
            "support_phone",
            "support_hours",
            "telegram_url",
            "viber_url",
            # Footer & Legal
            "footer_text",
            "terms_url",
            "privacy_url",
            # SEO
            "meta_title",
            "meta_description",
            # Navigation
            "links",
        ]

    def get_links(self, obj):
        qs = obj.site_links.filter(is_active=True).order_by("order", "label")
        return SiteLinkSerializer(qs, many=True).data

    def get_hero_image_url(self, obj):
        request = self.context.get("request")
        if obj.hero_image:
            url = obj.hero_image.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None
