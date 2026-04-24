from rest_framework import serializers
from taggit.serializers import TaggitSerializer, TagListSerializerField

from apps.news.models import News, NewsCategory


class NewsCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsCategory
        fields = ["id", "name", "slug", "color"]


class NewsListSerializer(TaggitSerializer, serializers.ModelSerializer):
    category = NewsCategorySerializer(read_only=True)
    tags = TagListSerializerField()
    author_name = serializers.ReadOnlyField(source="author.full_name")

    class Meta:
        model = News
        fields = [
            "id", "title", "slug", "excerpt", "cover_image",
            "category", "tags", "author_name",
            "published_at", "is_published", "pinned",
            "views_count", "external_url", "created_at",
        ]


class NewsDetailSerializer(NewsListSerializer):
    class Meta(NewsListSerializer.Meta):
        fields = NewsListSerializer.Meta.fields + ["body"]


class NewsCategoryPKField(serializers.PrimaryKeyRelatedField):
    """Accept UUID `id` instead of the BigAutoField `pkid`."""

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        return str(value.id)

    def to_internal_value(self, data):
        try:
            return NewsCategory.objects.get(id=data)
        except (NewsCategory.DoesNotExist, ValueError, TypeError):
            self.fail("does_not_exist", pk_value=data)


class OrganizationPKField(serializers.PrimaryKeyRelatedField):
    """
    Поле для вибору організації за UUID.
    queryset визначається динамічно щоб уникнути circular import на рівні модуля.
    """

    def get_queryset(self):
        from apps.organizations.models import Organization
        return Organization.objects.filter(is_active=True)

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        if value is None:
            return None
        return str(value.id)

    def to_internal_value(self, data):
        if data is None:
            return None
        try:
            from apps.organizations.models import Organization
            return Organization.objects.get(id=data)
        except (Organization.DoesNotExist, ValueError, TypeError):
            self.fail("does_not_exist", pk_value=data)


class NewsAdminSerializer(TaggitSerializer, serializers.ModelSerializer):
    category = NewsCategoryPKField(
        queryset=NewsCategory.objects.all(), allow_null=True, required=False
    )
    organization = OrganizationPKField(allow_null=True, required=False)
    tags = TagListSerializerField(required=False)
    author_name = serializers.ReadOnlyField(source="author.full_name")

    class Meta:
        model = News
        fields = [
            "id", "title", "slug", "excerpt", "body", "cover_image",
            "category", "tags", "author_name", "organization",
            "published_at", "is_published", "pinned", "notify_subscribers",
            "views_count", "external_url", "created_at",
        ]
        read_only_fields = ["id", "slug", "views_count", "created_at", "author_name"]
