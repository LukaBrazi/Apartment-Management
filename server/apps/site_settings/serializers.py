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


class SiteSettingsSerializer(serializers.ModelSerializer):
    """Public site settings serializer for homepage and initial page load."""

    links = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
    # Fallback to model fields if complex_name/address not set
    display_complex_name = serializers.SerializerMethodField()
    display_complex_address = serializers.SerializerMethodField()

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

    def get_display_complex_name(self, obj):
        """Return complex_name if set, otherwise fallback to current_complex.name."""
        if obj.complex_name:
            return obj.complex_name
        return obj.current_complex.name if obj.current_complex else ""

    def get_display_complex_address(self, obj):
        """Return complex_address if set, otherwise fallback to current_complex.address."""
        if obj.complex_address:
            return obj.complex_address
        return obj.current_complex.address if obj.current_complex else ""
