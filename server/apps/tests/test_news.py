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
