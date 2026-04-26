"""Regression test: NewsListAPIView must NOT N+1 on read-state lookup.

Before PR-6 ``unread_count`` was computed via ``qs.exclude(pk__in=read_ids)``
where ``read_ids`` was a fully-evaluated list of NewsRead.news_id values for
the user.  Each News row also re-evaluated tags / category lookups during
serialization, which inflated the query count further.

After PR-6 the unread count is a single subquery, ``qs`` is prefetched for
tags + category, and the total stays well under N news articles.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.news.models import News, NewsRead

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="news_perf",
        email="news_perf@t.com",
        password="Test1234!",
        first_name="News",
        last_name="Perf",
    )


@pytest.fixture
def ten_news_with_reads(db, user):
    """10 published news items, all marked as read by ``user``."""
    items = []
    for i in range(10):
        n = News.objects.create(
            title=f"Article {i}",
            excerpt=f"Excerpt {i}",
            body=f"Body {i}",
            is_published=True,
        )
        NewsRead.objects.create(user=user, news=n)
        items.append(n)
    return items


@pytest.mark.django_db
class TestNewsListNPlusOne:
    def test_news_list_uses_bounded_query_count(
        self, user, ten_news_with_reads, django_assert_num_queries
    ):
        """Total query count must stay well under N=10 articles.

        Tight bound — anything ≥ N indicates the serializer or unread-counter
        regressed back to per-row queries.
        """
        client = APIClient()
        client.force_authenticate(user=user)

        # 5 = auth + savepoint + News select + tags prefetch + unread subquery
        with django_assert_num_queries(5):
            response = client.get("/api/v1/news/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["news"]) == 10
        # All 10 are marked read → unread_count should be 0
        assert data["unread_count"] == 0
