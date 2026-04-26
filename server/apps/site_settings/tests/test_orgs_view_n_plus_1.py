"""Regression test: SuperAdminOrgsAPIView must NOT N+1 on memberships count.

The view used to iterate organizations and call
``org.memberships.filter(is_active=True).count()`` per row, which is O(N)
extra queries.  After PR-6 the view annotates the count in a single SQL
trip, so the total query count must stay constant regardless of N orgs.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationType,
    OrgRole,
)

User = get_user_model()


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="root_perf",
        email="root_perf@t.com",
        password="Test1234!",
        first_name="Root",
        last_name="Perf",
    )


@pytest.fixture
def orgs_with_members(db):
    """5 organizations, each with 3 active members."""
    orgs = []
    for i in range(5):
        owner = User.objects.create_user(
            username=f"perf_owner_{i}",
            email=f"perf_owner_{i}@t.com",
            password="Test1234!",
            first_name=f"Owner{i}",
            last_name="Perf",
        )
        org = Organization.objects.create(
            name=f"PerfOrg{i}",
            slug=f"perf-org-{i}",
            type=OrganizationType.HOUSING_COMPLEX,
            owner=owner,
            address=f"{i} Perf St",
            city="Kyiv",
            email=f"perf_org_{i}@t.com",
            phone=f"+38011111100{i}",
            is_active=True,
        )
        # Owner membership counts as one of the 3
        OrganizationMembership.objects.create(
            user=owner, organization=org, role=OrgRole.DIRECTOR, is_active=True
        )
        for j in range(2):
            user = User.objects.create_user(
                username=f"perf_u_{i}_{j}",
                email=f"perf_u_{i}_{j}@t.com",
                password="Test1234!",
                first_name=f"User{i}{j}",
                last_name="Perf",
            )
            OrganizationMembership.objects.create(
                user=user,
                organization=org,
                role=OrgRole.RESIDENT,
                is_active=True,
            )
        orgs.append(org)
    return orgs


@pytest.mark.django_db
class TestSuperAdminOrgsViewNPlusOne:
    def test_orgs_view_uses_constant_query_count(
        self, superuser, orgs_with_members, django_assert_num_queries
    ):
        """Should issue a small constant number of queries regardless of N orgs.

        Before PR-6: ~5 + N*1 queries (1 count() per org).  With 5 orgs that
        was ≥10.  After PR-6 the count is annotated, so the upper bound here
        is tight and stays the same as N grows.
        """
        client = APIClient()
        client.force_authenticate(user=superuser)

        # Tight bound — only the annotated SELECT + savepoint frame.
        # Anything ≥ baseline + N would indicate regression (N+1 came back).
        with django_assert_num_queries(3):
            response = client.get("/api/v1/site-settings/superadmin/orgs/")

        assert response.status_code == 200
        body = response.json()
        # GenericJSONRenderer wraps payload under self.object_label
        payload = body.get("organizations", body)
        if isinstance(payload, dict) and "organizations" in payload:
            payload = payload["organizations"]
        # Test data may coexist with seed-created orgs; assert only the 5 PerfOrg rows
        perf_rows = [row for row in payload if row["name"].startswith("PerfOrg")]
        assert len(perf_rows) == 5
        for row in perf_rows:
            assert row["members_count"] == 3
