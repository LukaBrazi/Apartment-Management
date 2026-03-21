# News Feature Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add portal-wide News model + API + `/news` frontend page; rename nav "Оголошення"→"Новини"; add `<ComingSoon>` component for microservices-ready placeholders; update README and TODO.

**Architecture:** New `apps/news/` Django app (NewsCategory + News models) with public read API and admin write API. Frontend: Redux slice + `/news` list/detail pages + `/admin/news` CRUD. `Announcement` (building-scoped) remains unchanged. All "В розробці" pages replaced by `<ComingSoon microserviceKey="..." />`.

**Tech Stack:** Django 4.2, DRF, taggit, autoslug, Next.js 14, RTK Query, TailwindCSS, Playwright (E2E), pytest + factory_boy.

---

## Chunk 1: Backend — `apps/news/` app

### Task 1: Scaffold `apps/news/` app

**Files:**
- Create: `server/apps/news/__init__.py`
- Create: `server/apps/news/apps.py`
- Modify: `server/config/settings/base.py` (INSTALLED_APPS)
- Modify: `server/config/urls.py`

- [ ] **Step 1: Create app directory and files**

```bash
cd server
mkdir -p apps/news/migrations
touch apps/news/__init__.py apps/news/migrations/__init__.py
```

- [ ] **Step 2: Write `apps/news/apps.py`**

```python
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.news"
    verbose_name = _("News")
```

- [ ] **Step 3: Add to INSTALLED_APPS in `server/config/settings/base.py`**

Find the local apps block and add after `"apps.passes"`:
```python
"apps.news",
```

- [ ] **Step 4: Add URL include in `server/config/urls.py`**

After `path("api/v1/passes/", include("apps.passes.urls")),` add:
```python
path("api/v1/news/", include("apps.news.urls")),
```

---

### Task 2: Write failing tests for News models

**Files:**
- Create: `server/apps/tests/test_news.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for News app — model + API."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.tests.factories import AdminUserFactory, NewsCategoryFactory, NewsFactory, UserFactory


# ── Model tests ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_news_category_creation():
    cat = NewsCategoryFactory(name="Технічне")
    assert cat.slug == "tekhnichne"
    assert cat.color.startswith("#")


@pytest.mark.django_db
def test_news_creation():
    news = NewsFactory(title="Оновлення порталу", is_published=True)
    assert news.slug
    assert news.is_published is True
    assert news.views_count == 0
    assert news.pinned is False


@pytest.mark.django_db
def test_news_str():
    news = NewsFactory(title="Тестова новина")
    assert str(news) == "Тестова новина"


# ── Public API — list ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_only_published_news_visible_to_user():
    user = UserFactory()
    NewsFactory(is_published=True, title="Published")
    NewsFactory(is_published=False, title="Draft")

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get(reverse("news-list"))

    assert resp.status_code == 200
    titles = [n["title"] for n in resp.data["news"]]
    assert "Published" in titles
    assert "Draft" not in titles


@pytest.mark.django_db
def test_pinned_news_appears_first():
    user = UserFactory()
    NewsFactory(is_published=True, pinned=False, title="Normal")
    NewsFactory(is_published=True, pinned=True, title="Pinned")

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get(reverse("news-list"))

    assert resp.data["news"][0]["title"] == "Pinned"


@pytest.mark.django_db
def test_unauthenticated_cannot_access_news():
    client = APIClient()
    resp = client.get(reverse("news-list"))
    assert resp.status_code == 401


# ── Public API — detail ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_news_detail_returns_200():
    user = UserFactory()
    news = NewsFactory(is_published=True)

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get(reverse("news-detail", kwargs={"slug": news.slug}))

    assert resp.status_code == 200
    assert resp.data["news_item"]["title"] == news.title


@pytest.mark.django_db
def test_news_detail_increments_views_count():
    user = UserFactory()
    news = NewsFactory(is_published=True)

    client = APIClient()
    client.force_authenticate(user=user)
    client.get(reverse("news-detail", kwargs={"slug": news.slug}))
    client.get(reverse("news-detail", kwargs={"slug": news.slug}))

    news.refresh_from_db()
    assert news.views_count == 2


@pytest.mark.django_db
def test_unpublished_news_returns_404_for_regular_user():
    user = UserFactory()
    news = NewsFactory(is_published=False)

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get(reverse("news-detail", kwargs={"slug": news.slug}))

    assert resp.status_code == 404


# ── Admin API ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_sees_all_news_including_drafts():
    admin = AdminUserFactory()
    NewsFactory(is_published=True, title="Published")
    NewsFactory(is_published=False, title="Draft")

    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.get(reverse("news-admin-list"))

    assert resp.status_code == 200
    titles = [n["title"] for n in resp.data["news"]]
    assert "Published" in titles
    assert "Draft" in titles


@pytest.mark.django_db
def test_admin_can_create_news():
    admin = AdminUserFactory()
    cat = NewsCategoryFactory()

    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.post(reverse("news-admin-list"), {
        "title": "Нова новина",
        "excerpt": "Короткий опис",
        "body": "Повний текст",
        "is_published": True,
        "pinned": False,
        "category": str(cat.id),
    }, format="json")

    assert resp.status_code == 201
    assert resp.data["news_item"]["title"] == "Нова новина"


@pytest.mark.django_db
def test_admin_can_update_news():
    admin = AdminUserFactory()
    news = NewsFactory(title="Стара назва")

    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.patch(
        reverse("news-admin-detail", kwargs={"slug": news.slug}),
        {"title": "Нова назва"},
        format="json",
    )

    assert resp.status_code == 200
    news.refresh_from_db()
    assert news.title == "Нова назва"


@pytest.mark.django_db
def test_admin_can_delete_news():
    admin = AdminUserFactory()
    news = NewsFactory()

    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.delete(reverse("news-admin-detail", kwargs={"slug": news.slug}))

    assert resp.status_code == 204


@pytest.mark.django_db
def test_non_admin_cannot_create_news():
    user = UserFactory()

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(reverse("news-admin-list"), {
        "title": "Hack", "excerpt": "x", "body": "x", "is_published": True,
    }, format="json")

    assert resp.status_code == 403


@pytest.mark.django_db
def test_external_url_is_optional():
    news = NewsFactory(external_url="")
    assert news.external_url == ""

    news2 = NewsFactory(external_url="https://example.com")
    assert news2.external_url == "https://example.com"
```

- [ ] **Step 2: Run tests — expect FAIL (factories + URLs missing)**

```bash
cd server
source ../.venv/bin/activate
python -m pytest apps/tests/test_news.py -v 2>&1 | head -30
```

Expected: `ImportError: cannot import name 'NewsCategoryFactory'`

---

### Task 3: Add factories for News

**Files:**
- Modify: `server/apps/tests/factories.py`

- [ ] **Step 1: Add NewsCategory and News factories at end of file**

```python
# ── News ──────────────────────────────────────────────────────────────────────

class NewsCategoryFactory(DjangoModelFactory):
    class Meta:
        model = "news.NewsCategory"

    name = factory.Sequence(lambda n: f"Category {n}")
    color = "#2F6FED"


class NewsFactory(DjangoModelFactory):
    class Meta:
        model = "news.News"

    title = factory.Sequence(lambda n: f"News Article {n}")
    excerpt = factory.Faker("sentence", nb_words=10)
    body = factory.Faker("paragraph", nb_sentences=5)
    author = factory.SubFactory(AdminUserFactory)
    is_published = False
    pinned = False
    views_count = 0
    external_url = ""
```

- [ ] **Step 2: Run tests — still fail (model missing)**

```bash
python -m pytest apps/tests/test_news.py::test_news_category_creation -v
```

Expected: `django.db.utils.OperationalError` or `ModuleNotFoundError`

---

### Task 4: Write News models

**Files:**
- Create: `server/apps/news/models.py`

- [ ] **Step 1: Write models**

```python
from autoslug import AutoSlugField
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from taggit.managers import TaggableManager

from apps.common.models import TimeStampedModel

User = get_user_model()


class NewsCategory(TimeStampedModel):
    name = models.CharField(_("Name"), max_length=100)
    slug = AutoSlugField(populate_from="name", unique=True, always_update=False)
    color = models.CharField(_("Color"), max_length=7, default="#2F6FED")

    class Meta:
        verbose_name = _("News Category")
        verbose_name_plural = _("News Categories")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class News(TimeStampedModel):
    title = models.CharField(_("Title"), max_length=255)
    slug = AutoSlugField(
        populate_from="title", unique=True, always_update=True, verbose_name=_("Slug")
    )
    excerpt = models.TextField(_("Excerpt"))
    body = models.TextField(_("Body"))
    cover_image = models.ImageField(
        _("Cover Image"), upload_to="news/covers/", blank=True, null=True
    )
    category = models.ForeignKey(
        NewsCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news",
        verbose_name=_("Category"),
    )
    tags = TaggableManager(verbose_name=_("Tags"), blank=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="news_articles",
        verbose_name=_("Author"),
    )
    published_at = models.DateTimeField(_("Published At"), null=True, blank=True)
    is_published = models.BooleanField(_("Published"), default=False)
    pinned = models.BooleanField(_("Pinned"), default=False)
    views_count = models.PositiveIntegerField(_("Views"), default=0)
    external_url = models.URLField(_("External URL"), blank=True)

    class Meta:
        verbose_name = _("News")
        verbose_name_plural = _("News")
        ordering = ["-pinned", "-published_at", "-created_at"]

    def __str__(self) -> str:
        return self.title
```

- [ ] **Step 2: Create and run migration**

```bash
python manage.py makemigrations news
python manage.py migrate
```

Expected: `Applying news.0001_initial... OK`

---

### Task 5: Write serializers and views

**Files:**
- Create: `server/apps/news/serializers.py`
- Create: `server/apps/news/views.py`
- Create: `server/apps/news/urls.py`
- Create: `server/apps/news/admin.py`

- [ ] **Step 1: Write `server/apps/news/serializers.py`**

```python
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


class NewsAdminSerializer(TaggitSerializer, serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=NewsCategory.objects.all(), allow_null=True, required=False
    )
    tags = TagListSerializerField(required=False)
    author_name = serializers.ReadOnlyField(source="author.full_name")

    class Meta:
        model = News
        fields = [
            "id", "title", "slug", "excerpt", "body", "cover_image",
            "category", "tags", "author_name",
            "published_at", "is_published", "pinned",
            "views_count", "external_url", "created_at",
        ]
        read_only_fields = ["id", "slug", "views_count", "created_at", "author_name"]
```

- [ ] **Step 2: Write `server/apps/news/views.py`**

```python
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.common.renderers import GenericJSONRenderer
from apps.news.models import News, NewsCategory
from apps.news.serializers import (
    NewsAdminSerializer,
    NewsDetailSerializer,
    NewsListSerializer,
)


class NewsListAPIView(generics.ListAPIView):
    """Public: list published news, pinned first."""

    serializer_class = NewsListSerializer
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [GenericJSONRenderer]
    object_label = "news"
    pagination_class = None

    def get_queryset(self):
        return News.objects.filter(is_published=True).order_by("-pinned", "-published_at", "-created_at")


class NewsDetailAPIView(generics.RetrieveAPIView):
    """Public: get published news by slug; increments views_count."""

    serializer_class = NewsDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [GenericJSONRenderer]
    object_label = "news_item"

    def get_object(self):
        news = get_object_or_404(News, slug=self.kwargs["slug"], is_published=True)
        News.objects.filter(pk=news.pk).update(views_count=news.views_count + 1)
        news.views_count += 1
        return news


class NewsAdminListCreateAPIView(generics.ListCreateAPIView):
    """Admin: list all news (incl. drafts) and create new."""

    serializer_class = NewsAdminSerializer
    permission_classes = [permissions.IsAdminUser]
    renderer_classes = [GenericJSONRenderer]
    object_label = "news"
    pagination_class = None

    def get_queryset(self):
        return News.objects.all().order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"news_item": serializer.data},
            status=status.HTTP_201_CREATED,
        )


class NewsAdminDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: retrieve, update or delete a news item by slug."""

    serializer_class = NewsAdminSerializer
    permission_classes = [permissions.IsAdminUser]
    renderer_classes = [GenericJSONRenderer]
    object_label = "news_item"
    lookup_field = "slug"
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        return News.objects.all()
```

- [ ] **Step 3: Write `server/apps/news/urls.py`**

```python
from django.urls import path

from apps.news.views import (
    NewsAdminDetailAPIView,
    NewsAdminListCreateAPIView,
    NewsDetailAPIView,
    NewsListAPIView,
)

urlpatterns = [
    path("", NewsListAPIView.as_view(), name="news-list"),
    path("<slug:slug>/", NewsDetailAPIView.as_view(), name="news-detail"),
    path("admin/", NewsAdminListCreateAPIView.as_view(), name="news-admin-list"),
    path("admin/<slug:slug>/", NewsAdminDetailAPIView.as_view(), name="news-admin-detail"),
]
```

- [ ] **Step 4: Write `server/apps/news/admin.py`**

```python
from django.contrib import admin

from apps.news.models import News, NewsCategory


@admin.register(NewsCategory)
class NewsCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "color"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "author", "is_published", "pinned", "views_count", "published_at"]
    list_filter = ["is_published", "pinned", "category"]
    search_fields = ["title", "excerpt"]
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ["author"]
```

- [ ] **Step 5: Run all news tests**

```bash
python -m pytest apps/tests/test_news.py -v
```

Expected: all 14 tests PASS

- [ ] **Step 6: Run full test suite — no regressions**

```bash
python -m pytest apps/tests/ -v
```

Expected: all 106+ tests PASS

- [ ] **Step 7: Commit backend**

```bash
cd /Users/d.andriienko/PycharmProjects/Django-Apartment-Management
git add server/apps/news/ server/apps/tests/test_news.py server/apps/tests/factories.py server/config/settings/base.py server/config/urls.py
git commit -m "feat(news): add News + NewsCategory models, API endpoints, admin, tests"
```

---

## Chunk 2: Frontend — Redux + Pages

### Task 6: Add type definitions

**Files:**
- Modify: `client/src/types/index.d.ts`

- [ ] **Step 1: Add News types at end of file**

```typescript
export interface NewsCategory {
  id: string;
  name: string;
  slug: string;
  color: string;
}

export interface NewsItem {
  id: string;
  title: string;
  slug: string;
  excerpt: string;
  body?: string;
  cover_image: string | null;
  category: NewsCategory | null;
  tags: string[];
  author_name: string;
  published_at: string | null;
  is_published: boolean;
  pinned: boolean;
  views_count: number;
  external_url: string;
  created_at: string;
}

export interface NewsResponse {
  status_code: number;
  news: NewsItem[];
}

export interface NewsItemResponse {
  status_code: number;
  news_item: NewsItem;
}

export interface NewsCreateData {
  title: string;
  excerpt: string;
  body: string;
  is_published: boolean;
  pinned: boolean;
  category?: string | null;
  external_url?: string;
  published_at?: string | null;
}
```

---

### Task 7: Add Redux news slice

**Files:**
- Create: `client/src/lib/redux/features/news/newsApiSlice.ts`
- Modify: `client/src/lib/redux/features/api/baseApiSlice.ts` (add "News" tag)

- [ ] **Step 1: Add "News" tag to baseApiSlice**

In `baseApiSlice.ts`, find `tagTypes` array and add `"News"`.

- [ ] **Step 2: Create `newsApiSlice.ts`**

```typescript
import { NewsItemResponse, NewsResponse, NewsCreateData } from "@/types";
import { baseApiSlice } from "../api/baseApiSlice";

export const newsApiSlice = baseApiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getNews: builder.query<NewsResponse, void>({
      query: () => "/news/",
      providesTags: ["News"],
    }),

    getNewsItem: builder.query<NewsItemResponse, string>({
      query: (slug) => `/news/${slug}/`,
      providesTags: ["News"],
    }),

    adminGetAllNews: builder.query<NewsResponse, void>({
      query: () => "/news/admin/",
      providesTags: ["News"],
    }),

    adminCreateNews: builder.mutation<NewsItemResponse, NewsCreateData>({
      query: (data) => ({ url: "/news/admin/", method: "POST", body: data }),
      invalidatesTags: ["News"],
    }),

    adminUpdateNews: builder.mutation<NewsItemResponse, { slug: string } & Partial<NewsCreateData>>({
      query: ({ slug, ...data }) => ({ url: `/news/admin/${slug}/`, method: "PATCH", body: data }),
      invalidatesTags: ["News"],
    }),

    adminDeleteNews: builder.mutation<void, string>({
      query: (slug) => ({ url: `/news/admin/${slug}/`, method: "DELETE" }),
      invalidatesTags: ["News"],
    }),
  }),
});

export const {
  useGetNewsQuery,
  useGetNewsItemQuery,
  useAdminGetAllNewsQuery,
  useAdminCreateNewsMutation,
  useAdminUpdateNewsMutation,
  useAdminDeleteNewsMutation,
} = newsApiSlice;
```

---

### Task 8: Create `<ComingSoon>` component

**Files:**
- Create: `client/src/components/shared/ComingSoon.tsx`
- Modify: `client/src/app/(estate)/payments/page.tsx`
- Modify: `client/src/app/(estate)/contacts/page.tsx`

- [ ] **Step 1: Create component**

```tsx
// client/src/components/shared/ComingSoon.tsx
interface ComingSoonProps {
  serviceName: string;
  microserviceKey: string;
  description?: string;
}

export default function ComingSoon({ serviceName, microserviceKey, description }: ComingSoonProps) {
  const serviceUrl = process.env[`NEXT_PUBLIC_${microserviceKey}_URL`];

  if (serviceUrl) {
    return (
      <div className="rounded-2xl border border-[#E5E7EB] bg-white shadow-sm overflow-hidden">
        <iframe src={serviceUrl} className="w-full h-[600px]" title={serviceName} />
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 text-center shadow-sm">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#EEF3FD]">
        <svg className="h-8 w-8 text-[#2F6FED]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-[#111827]">{serviceName}</h2>
      <p className="mt-2 text-sm text-[#6B7280]">
        {description ?? "Цей розділ незабаром буде доступний."}
      </p>
      <p className="mt-3 text-xs text-[#9CA3AF] font-mono">
        {`NEXT_PUBLIC_${microserviceKey}_URL`}
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Update `payments/page.tsx`**

```tsx
import type { Metadata } from "next";
import ComingSoon from "@/components/shared/ComingSoon";

export const metadata: Metadata = { title: "Skandi Apartments | Платежі" };

export default function PaymentsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-[#111827]">Платежі</h1>
        <p className="text-sm text-[#6B7280] mt-1">Квитанції та оплата комунальних послуг</p>
      </div>
      <ComingSoon
        serviceName="Платежі"
        microserviceKey="PAYMENTS_SERVICE"
        description="Інтеграція з платіжним сервісом незабаром буде доступна."
      />
    </div>
  );
}
```

- [ ] **Step 3: Update `contacts/page.tsx`**

```tsx
import type { Metadata } from "next";
import ComingSoon from "@/components/shared/ComingSoon";

export const metadata: Metadata = { title: "Skandi Apartments | Контакти" };

export default function ContactsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-[#111827]">Контакти</h1>
        <p className="text-sm text-[#6B7280] mt-1">Контакти служб та управителя будинку</p>
      </div>
      <ComingSoon
        serviceName="Контакти"
        microserviceKey="CONTACTS_SERVICE"
        description="Довідник контактів управителя та аварійних служб незабаром буде доступний."
      />
    </div>
  );
}
```

---

### Task 9: Create `/news` list page

**Files:**
- Create: `client/src/app/(estate)/news/page.tsx`

- [ ] **Step 1: Write news list page**

```tsx
"use client";

import type { Metadata } from "next";
import { useGetNewsQuery } from "@/lib/redux/features/news/newsApiSlice";
import Link from "next/link";
import { format } from "date-fns";
import { uk } from "date-fns/locale";
import { Pin, ExternalLink } from "lucide-react";

export default function NewsPage() {
  const { data, isLoading, isError } = useGetNewsQuery();
  const newsList = data?.news ?? [];

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-bold text-[#111827]">Новини</h1>
        <div className="text-sm text-[#6B7280]">Завантаження...</div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-bold text-[#111827]">Новини</h1>
        <div className="rounded-2xl border border-red-100 bg-red-50 p-6 text-sm text-red-600">
          Не вдалося завантажити новини.
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-[#111827]">Новини</h1>
        <p className="text-sm text-[#6B7280] mt-1">Актуальні новини та оновлення порталу</p>
      </div>

      {newsList.length === 0 ? (
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 text-center shadow-sm">
          <p className="text-sm text-[#6B7280]">Новин ще немає.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {newsList.map((item) => (
            <Link
              key={item.id}
              href={`/news/${item.slug}`}
              className="group rounded-2xl border border-[#E5E7EB] bg-white shadow-sm overflow-hidden hover:shadow-md transition-shadow"
            >
              {item.cover_image && (
                <img
                  src={item.cover_image}
                  alt={item.title}
                  className="w-full h-44 object-cover"
                />
              )}
              <div className="p-4 flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  {item.pinned && (
                    <Pin className="h-3.5 w-3.5 text-[#2F6FED]" />
                  )}
                  {item.category && (
                    <span
                      className="text-xs font-medium px-2 py-0.5 rounded-full"
                      style={{ background: `${item.category.color}20`, color: item.category.color }}
                    >
                      {item.category.name}
                    </span>
                  )}
                </div>
                <h2 className="font-semibold text-[#111827] group-hover:text-[#2F6FED] transition-colors line-clamp-2">
                  {item.title}
                </h2>
                <p className="text-sm text-[#6B7280] line-clamp-3">{item.excerpt}</p>
                <div className="flex items-center justify-between mt-auto pt-2 border-t border-[#F3F4F6]">
                  <span className="text-xs text-[#9CA3AF]">
                    {item.published_at
                      ? format(new Date(item.published_at), "d MMM yyyy", { locale: uk })
                      : format(new Date(item.created_at), "d MMM yyyy", { locale: uk })}
                  </span>
                  {item.external_url && (
                    <ExternalLink className="h-3.5 w-3.5 text-[#9CA3AF]" />
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

### Task 10: Create `/news/[slug]` detail page

**Files:**
- Create: `client/src/app/(estate)/news/[slug]/page.tsx`

- [ ] **Step 1: Write detail page**

```tsx
"use client";

import { useGetNewsItemQuery } from "@/lib/redux/features/news/newsApiSlice";
import { useParams } from "next/navigation";
import { format } from "date-fns";
import { uk } from "date-fns/locale";
import { ExternalLink, Eye, Pin } from "lucide-react";
import Link from "next/link";

export default function NewsDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data, isLoading, isError } = useGetNewsItemQuery(slug);
  const item = data?.news_item;

  if (isLoading) return <div className="text-sm text-[#6B7280]">Завантаження...</div>;
  if (isError || !item) {
    return (
      <div className="rounded-2xl border border-red-100 bg-red-50 p-6 text-sm text-red-600">
        Новину не знайдено.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 max-w-3xl mx-auto">
      <Link href="/news" className="text-sm text-[#2F6FED] hover:underline">
        ← Всі новини
      </Link>

      {item.cover_image && (
        <img
          src={item.cover_image}
          alt={item.title}
          className="w-full rounded-2xl h-64 object-cover"
        />
      )}

      <div className="flex items-center gap-3 flex-wrap">
        {item.pinned && <Pin className="h-4 w-4 text-[#2F6FED]" />}
        {item.category && (
          <span
            className="text-xs font-medium px-2.5 py-1 rounded-full"
            style={{ background: `${item.category.color}20`, color: item.category.color }}
          >
            {item.category.name}
          </span>
        )}
        {item.tags.map((tag) => (
          <span key={tag} className="text-xs bg-[#F3F4F6] text-[#6B7280] px-2 py-0.5 rounded-full">
            #{tag}
          </span>
        ))}
      </div>

      <h1 className="text-3xl font-bold text-[#111827]">{item.title}</h1>

      <div className="flex items-center gap-4 text-xs text-[#9CA3AF]">
        <span>{item.author_name}</span>
        <span>
          {item.published_at
            ? format(new Date(item.published_at), "d MMMM yyyy", { locale: uk })
            : format(new Date(item.created_at), "d MMMM yyyy", { locale: uk })}
        </span>
        <span className="flex items-center gap-1">
          <Eye className="h-3.5 w-3.5" /> {item.views_count}
        </span>
      </div>

      <p className="text-[#374151] italic border-l-4 border-[#2F6FED] pl-4">{item.excerpt}</p>

      <div className="prose prose-sm max-w-none text-[#374151] whitespace-pre-wrap">
        {item.body}
      </div>

      {item.external_url && (
        <a
          href={item.external_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-sm text-[#2F6FED] hover:underline"
        >
          <ExternalLink className="h-4 w-4" /> Джерело
        </a>
      )}
    </div>
  );
}
```

---

### Task 11: Create `/admin/news` page

**Files:**
- Create: `client/src/app/admin/news/page.tsx`
- Modify: `client/src/app/admin/layout.tsx`

- [ ] **Step 1: Add news to admin nav in `layout.tsx`**

Find `adminNavLinks` array and add after posts entry:
```typescript
{ path: "/admin/news", label: "Новини (портал)", icon: Newspaper },
```

- [ ] **Step 2: Write `client/src/app/admin/news/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ColumnDef } from "@tanstack/react-table";
import { toast } from "react-toastify";
import { format } from "date-fns";
import { Plus, Pencil, Trash2, Pin } from "lucide-react";
import { DataTable } from "@/components/admin/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  useAdminGetAllNewsQuery,
  useAdminCreateNewsMutation,
  useAdminUpdateNewsMutation,
  useAdminDeleteNewsMutation,
} from "@/lib/redux/features/news/newsApiSlice";
import { NewsItem } from "@/types";

const newsSchema = z.object({
  title: z.string().min(1, "Вкажіть заголовок"),
  excerpt: z.string().min(1, "Вкажіть короткий опис"),
  body: z.string().min(1, "Вкажіть текст новини"),
  is_published: z.boolean(),
  pinned: z.boolean(),
  external_url: z.string().url("Невалідний URL").or(z.literal("")),
});

type NewsFormData = z.infer<typeof newsSchema>;

const emptyForm: NewsFormData = {
  title: "",
  excerpt: "",
  body: "",
  is_published: false,
  pinned: false,
  external_url: "",
};

export default function AdminNewsPage() {
  const { data, isLoading } = useAdminGetAllNewsQuery();
  const [createNews] = useAdminCreateNewsMutation();
  const [updateNews] = useAdminUpdateNewsMutation();
  const [deleteNews] = useAdminDeleteNewsMutation();

  const [showForm, setShowForm] = useState(false);
  const [editingSlug, setEditingSlug] = useState<string | null>(null);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<NewsFormData>({
    resolver: zodResolver(newsSchema),
    defaultValues: emptyForm,
  });

  const newsList = data?.news ?? [];

  const onSubmit = async (values: NewsFormData) => {
    try {
      if (editingSlug) {
        await updateNews({ slug: editingSlug, ...values }).unwrap();
        toast.success("Новину оновлено");
      } else {
        await createNews(values).unwrap();
        toast.success("Новину створено");
      }
      reset(emptyForm);
      setShowForm(false);
      setEditingSlug(null);
    } catch {
      toast.error("Помилка збереження");
    }
  };

  const handleEdit = (item: NewsItem) => {
    reset({
      title: item.title,
      excerpt: item.excerpt,
      body: item.body ?? "",
      is_published: item.is_published,
      pinned: item.pinned,
      external_url: item.external_url,
    });
    setEditingSlug(item.slug);
    setShowForm(true);
  };

  const handleDelete = async (slug: string) => {
    if (!confirm("Видалити новину?")) return;
    try {
      await deleteNews(slug).unwrap();
      toast.success("Новину видалено");
    } catch {
      toast.error("Помилка видалення");
    }
  };

  const columns: ColumnDef<NewsItem>[] = [
    {
      accessorKey: "title",
      header: "Заголовок",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          {row.original.pinned && <Pin className="h-3.5 w-3.5 text-[#2F6FED]" />}
          <span className="font-medium text-sm">{row.original.title}</span>
        </div>
      ),
    },
    {
      accessorKey: "is_published",
      header: "Статус",
      cell: ({ row }) => (
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          row.original.is_published
            ? "bg-green-100 text-green-700"
            : "bg-yellow-100 text-yellow-700"
        }`}>
          {row.original.is_published ? "Опубліковано" : "Чернетка"}
        </span>
      ),
    },
    {
      accessorKey: "views_count",
      header: "Перегляди",
      cell: ({ row }) => <span className="text-sm text-[#6B7280]">{row.original.views_count}</span>,
    },
    {
      accessorKey: "created_at",
      header: "Дата",
      cell: ({ row }) => (
        <span className="text-sm text-[#6B7280]">
          {format(new Date(row.original.created_at), "dd.MM.yyyy")}
        </span>
      ),
    },
    {
      id: "actions",
      header: "Дії",
      cell: ({ row }) => (
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => handleEdit(row.original)}>
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <Button size="sm" variant="outline" onClick={() => handleDelete(row.original.slug)}
            className="text-red-500 hover:text-red-700">
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[#111827]">Новини порталу</h1>
        <Button onClick={() => { setShowForm(!showForm); setEditingSlug(null); reset(emptyForm); }}>
          <Plus className="h-4 w-4 mr-2" />
          {showForm ? "Скасувати" : "Нова новина"}
        </Button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit(onSubmit)} className="rounded-2xl border border-[#E5E7EB] bg-white p-6 flex flex-col gap-4 shadow-sm">
          <h2 className="font-semibold text-[#111827]">{editingSlug ? "Редагувати" : "Нова новина"}</h2>
          <div>
            <Input placeholder="Заголовок" {...register("title")} />
            {errors.title && <p className="text-xs text-red-500 mt-1">{errors.title.message}</p>}
          </div>
          <div>
            <Textarea placeholder="Короткий опис (для картки)" rows={2} {...register("excerpt")} />
            {errors.excerpt && <p className="text-xs text-red-500 mt-1">{errors.excerpt.message}</p>}
          </div>
          <div>
            <Textarea placeholder="Повний текст новини" rows={6} {...register("body")} />
            {errors.body && <p className="text-xs text-red-500 mt-1">{errors.body.message}</p>}
          </div>
          <Input placeholder="Посилання на джерело (необов'язково)" {...register("external_url")} />
          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" {...register("is_published")} className="rounded" />
              Опублікувати
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" {...register("pinned")} className="rounded" />
              Закріпити
            </label>
          </div>
          <Button type="submit" className="self-start">
            {editingSlug ? "Зберегти зміни" : "Створити новину"}
          </Button>
        </form>
      )}

      <DataTable columns={columns} data={newsList} isLoading={isLoading} />
    </div>
  );
}
```

---

### Task 12: Update navigation constants

**Files:**
- Modify: `client/src/constants/index.ts`

- [ ] **Step 1: Rename nav link**

Change:
```typescript
{ path: "/announcements", label: "Оголошення", imgLocation: "/assets/icons/speak.svg" },
```
To:
```typescript
{ path: "/news", label: "Новини", imgLocation: "/assets/icons/speak.svg" },
```

- [ ] **Step 2: Commit frontend**

```bash
git add client/src/
git commit -m "feat(news): add /news pages, ComingSoon component, rename nav Оголошення→Новини"
```

---

## Chunk 3: README, TODO, E2E, Push

### Task 13: Update README

**Files:**
- Modify: `readme.md`

- [ ] **Step 1: Rewrite README**

```markdown
# Skandi Apartments — ОСББ Портал

Веб-портал для управління ОСББ та житловими комплексами. Мешканці подають заявки на обслуговування, переглядають новини та оголошення свого будинку, охорона керує перепустками для відвідувачів.

> **Архітектурний принцип:** Цей репозиторій — **ядро платформи**. Нові модулі (платежі, контакти, нотифікації) підключаються як окремі мікросервіси через змінні середовища.

## Можливості

### Ієрархія нерухомості
- **Будинок (Building)** → **Під'їзд (Entrance)** → **Квартира (Unit)**

### Заявки на обслуговування
- Категорії з SLA (норматив часу виконання у годинах)
- Автоматичний `due_at` та прапорець `is_overdue`
- Статуси: `reported → accepted → in_progress → done | rejected`
- Email-сповіщення при призначенні та вирішенні

### Новини порталу
- Портальні новини (адмін створює, всі мешканці бачать)
- Категорії, теги, обкладинка, закріплені новини, лічильник переглядів
- Підтримка зовнішніх посилань

### Оголошення будинку
- Прив'язані до конкретного будинку
- Мешканці бачать лише оголошення свого будинку

### Портал охорони
- Перепустки для відвідувачів (VehiclePass)
- Охорона закриває перепустку при в'їзді

### Профілі та соціальні функції
- Рейтинги технічного персоналу
- Публікації з тегами, голосуванням, закладками
- Звіти про порушення (5 скарг → блокування)

### Мікросервісна готовність
- Сторінки Платежі, Контакти — заглушки `<ComingSoon>` з `microserviceKey`
- Встановіть `NEXT_PUBLIC_{KEY}_URL` → сторінка автоматично підключить сервіс

## Технічний стек

| Шар | Технологія |
|-----|-----------|
| Backend | Django 4.2 + DRF |
| Database | PostgreSQL |
| Queue | Celery + Redis |
| Storage | MinIO (S3-compatible) |
| Frontend | Next.js 14 + TailwindCSS |
| State | Redux Toolkit + RTK Query |
| Forms | react-hook-form + Zod |
| Tests (unit) | pytest + factory_boy |
| Tests (E2E) | Playwright |
| Dev infra | Docker Compose + Nginx |

## Швидкий старт

```bash
# Клонувати
git clone <repo-url> && cd Django-Apartment-Management

# Запустити всі сервіси
make up

# Після першого запуску
make migrate && make seed
```

## Адреси після `make up`

| Сервіс | URL |
|--------|-----|
| Frontend | http://localhost:8080 |
| Django Admin | http://localhost:8080/django-admin/ |
| REST API | http://localhost:8080/api/v1/ |
| API Docs | http://localhost:8080/api/v1/redoc/ |
| MinIO | http://localhost:9090 |
| Mailpit | http://localhost:8025 |
| Flower | http://localhost:5555 |

## Тестування

```bash
make test        # unit тести (pytest)
make e2e-dev     # E2E тести (Playwright, піднімає стек)
make e2e         # повторно запустити E2E (стек вже живий)
```

## Облікові дані (seed)

| Роль | Email | Пароль |
|------|-------|--------|
| Диспетчер (staff) | dispatcher@demo.com | Demo1234! |
| Охоронець | guard@demo.com | Demo1234! |
| Мешканець | tenant@demo.com | Demo1234! |
| Мешканець 1 | resident1@demo.com | Demo1234! |

## Структура API

```
/api/v1/auth/        — аутентифікація (JWT cookie)
/api/v1/profiles/    — профілі користувачів
/api/v1/apartments/  — будинки, під'їзди, квартири
/api/v1/issues/      — заявки на обслуговування
/api/v1/news/        — новини порталу
/api/v1/posts/       — публікації + оголошення будинку
/api/v1/passes/      — перепустки охорони
/api/v1/ratings/     — рейтинги
/api/v1/reports/     — звіти про порушення
/api/v1/site-settings/ — налаштування сайту
```

## Ліцензія

BSL-1.1 — дивіться LICENSE.
```

---

### Task 14: Update TODO.md

**Files:**
- Modify: `TODO.md`

- [ ] **Step 1: Update TODO — mark completed, add News, clean stale items**

Replace content with current state (mark News as done, remove outdated items, keep future queue).

The key changes:
- Add `[x] Новини порталу (News) — модель, API, frontend /news`
- Add `[x] ComingSoon компонент для мікросервісів (payments, contacts)`
- Add `[x] Перейменування: Оголошення → Новини в навігації`
- Mark all previously completed items correctly

---

### Task 15: Write E2E tests for News

**Files:**
- Create: `sckandi-e2e/tests/functional/news-flow.spec.ts`

- [ ] **Step 1: Write E2E tests**

```typescript
/**
 * E2E tests for News feature (/news list and detail pages).
 * Requires: seed data + at least one published news item created via admin API.
 */

import { test, expect } from "@playwright/test";
import { authTest } from "../../fixtures/auth.fixture";

// ── Navigation ────────────────────────────────────────────────────────────────

authTest.describe("News navigation", () => {
  authTest("nav link 'Новини' is present and points to /news", async ({ tenantPage }) => {
    await tenantPage.goto("/welcome");
    const navLink = tenantPage.getByRole("link", { name: /^Новини$/i });
    await expect(navLink).toBeVisible({ timeout: 10_000 });
    const href = await navLink.getAttribute("href");
    expect(href).toContain("/news");
  });

  authTest("nav does NOT contain 'Оголошення' link", async ({ tenantPage }) => {
    await tenantPage.goto("/welcome");
    const oldLink = tenantPage.getByRole("link", { name: /^Оголошення$/i });
    await expect(oldLink).not.toBeVisible();
  });
});

// ── /news list page ───────────────────────────────────────────────────────────

authTest.describe("News list page", () => {
  authTest("page loads without error", async ({ tenantPage }) => {
    await tenantPage.goto("/news");
    await expect(tenantPage.getByRole("heading", { name: /Новини/i })).toBeVisible({ timeout: 10_000 });
    await expect(tenantPage.getByText(/Unhandled Runtime Error/i)).not.toBeVisible();
  });

  authTest("no .map TypeError on news page", async ({ tenantPage }) => {
    const errors: string[] = [];
    tenantPage.on("pageerror", (err) => errors.push(err.message));
    await tenantPage.goto("/news");
    await tenantPage.waitForTimeout(3_000);
    const mapErrors = errors.filter((e) => e.includes(".map is not a function"));
    expect(mapErrors).toHaveLength(0);
  });
});

// ── Admin creates news → appears in list ─────────────────────────────────────

authTest.describe("Admin news CRUD", () => {
  authTest("admin can navigate to /admin/news", async ({ staffPage }) => {
    await staffPage.goto("/admin/news");
    await expect(staffPage.getByRole("heading", { name: /Новини порталу/i })).toBeVisible({ timeout: 10_000 });
  });

  authTest("admin can open create form", async ({ staffPage }) => {
    await staffPage.goto("/admin/news");
    const addButton = staffPage.getByRole("button", { name: /Нова новина/i });
    await expect(addButton).toBeVisible({ timeout: 8_000 });
    await addButton.click();
    await expect(staffPage.getByPlaceholder(/Заголовок/i)).toBeVisible({ timeout: 5_000 });
  });
});

// ── /news detail page ─────────────────────────────────────────────────────────

test.describe("News detail page", () => {
  test("navigating to invalid slug shows error state", async ({ page }) => {
    // Login first
    const { LoginPage } = await import("../../pages/LoginPage");
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login("tenant@demo.com", "Demo1234!");
    await page.waitForURL(/\/welcome/, { timeout: 15_000 });

    await page.goto("/news/this-slug-does-not-exist-xyz");
    await expect(page.getByText(/не знайдено|not found|404/i)).toBeVisible({ timeout: 8_000 });
  });
});
```

- [ ] **Step 2: Commit E2E tests**

```bash
cd /Users/d.andriienko/PycharmProjects/sckandi-e2e
git add tests/functional/news-flow.spec.ts tests/functional/regression-bugs.spec.ts
git commit -m "feat(e2e): add news-flow tests + regression-bugs tests"
```

---

### Task 16: Final verification and push

- [ ] **Step 1: Run full unit test suite**

```bash
cd /Users/d.andriienko/PycharmProjects/Django-Apartment-Management/server
source ../.venv/bin/activate
python -m pytest apps/tests/ -v
```

Expected: all tests PASS (no regressions)

- [ ] **Step 2: Verify server running with new news endpoint**

```bash
python3 -c "
import urllib.request, json
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
data = json.dumps({'email':'dispatcher@demo.com','password':'Demo1234!'}).encode()
req = urllib.request.Request('http://localhost:8080/api/v1/auth/login/', data=data, headers={'Content-Type':'application/json'}, method='POST')
opener.open(req)
resp = opener.open(urllib.request.Request('http://localhost:8080/api/v1/news/'))
print(json.loads(resp.read().decode()))
"
```

Expected: `{'status_code': 200, 'news': [...]}`

- [ ] **Step 3: Push main repo**

```bash
cd /Users/d.andriienko/PycharmProjects/Django-Apartment-Management
git push
```

- [ ] **Step 4: Push E2E repo**

```bash
cd /Users/d.andriienko/PycharmProjects/sckandi-e2e
git push
```

---

## Summary of files changed

### New files
```
server/apps/news/__init__.py
server/apps/news/apps.py
server/apps/news/models.py
server/apps/news/serializers.py
server/apps/news/views.py
server/apps/news/urls.py
server/apps/news/admin.py
server/apps/news/migrations/__init__.py
server/apps/news/migrations/0001_initial.py  (auto-generated)
server/apps/tests/test_news.py
client/src/lib/redux/features/news/newsApiSlice.ts
client/src/app/(estate)/news/page.tsx
client/src/app/(estate)/news/[slug]/page.tsx
client/src/app/admin/news/page.tsx
client/src/components/shared/ComingSoon.tsx
docs/superpowers/specs/2026-03-12-news-design.md
docs/superpowers/plans/2026-03-12-news-feature.md
sckandi-e2e/tests/functional/news-flow.spec.ts
```

### Modified files
```
server/config/settings/base.py        (INSTALLED_APPS)
server/config/urls.py                 (add /api/v1/news/)
server/apps/tests/factories.py        (NewsCategory + News factories)
client/src/types/index.d.ts           (News types)
client/src/lib/redux/features/api/baseApiSlice.ts  (News tag)
client/src/app/admin/layout.tsx       (add /admin/news nav link)
client/src/app/(estate)/payments/page.tsx    (ComingSoon)
client/src/app/(estate)/contacts/page.tsx    (ComingSoon)
client/src/constants/index.ts         (rename nav link)
readme.md
TODO.md
```
