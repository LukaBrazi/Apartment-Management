from rest_framework import serializers

from .models import SiteLink, SiteSettings


class SiteLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteLink
        fields = ["id", "label", "url", "order", "open_in_new_tab"]


class SiteSettingsSerializer(serializers.ModelSerializer):
    links = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
    complex_name = serializers.ReadOnlyField(source="current_complex.name")
    complex_address = serializers.ReadOnlyField(source="current_complex.address")

    class Meta:
        model = SiteSettings
        fields = [
            "complex_name",
            "complex_address",
            "hero_title",
            "hero_subtitle",
            "hero_image_url",
            "cta_text",
            "cta_url",
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
