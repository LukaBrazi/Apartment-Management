from django.contrib import admin

from apps.news.models import News, NewsCategory


@admin.register(NewsCategory)
class NewsCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "color"]


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "author", "is_published", "pinned", "views_count", "published_at"]
    list_filter = ["is_published", "pinned", "category"]
    search_fields = ["title", "excerpt"]
    raw_id_fields = ["author"]
