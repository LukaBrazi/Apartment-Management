"""TDD tests for IssueReview — mutual rating after issue is closed.

Covers:
  - Author can review worker on a done issue
  - Worker can review author on a done issue
  - Non-participant cannot review
  - Cannot review open (not-done) issue
  - Cannot review twice (unique_together)
  - GET reviews returns only reviews for that issue
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

REVIEW_URL = "/api/v1/issues/{id}/review/"
REVIEWS_URL = "/api/v1/issues/{id}/reviews/"


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def org(db):
    from apps.organizations.models import Organization
    return Organization.objects.create(
        name="Test Org", slug="review-test-org", is_active=True
    )


@pytest.fixture
def author(db):
    u = User.objects.create_user(username="author", email="author@t.com", password="pass")
    u.profile.occupation = "tenant"
    u.profile.save()
    return u


@pytest.fixture
def worker(db):
    u = User.objects.create_user(username="worker", email="worker@t.com", password="pass")
    u.profile.occupation = "plumber"
    u.profile.is_staff = True
    u.profile.save()
    return u


@pytest.fixture
def outsider(db):
    return User.objects.create_user(username="outsider", email="out@t.com", password="pass")


@pytest.fixture
def done_issue(db, org, author, worker):
    from apps.issues.models import Issue
    from unittest.mock import patch
    # Patch email sending to avoid SMTP errors
    with patch("apps.issues.models.Issue.notify_assigned_user"):
        issue = Issue.objects.create(
            title="Leaking pipe",
            description="Water everywhere",
            reported_by=author,
            assigned_to=worker,
            status=Issue.IssueStatus.DONE,
            organization=org,
        )
    return issue


@pytest.fixture
def open_issue(db, org, author, worker):
    from apps.issues.models import Issue
    with patch_email():
        issue = Issue.objects.create(
            title="Open issue",
            description="Not done yet",
            reported_by=author,
            assigned_to=worker,
            status=Issue.IssueStatus.IN_PROGRESS,
            organization=org,
        )
    return issue


def patch_email():
    from unittest.mock import patch
    return patch("apps.issues.models.Issue.notify_assigned_user")


# ── POST /review/ tests ───────────────────────────────────────────────────────


@pytest.mark.django_db
def test_author_can_review_worker(done_issue, author):
    """Issue author can rate the worker after the issue is done."""
    client = APIClient()
    client.force_authenticate(author)
    resp = client.post(
        REVIEW_URL.format(id=done_issue.id),
        {"rating": 5, "comment": "Excellent work!"},
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["rating"] == 5
    assert data["reviewee"] == done_issue.assigned_to.pk


@pytest.mark.django_db
def test_worker_can_review_author(done_issue, worker):
    """Assigned worker can rate the issue author (reporter)."""
    client = APIClient()
    client.force_authenticate(worker)
    resp = client.post(
        REVIEW_URL.format(id=done_issue.id),
        {"rating": 4, "comment": "Clear description."},
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["rating"] == 4
    assert data["reviewee"] == done_issue.reported_by.pk


@pytest.mark.django_db
def test_outsider_cannot_review(done_issue, outsider):
    """A user who is neither reporter nor assignee gets 403."""
    client = APIClient()
    client.force_authenticate(outsider)
    resp = client.post(
        REVIEW_URL.format(id=done_issue.id),
        {"rating": 3},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_cannot_review_open_issue(db, org, author, worker):
    """Reviewing an issue that is not ``done`` returns 400."""
    from apps.issues.models import Issue
    with patch_email():
        issue = Issue.objects.create(
            title="Open",
            description="In progress",
            reported_by=author,
            assigned_to=worker,
            status=Issue.IssueStatus.IN_PROGRESS,
            organization=org,
        )
    client = APIClient()
    client.force_authenticate(author)
    resp = client.post(
        REVIEW_URL.format(id=issue.id),
        {"rating": 3},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_cannot_review_twice(done_issue, author):
    """Submitting a second review from the same user returns 400."""
    client = APIClient()
    client.force_authenticate(author)
    client.post(
        REVIEW_URL.format(id=done_issue.id),
        {"rating": 5},
        format="json",
    )
    resp = client.post(
        REVIEW_URL.format(id=done_issue.id),
        {"rating": 3},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_invalid_rating_returns_400(done_issue, author):
    """Rating outside 1–5 is rejected."""
    client = APIClient()
    client.force_authenticate(author)
    resp = client.post(
        REVIEW_URL.format(id=done_issue.id),
        {"rating": 6},
        format="json",
    )
    assert resp.status_code == 400


# ── GET /reviews/ tests ───────────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_reviews_returns_both_reviews(done_issue, author, worker):
    """After both parties review, GET returns two reviews."""
    client = APIClient()

    client.force_authenticate(author)
    client.post(REVIEW_URL.format(id=done_issue.id), {"rating": 5}, format="json")

    client.force_authenticate(worker)
    client.post(REVIEW_URL.format(id=done_issue.id), {"rating": 4, "comment": "OK"}, format="json")

    client.force_authenticate(author)
    resp = client.get(REVIEWS_URL.format(id=done_issue.id))
    assert resp.status_code == 200
    assert len(resp.json()["reviews"]) == 2


@pytest.mark.django_db
def test_outsider_cannot_get_reviews(done_issue, outsider):
    """Non-participant cannot GET reviews."""
    client = APIClient()
    client.force_authenticate(outsider)
    resp = client.get(REVIEWS_URL.format(id=done_issue.id))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_unauthenticated_cannot_review(done_issue):
    """Unauthenticated request returns 401."""
    client = APIClient()
    resp = client.post(
        REVIEW_URL.format(id=done_issue.id),
        {"rating": 3},
        format="json",
    )
    assert resp.status_code == 401
