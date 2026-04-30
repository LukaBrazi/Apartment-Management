"""PR-16 tests for `MyAssignedStatsAPIView`.

Endpoint: ``GET /api/v1/issues/assigned/stats/``

Returns a flat dict with COUNT-only stats per ``Issue.IssueStatus`` value
for issues currently assigned to ``request.user``.  Used by the LeftNavbar
sidebar badge to show the number of newly-accepted assignments.

Test coverage:
- Status breakdown returned for the authenticated worker.
- Strict caller-scoping (one staff cannot see another staff's stats).
- Self-reported issues are excluded (reporter == assignee == user).
- Anonymous client → 401.
- Lock-down regex test that ``permission_classes`` stays explicit on
  the view (anti-IDOR safety in case ``DEFAULT_PERMISSION_CLASSES``
  ever gets relaxed).
"""
import inspect

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.issues.models import Issue
from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationType,
    OrgRole,
)

User = get_user_model()


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def org(db):
    owner = User.objects.create_user(
        email="pr16_owner@test.com",
        username="pr16_owner",
        first_name="PR16",
        last_name="Owner",
        password="testpass123",
    )
    organization = Organization.objects.create(
        name="PR16 Org",
        type=OrganizationType.HOUSING_COMPLEX,
        owner=owner,
        address="Main Street 1",
        city="Kyiv",
        email="pr16_org@test.com",
        phone="+380777777777",
    )
    OrganizationMembership.objects.create(
        user=owner, organization=organization, role=OrgRole.DIRECTOR
    )
    return organization


@pytest.fixture
def staff_a(db, org):
    user = User.objects.create_user(
        email="pr16_staff_a@test.com",
        username="pr16_staff_a",
        first_name="StaffA",
        last_name="Worker",
        password="testpass123",
        is_staff=True,
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.STAFF
    )
    return user


@pytest.fixture
def staff_b(db, org):
    user = User.objects.create_user(
        email="pr16_staff_b@test.com",
        username="pr16_staff_b",
        first_name="StaffB",
        last_name="Worker",
        password="testpass123",
        is_staff=True,
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.STAFF
    )
    return user


@pytest.fixture
def reporter(db, org):
    user = User.objects.create_user(
        email="pr16_reporter@test.com",
        username="pr16_reporter",
        first_name="Reporter",
        last_name="Tenant",
        password="testpass123",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.RESIDENT
    )
    return user


def _make_issue(*, org, reporter, assigned_to, status, title="Issue"):
    return Issue.objects.create(
        title=title,
        description="desc",
        organization=org,
        reported_by=reporter,
        assigned_to=assigned_to,
        status=status,
    )


# ── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestMyAssignedStatsAPIView:
    """Tests for the assigned-issues badge stats endpoint."""

    URL = "/api/v1/issues/assigned/stats/"

    def test_assigned_stats_returns_status_breakdown_for_worker(
        self, staff_a, reporter, org
    ):
        """Worker з 3 accepted, 1 in_progress, 2 done → endpoint повертає
        flat dict зі всіма 5 статусами (нулі для відсутніх)."""

        for _ in range(3):
            _make_issue(
                org=org,
                reporter=reporter,
                assigned_to=staff_a,
                status=Issue.IssueStatus.ACCEPTED,
            )
        _make_issue(
            org=org,
            reporter=reporter,
            assigned_to=staff_a,
            status=Issue.IssueStatus.IN_PROGRESS,
        )
        for _ in range(2):
            _make_issue(
                org=org,
                reporter=reporter,
                assigned_to=staff_a,
                status=Issue.IssueStatus.DONE,
            )

        client = APIClient()
        client.force_authenticate(user=staff_a)
        response = client.get(self.URL)

        assert response.status_code == 200, response.data

        # ``response.data`` is the unrendered Response payload (a flat
        # dict for this view).  ``GenericJSONRenderer`` re-wraps it under
        # ``stats`` only at the wire level (``response.json()``).
        body = response.json()
        assert body["status_code"] == 200
        assert body["stats"] == {
            "reported": 0,
            "accepted": 3,
            "in_progress": 1,
            "done": 2,
            "rejected": 0,
        }

    def test_assigned_stats_only_counts_caller_assignments(
        self, staff_a, staff_b, reporter, org
    ):
        """Stats endpoint scoped to ``request.user`` — staff_a does not see
        staff_b's assignments and vice-versa."""

        # 2 accepted assigned to staff_a
        for _ in range(2):
            _make_issue(
                org=org,
                reporter=reporter,
                assigned_to=staff_a,
                status=Issue.IssueStatus.ACCEPTED,
            )
        # 5 accepted assigned to staff_b
        for _ in range(5):
            _make_issue(
                org=org,
                reporter=reporter,
                assigned_to=staff_b,
                status=Issue.IssueStatus.ACCEPTED,
            )

        client = APIClient()

        client.force_authenticate(user=staff_a)
        resp_a = client.get(self.URL)
        assert resp_a.status_code == 200
        assert resp_a.json()["stats"]["accepted"] == 2

        client.force_authenticate(user=staff_b)
        resp_b = client.get(self.URL)
        assert resp_b.status_code == 200
        assert resp_b.json()["stats"]["accepted"] == 5

    def test_assigned_stats_excludes_self_reported(self, staff_a, org):
        """Issue де reported_by == assigned_to == user → НЕ рахується."""

        # Self-assignment — should NOT count
        _make_issue(
            org=org,
            reporter=staff_a,
            assigned_to=staff_a,
            status=Issue.IssueStatus.ACCEPTED,
        )
        # Real assignment — SHOULD count
        other_reporter = User.objects.create_user(
            email="pr16_other_reporter@test.com",
            username="pr16_other_reporter",
            first_name="Other",
            last_name="Reporter",
            password="testpass123",
        )
        OrganizationMembership.objects.create(
            user=other_reporter, organization=org, role=OrgRole.RESIDENT
        )
        _make_issue(
            org=org,
            reporter=other_reporter,
            assigned_to=staff_a,
            status=Issue.IssueStatus.ACCEPTED,
        )

        client = APIClient()
        client.force_authenticate(user=staff_a)
        response = client.get(self.URL)

        assert response.status_code == 200
        # Only the externally-reported assignment should count.
        assert response.json()["stats"]["accepted"] == 1

    def test_assigned_stats_unauthenticated_rejected(self, db):
        """Anonymous client → 401."""

        client = APIClient()
        response = client.get(self.URL)
        assert response.status_code in (401, 403)

    def test_assigned_stats_view_has_explicit_permission_classes(self):
        """Anti-IDOR lock-down: explicit ``permission_classes`` prevents
        accidental public exposure if ``DEFAULT_PERMISSION_CLASSES`` ever
        change.  Mirrors the regex lock-down pattern from PR-14/PR-15."""

        from apps.issues.views import MyAssignedStatsAPIView

        src = inspect.getsource(MyAssignedStatsAPIView)
        assert "permission_classes" in src
        assert "IsAuthenticated" in src
