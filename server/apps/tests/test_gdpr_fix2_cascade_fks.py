"""
GDPR Fix 2 — CASCADE → SET_NULL on user-linked FK fields.

Перевіряє, що після видалення User:
- Rating зберігається (rated_user/rating_user = NULL)
- Report зберігається (reported_by/reported_user = NULL)
- VehiclePass зберігається (tenant = NULL)
- Issue зберігається (reported_by = NULL)
- Post зберігається (author = NULL)
- Reply зберігається (author = NULL)
- News зберігається (author = NULL)

Ці тести гарантують, що GDPR-erasure (Fix 3) не знищить бізнес-дані.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.ratings.models import Rating
from apps.reports.models import Report
from apps.passes.models import VehiclePass
from apps.issues.models import Issue, Category
from apps.apartments.models import Apartment
from apps.posts.models import Post, Reply
from apps.news.models import News

User = get_user_model()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        username="gdpr2_user_a", email="gdpr2_a@test.com", password="Test1234!"
    )


@pytest.fixture
def user_b(db):
    return User.objects.create_user(
        username="gdpr2_user_b", email="gdpr2_b@test.com", password="Test1234!"
    )


@pytest.fixture
def apartment(db, user_a):
    return Apartment.objects.create(
        unit_number="gdpr2_101",
        floor=1,
        building="Тестовий будинок",
        tenant=user_a,
    )


# ── Rating ────────────────────────────────────────────────────────────────────

class TestRatingSetNull:
    def test_rating_survives_rated_user_deletion(self, user_a, user_b):
        """Рейтинг залишається після видалення rated_user (SET_NULL)."""
        rating = Rating.objects.create(
            rated_user=user_a,
            rating_user=user_b,
            rating=Rating.RatingChoices.FOUR,
        )
        rating_id = rating.pk

        user_a.delete()

        rating.refresh_from_db()
        assert rating.rated_user is None, "rated_user має бути NULL після видалення"
        assert Rating.objects.filter(pk=rating_id).exists(), "Rating має зберегтись"

    def test_rating_survives_rating_user_deletion(self, user_a, user_b):
        """Рейтинг залишається після видалення rating_user (SET_NULL)."""
        rating = Rating.objects.create(
            rated_user=user_b,
            rating_user=user_a,
            rating=Rating.RatingChoices.THREE,
        )
        rating_id = rating.pk

        user_a.delete()

        rating.refresh_from_db()
        assert rating.rating_user is None, "rating_user має бути NULL після видалення"
        assert Rating.objects.filter(pk=rating_id).exists(), "Rating має зберегтись"


# ── Report ────────────────────────────────────────────────────────────────────

class TestReportSetNull:
    def test_report_survives_reported_by_deletion(self, user_a, user_b):
        """Скарга залишається після видалення автора (SET_NULL)."""
        report = Report.objects.create(
            title="Тестова скарга",
            reported_by=user_a,
            reported_user=user_b,
            description="Тест видалення користувача",
        )
        report_id = report.pk

        user_a.delete()

        report.refresh_from_db()
        assert report.reported_by is None, "reported_by має бути NULL"
        assert Report.objects.filter(pk=report_id).exists(), "Report має зберегтись"

    def test_report_survives_reported_user_deletion(self, user_a, user_b):
        """Скарга залишається після видалення відповідача (SET_NULL)."""
        report = Report.objects.create(
            title="Тестова скарга 2",
            reported_by=user_b,
            reported_user=user_a,
            description="Тест видалення відповідача",
        )
        report_id = report.pk

        user_a.delete()

        report.refresh_from_db()
        assert report.reported_user is None, "reported_user має бути NULL"
        assert Report.objects.filter(pk=report_id).exists(), "Report має зберегтись"


# ── VehiclePass ───────────────────────────────────────────────────────────────

class TestVehiclePassSetNull:
    def test_vehicle_pass_survives_tenant_deletion(self, user_a):
        """Перепустка залишається після видалення мешканця (SET_NULL)."""
        vpass = VehiclePass.objects.create(
            tenant=user_a,
            car_number="AA1234BB",
            visit_date=timezone.now().date(),
        )
        vpass_id = vpass.pk

        user_a.delete()

        vpass.refresh_from_db()
        assert vpass.tenant is None, "tenant має бути NULL після видалення"
        assert VehiclePass.objects.filter(pk=vpass_id).exists(), "VehiclePass має зберегтись"


# ── Issue ─────────────────────────────────────────────────────────────────────

class TestIssueSetNull:
    def test_issue_survives_reporter_deletion(self, user_a, apartment):
        """Заявка залишається після видалення мешканця (SET_NULL)."""
        issue = Issue.objects.create(
            apartment=apartment,
            reported_by=user_a,
            title="Тестова заявка",
            description="Тест видалення reporter",
            status=Issue.IssueStatus.REPORTED,
            priority=Issue.Priority.LOW,
        )
        issue_id = issue.pk

        user_a.delete()

        issue.refresh_from_db()
        assert issue.reported_by is None, "reported_by має бути NULL після видалення"
        assert Issue.objects.filter(pk=issue_id).exists(), "Issue має зберегтись"


# ── Post / Reply ──────────────────────────────────────────────────────────────

class TestPostSetNull:
    def test_post_survives_author_deletion(self, user_a):
        """Пост залишається після видалення автора (SET_NULL)."""
        post = Post.objects.create(
            title="Тестовий пост GDPR",
            body="Тіло посту",
            author=user_a,
        )
        post_id = post.pk

        user_a.delete()

        post.refresh_from_db()
        assert post.author is None, "author має бути NULL після видалення"
        assert Post.objects.filter(pk=post_id).exists(), "Post має зберегтись"

    def test_reply_survives_author_deletion(self, user_a, user_b):
        """Відповідь залишається після видалення автора (SET_NULL)."""
        post = Post.objects.create(
            title="Пост для відповіді GDPR",
            body="Тіло",
            author=user_b,
        )
        reply = Reply.objects.create(
            post=post,
            author=user_a,
            body="Тестова відповідь",
        )
        reply_id = reply.pk

        user_a.delete()

        reply.refresh_from_db()
        assert reply.author is None, "author має бути NULL після видалення"
        assert Reply.objects.filter(pk=reply_id).exists(), "Reply має зберегтись"


# ── News ──────────────────────────────────────────────────────────────────────

class TestNewsSetNull:
    def test_news_survives_author_deletion(self, user_a):
        """Новина залишається після видалення автора (SET_NULL)."""
        article = News.objects.create(
            title="Тестова новина GDPR",
            body="Тіло новини",
            author=user_a,
        )
        article_id = article.pk

        user_a.delete()

        article.refresh_from_db()
        assert article.author is None, "author має бути NULL після видалення"
        assert News.objects.filter(pk=article_id).exists(), "News має зберегтись"
