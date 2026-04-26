"""TDD tests for GET /issues/my/reviewable/

Covers:
  - Returns only done issues with assigned_to for the requesting user
  - Excludes issues not yet done, not assigned, or belonging to other users
  - my_review is null when no review exists yet
  - my_review contains rating/comment after the user has reviewed
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

REVIEWABLE_URL = "/api/v1/issues/my/reviewable/"


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def org(db):
    from apps.organizations.models import Organization
    return Organization.objects.create(
        name="Reviewable Test Org", slug="reviewable-test-org", is_active=True
    )


@pytest.fixture
def tenant(db, org):
    from apps.organizations.models import OrganizationMembership, OrgRole
    u = User.objects.create_user(username="rv_tenant", email="rv_tenant@t.com", password="pass")
    u.profile.occupation = "tenant"
    u.profile.save()
    OrganizationMembership.objects.create(user=u, organization=org, role=OrgRole.RESIDENT)
    return u


@pytest.fixture
def worker(db, org):
    from apps.organizations.models import OrganizationMembership, OrgRole
    u = User.objects.create_user(username="rv_worker", email="rv_worker@t.com", password="pass")
    u.profile.occupation = "plumber"
    u.is_staff = True
    u.save()
    u.profile.save()
    OrganizationMembership.objects.create(user=u, organization=org, role=OrgRole.STAFF)
    return u


@pytest.fixture
def building(db, org):
    from apps.apartments.models import Building, Entrance, Unit
    b = Building.objects.create(name="RV Building", organization=org)
    e = Entrance.objects.create(building=b, name="1", organization=org)
    u = Unit.objects.create(entrance=e, number="10", organization=org)
    return b


@pytest.fixture
def unit(db, building, org):
    return building.entrances.first().units.first()


@pytest.fixture
def done_issue(db, tenant, worker, unit, org):
    from apps.issues.models import Issue
    return Issue.objects.create(
        reported_by=tenant,
        assigned_to=worker,
        unit=unit,
        organization=org,
        title="Leaking pipe",
        description="Water everywhere",
        status=Issue.IssueStatus.DONE,
    )


@pytest.fixture
def open_issue(db, tenant, worker, unit, org):
    from apps.issues.models import Issue
    return Issue.objects.create(
        reported_by=tenant,
        assigned_to=worker,
        unit=unit,
        organization=org,
        title="Open issue",
        description="Not yet done",
        status=Issue.IssueStatus.IN_PROGRESS,
    )


@pytest.fixture
def unassigned_done_issue(db, tenant, unit, org):
    from apps.issues.models import Issue
    return Issue.objects.create(
        reported_by=tenant,
        assigned_to=None,
        unit=unit,
        organization=org,
        title="Unassigned done",
        description="No worker",
        status=Issue.IssueStatus.DONE,
    )


@pytest.fixture
def tenant_client(tenant):
    client = APIClient()
    client.force_authenticate(user=tenant)
    return client


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestMyReviewableIssues:
    def test_returns_only_done_assigned_issues(self, tenant_client, done_issue, open_issue, unassigned_done_issue):
        """Only done+assigned issues appear — open and unassigned are excluded."""
        response = tenant_client.get(REVIEWABLE_URL)
        assert response.status_code == 200
        ids = [item["id"] for item in response.data]
        assert str(done_issue.id) in ids
        assert str(open_issue.id) not in ids
        assert str(unassigned_done_issue.id) not in ids

    def test_my_review_is_null_when_not_yet_rated(self, tenant_client, done_issue):
        response = tenant_client.get(REVIEWABLE_URL)
        assert response.status_code == 200
        item = next(i for i in response.data if i["id"] == str(done_issue.id))
        assert item["my_review"] is None

    def test_my_review_populated_after_rating(self, tenant_client, tenant, done_issue, worker):
        from apps.issues.models import IssueReview
        IssueReview.objects.create(
            issue=done_issue,
            reviewer=tenant,
            reviewee=worker,
            rating=4,
            comment="Good job",
        )
        response = tenant_client.get(REVIEWABLE_URL)
        assert response.status_code == 200
        item = next(i for i in response.data if i["id"] == str(done_issue.id))
        assert item["my_review"] is not None
        assert item["my_review"]["rating"] == 4
        assert item["my_review"]["comment"] == "Good job"

    def test_does_not_return_other_users_issues(self, db, org, worker, unit, tenant_client):
        """Issues reported by a different user must not appear."""
        from apps.issues.models import Issue
        other = User.objects.create_user(username="other_rv", email="other_rv@t.com", password="pass")
        Issue.objects.create(
            reported_by=other,
            assigned_to=worker,
            unit=unit,
            organization=org,
            title="Other user issue",
            description="Not mine",
            status=Issue.IssueStatus.DONE,
        )
        response = tenant_client.get(REVIEWABLE_URL)
        titles = [item["title"] for item in response.data]
        assert "Other user issue" not in titles

    def test_unauthenticated_returns_401(self, db):
        client = APIClient()
        response = client.get(REVIEWABLE_URL)
        assert response.status_code == 401

    def test_response_contains_expected_fields(self, tenant_client, done_issue):
        response = tenant_client.get(REVIEWABLE_URL)
        assert response.status_code == 200
        item = next(i for i in response.data if i["id"] == str(done_issue.id))
        for field in ["id", "title", "assigned_to_name", "assigned_to_username", "my_review"]:
            assert field in item
