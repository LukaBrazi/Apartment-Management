"""TDD tests for notify_subscribers_news Celery task and the news admin create view.

Tests follow the Red → Green → Refactor cycle.

Key conventions (matching the rest of this test suite):
- ``OrganizationBot`` is created via instance + property setter (not kwargs) because
  ``encrypted_token`` is handled by the ``bot_token`` setter.
- Tasks receive ``str(instance.pk)`` — the BigAutoField integer as a string —
  not the UUID ``id`` field.  ``TimeStampedModel`` uses pkid as PK, id as UUID.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def org(db):
    from apps.organizations.models import Organization
    return Organization.objects.create(
        name="Test Org",
        slug="test-org",
        is_active=True,
        features={"telegram_notifications": True},
    )


@pytest.fixture
def bot(db, org):
    """A configured OrganizationBot — uses property setter for token encryption."""
    from apps.notifications.models import OrganizationBot
    b = OrganizationBot(
        organization=org,
        bot_username="TestBot",
        is_active=True,
        is_primary=True,
    )
    b.bot_token = "123456789:AAE-test-token-xyz"
    b.save()
    return b


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin", email="admin@test.com", password="pass"
    )


@pytest.fixture
def tg_profile(db, org):
    """An active TelegramProfile subscribed to announcements (= news broadcast)."""
    from apps.notifications.models import TelegramProfile
    user = User.objects.create_user(username="subscriber", email="sub@test.com", password="pass")
    return TelegramProfile.objects.create(
        user=user,
        organization=org,
        chat_id=99001,
        is_active=True,
        notify_announcements=True,
    )


@pytest.fixture
def news_item(db, org):
    from apps.news.models import News
    return News.objects.create(
        title="Big News",
        excerpt="Short excerpt.",
        body="Full body.",
        organization=org,
        is_published=True,
        notify_subscribers=True,
    )


# ── Task unit tests ───────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_task_fires_broadcast_when_notify_subscribers_true(news_item, bot, tg_profile):
    """Task calls send_telegram_broadcast when notify_subscribers=True and org has a bot."""
    with patch(
        "apps.notifications.tasks.send_telegram_broadcast.delay"
    ) as mock_broadcast:
        from apps.notifications.tasks import notify_subscribers_news
        notify_subscribers_news(str(news_item.pk))

    mock_broadcast.assert_called_once()
    _, chat_ids, text = mock_broadcast.call_args[0]
    assert tg_profile.chat_id in chat_ids
    assert "Big News" in text


@pytest.mark.django_db
def test_task_skips_broadcast_when_notify_subscribers_false(news_item, bot, tg_profile):
    """Task does nothing when notify_subscribers=False."""
    news_item.notify_subscribers = False
    news_item.save()

    with patch(
        "apps.notifications.tasks.send_telegram_broadcast.delay"
    ) as mock_broadcast:
        from apps.notifications.tasks import notify_subscribers_news
        notify_subscribers_news(str(news_item.pk))

    mock_broadcast.assert_not_called()


@pytest.mark.django_db
def test_task_skips_global_news_without_org(db):
    """Global news (org=None) is silently skipped — no org bot available."""
    from apps.news.models import News
    global_news = News.objects.create(
        title="Global",
        excerpt="x",
        body="y",
        organization=None,
        is_published=True,
        notify_subscribers=True,
    )

    with patch(
        "apps.notifications.tasks.send_telegram_broadcast.delay"
    ) as mock_broadcast:
        from apps.notifications.tasks import notify_subscribers_news
        notify_subscribers_news(str(global_news.pk))

    mock_broadcast.assert_not_called()


@pytest.mark.django_db
def test_task_skips_when_no_bot_configured(news_item, tg_profile):
    """No bot for org → task exits silently without broadcasting."""
    with patch(
        "apps.notifications.bot_resolver.get_bot_for_org", return_value=None
    ), patch(
        "apps.notifications.tasks.send_telegram_broadcast.delay"
    ) as mock_broadcast:
        from apps.notifications.tasks import notify_subscribers_news
        notify_subscribers_news(str(news_item.pk))

    mock_broadcast.assert_not_called()


@pytest.mark.django_db
def test_task_skips_when_no_subscribers(news_item, bot):
    """No subscribers in org → chat_ids list empty → task exits without broadcasting."""
    with patch(
        "apps.notifications.tasks.send_telegram_broadcast.delay"
    ) as mock_broadcast:
        from apps.notifications.tasks import notify_subscribers_news
        notify_subscribers_news(str(news_item.pk))

    mock_broadcast.assert_not_called()


@pytest.mark.django_db
def test_task_message_contains_link_when_platform_url_set(news_item, bot, tg_profile, settings):
    """Broadcast text includes a deep link to the article."""
    settings.PLATFORM_PUBLIC_URL = "https://apartmentos.org"

    with patch(
        "apps.notifications.tasks.send_telegram_broadcast.delay"
    ) as mock_broadcast:
        from apps.notifications.tasks import notify_subscribers_news
        notify_subscribers_news(str(news_item.pk))

    _, _, text = mock_broadcast.call_args[0]
    assert f"https://apartmentos.org/news/{news_item.slug}" in text


# ── View integration tests ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_admin_create_news_fires_task_when_notify_true(admin_user, org, bot, tg_profile):
    """POST /news/admin/ with notify_subscribers=True + is_published=True → task queued."""
    client = APIClient()
    client.force_authenticate(admin_user)

    with patch(
        "apps.notifications.tasks.notify_subscribers_news.delay"
    ) as mock_task:
        resp = client.post(
            "/api/v1/news/admin/",
            {
                "title": "New Article",
                "excerpt": "Short.",
                "body": "Full text.",
                "is_published": True,
                "notify_subscribers": True,
                "pinned": False,
                "external_url": "",
            },
            format="json",
        )

    assert resp.status_code == 201
    mock_task.assert_called_once()


@pytest.mark.django_db
def test_admin_create_news_no_task_when_notify_false(admin_user, org):
    """POST /news/admin/ with notify_subscribers=False → task NOT queued."""
    client = APIClient()
    client.force_authenticate(admin_user)

    with patch(
        "apps.notifications.tasks.notify_subscribers_news.delay"
    ) as mock_task:
        resp = client.post(
            "/api/v1/news/admin/",
            {
                "title": "Draft Article",
                "excerpt": "Short.",
                "body": "Full text.",
                "is_published": True,
                "notify_subscribers": False,
                "pinned": False,
                "external_url": "",
            },
            format="json",
        )

    assert resp.status_code == 201
    mock_task.assert_not_called()


@pytest.mark.django_db
def test_admin_create_news_no_task_when_unpublished(admin_user, org, bot, tg_profile):
    """POST /news/admin/ with notify_subscribers=True but is_published=False → task NOT queued."""
    client = APIClient()
    client.force_authenticate(admin_user)

    with patch(
        "apps.notifications.tasks.notify_subscribers_news.delay"
    ) as mock_task:
        resp = client.post(
            "/api/v1/news/admin/",
            {
                "title": "Unpublished",
                "excerpt": "Short.",
                "body": "Full text.",
                "is_published": False,
                "notify_subscribers": True,
                "pinned": False,
                "external_url": "",
            },
            format="json",
        )

    assert resp.status_code == 201
    mock_task.assert_not_called()
