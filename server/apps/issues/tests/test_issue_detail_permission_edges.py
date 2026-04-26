"""Edge cases for IssueDetailAPIView permission scoping.

Before PR-6 the view leaked information through a 403:
``get_queryset`` accepted any issue from the user's org, then
``get_object`` raised ``PermissionDenied`` if the user wasn't a party.
That distinct-from-not-found response let an unrelated tenant probe
which issue IDs exist inside their own organisation.

After PR-6 the entire authorisation predicate lives in
``get_queryset``: a tenant who is not the reporter, the assignee,
or staff simply doesn't see the row at all → 404.
"""
import uuid

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from apps.issues.models import Issue
from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationType,
    OrgRole,
)

User = get_user_model()


@pytest.fixture
def org(db):
    owner = User.objects.create_user(
        email="edge_owner@test.com",
        username="edge_owner",
        first_name="Edge",
        last_name="Owner",
        password="testpass123",
    )
    organization = Organization.objects.create(
        name="Edge Org",
        type=OrganizationType.HOUSING_COMPLEX,
        owner=owner,
        address="1 Edge St",
        city="Kyiv",
        email="edge_org@test.com",
        phone="+380999999999",
    )
    OrganizationMembership.objects.create(
        user=owner, organization=organization, role=OrgRole.DIRECTOR
    )
    return organization


@pytest.fixture
def tenant_a(db, org):
    user = User.objects.create_user(
        email="tenant_a@test.com",
        username="tenant_a",
        first_name="Tenant",
        last_name="A",
        password="testpass123",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.RESIDENT
    )
    return user


@pytest.fixture
def tenant_b(db, org):
    """Another tenant in the same org as tenant_a — not party to A's issues."""
    user = User.objects.create_user(
        email="tenant_b@test.com",
        username="tenant_b",
        first_name="Tenant",
        last_name="B",
        password="testpass123",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.RESIDENT
    )
    return user


@pytest.fixture
def issue_owned_by_tenant_a(db, org, tenant_a):
    return Issue.objects.create(
        title="Tenant A's Private Issue",
        description="Tenant B should NOT see this even though same org.",
        organization=org,
        reported_by=tenant_a,
    )


@pytest.mark.django_db
class TestIssueDetailGetQuerysetScoping:
    def test_tenant_in_same_org_but_not_party_gets_404(
        self, tenant_b, issue_owned_by_tenant_a
    ):
        """Same-org tenant who is neither reporter nor assignee → 404, not 403.

        404 is the correct response: the row is filtered out by
        ``get_queryset``, so the view honestly doesn't see it.  Returning
        403 would leak the existence of the issue ID.
        """
        client = APIClient()
        client.force_authenticate(user=tenant_b)

        response = client.get(f"/api/v1/issues/{issue_owned_by_tenant_a.id}/")
        assert response.status_code == 404, (
            f"Same-org non-party tenant must get 404, got {response.status_code}. "
            "PermissionDenied (403) leaks issue existence."
        )

    def test_reporter_can_access_own_issue(self, tenant_a, issue_owned_by_tenant_a):
        client = APIClient()
        client.force_authenticate(user=tenant_a)
        response = client.get(f"/api/v1/issues/{issue_owned_by_tenant_a.id}/")
        assert response.status_code == 200

    def test_assignee_can_access_assigned_issue(
        self, db, tenant_a, tenant_b, issue_owned_by_tenant_a
    ):
        """Tenant B becomes the assignee — should now see the issue."""
        issue_owned_by_tenant_a.assigned_to = tenant_b
        issue_owned_by_tenant_a.save(update_fields=["assigned_to"])

        client = APIClient()
        client.force_authenticate(user=tenant_b)
        response = client.get(f"/api/v1/issues/{issue_owned_by_tenant_a.id}/")
        assert response.status_code == 200
