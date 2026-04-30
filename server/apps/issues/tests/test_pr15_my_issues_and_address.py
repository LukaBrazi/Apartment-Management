"""PR-15 tests:

Phase 3 — `/profile?tab=my-issues` showed empty list because some Issue rows
have `organization=NULL` (legacy data).  ``MyIssuesListAPIView.get_queryset``
filters by ``organization__in=user_orgs`` and NULL is excluded — so the
tenant sees nothing even when ``reported_by`` is themselves.

Phase 2 — Issue serializer must expose ``building_address`` + ``city`` to the
reporter, the assignee, and staff only.  Same-org tenant who is neither
party must NOT see the address (privacy / data minimisation).
"""
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
from apps.apartments.models import Building, Entrance, Unit

User = get_user_model()


# ── Shared fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def org(db):
    owner = User.objects.create_user(
        email="pr15_owner@test.com",
        username="pr15_owner",
        first_name="PR15",
        last_name="Owner",
        password="testpass123",
    )
    organization = Organization.objects.create(
        name="PR15 Org",
        type=OrganizationType.HOUSING_COMPLEX,
        owner=owner,
        address="Main Street 1",
        city="Kyiv",
        email="pr15_org@test.com",
        phone="+380555555555",
    )
    OrganizationMembership.objects.create(
        user=owner, organization=organization, role=OrgRole.DIRECTOR
    )
    return organization


@pytest.fixture
def building_with_address(db, org):
    """A Building with concrete address + city for serializer tests."""
    return Building.objects.create(
        name="PR15 Building",
        address="вул. Шевченка, 1",
        city="Київ",
        organization=org,
    )


@pytest.fixture
def unit(db, building_with_address, org):
    entrance = Entrance.objects.create(
        building=building_with_address, name="А", organization=org
    )
    return Unit.objects.create(entrance=entrance, number="10", organization=org)


@pytest.fixture
def tenant(db, org):
    user = User.objects.create_user(
        email="pr15_tenant@test.com",
        username="pr15_tenant",
        first_name="Tenant",
        last_name="One",
        password="testpass123",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.RESIDENT
    )
    return user


@pytest.fixture
def assignee(db, org):
    user = User.objects.create_user(
        email="pr15_assignee@test.com",
        username="pr15_assignee",
        first_name="Worker",
        last_name="One",
        password="testpass123",
    )
    user.is_staff = False
    user.save()
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.STAFF
    )
    return user


@pytest.fixture
def staff(db, org):
    user = User.objects.create_user(
        email="pr15_staff@test.com",
        username="pr15_staff",
        first_name="Staff",
        last_name="One",
        password="testpass123",
    )
    user.is_staff = True
    user.save()
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.STAFF
    )
    return user


@pytest.fixture
def third_party_tenant(db, org):
    """Tenant in same org but NOT party to the issue — must not see address."""
    user = User.objects.create_user(
        email="pr15_third@test.com",
        username="pr15_third",
        first_name="Third",
        last_name="Party",
        password="testpass123",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.RESIDENT
    )
    return user


# ── Phase 3 tests — my-issues with NULL organization ─────────────────────────


@pytest.mark.django_db
class TestMyIssuesNullOrganizationFallback:
    """Bug 1 pattern reproduction: legacy Issue rows have ``organization=None``
    even though the reporter belongs to an Organization.  Before PR-15 the
    tenant saw an empty list because ``organization__in=user_orgs`` excludes
    NULL.  After the fix the queryset includes anything the user reported,
    regardless of org pin.
    """

    def test_my_issues_returns_issues_for_tenant_with_membership_when_issue_has_null_org(
        self, tenant, unit
    ):
        """Tenant has an active membership; their issue has org=NULL → must
        still appear in /my-issues/ output.
        """
        legacy_issue = Issue.objects.create(
            title="Legacy NULL-org issue",
            description="Created before org auto-pin",
            organization=None,  # Bug 1 — pre-fix data
            reported_by=tenant,
            unit=unit,
        )

        client = APIClient()
        client.force_authenticate(user=tenant)
        response = client.get("/api/v1/issues/my-issues/")

        assert response.status_code == 200
        # Renderer wraps in "my_issues"
        body = response.json()
        results = body.get("my_issues", body).get("results", [])
        ids = [item["id"] for item in results]
        assert str(legacy_issue.id) in ids, (
            "Tenant should see their own issue even when organization is NULL "
            "(legacy data fallback)."
        )

    def test_my_issues_still_returns_org_pinned_issues(
        self, tenant, unit, org
    ):
        """Sanity check — properly org-pinned issues still appear."""
        pinned_issue = Issue.objects.create(
            title="Pinned issue",
            description="Org-pinned",
            organization=org,
            reported_by=tenant,
            unit=unit,
        )

        client = APIClient()
        client.force_authenticate(user=tenant)
        response = client.get("/api/v1/issues/my-issues/")

        assert response.status_code == 200
        body = response.json()
        results = body.get("my_issues", body).get("results", [])
        ids = [item["id"] for item in results]
        assert str(pinned_issue.id) in ids

    def test_my_issues_does_not_leak_other_users_null_org_issue(
        self, tenant, third_party_tenant, unit
    ):
        """Issue reported by someone else with org=NULL must NOT leak to
        an unrelated tenant — the fallback is reporter-scoped.
        """
        other_issue = Issue.objects.create(
            title="Other user's issue",
            description="Should not leak",
            organization=None,
            reported_by=third_party_tenant,
            unit=unit,
        )

        client = APIClient()
        client.force_authenticate(user=tenant)
        response = client.get("/api/v1/issues/my-issues/")

        assert response.status_code == 200
        body = response.json()
        results = body.get("my_issues", body).get("results", [])
        ids = [item["id"] for item in results]
        assert str(other_issue.id) not in ids


# ── Phase 2 tests — address visibility ───────────────────────────────────────


@pytest.mark.django_db
class TestIssueSerializerAddressVisibility:
    """``building_address`` and ``city`` are PII-adjacent — exposing exact
    apartment address to every same-org tenant who can guess an issue ID
    is a privacy leak.  Only the reporter, the assignee, and staff get
    these fields; everyone else gets ``None``.
    """

    def _make_issue(self, org, unit, reporter, assignee=None):
        return Issue.objects.create(
            title="Address visibility issue",
            description="…",
            organization=org,
            reported_by=reporter,
            unit=unit,
            assigned_to=assignee,
        )

    def test_reporter_sees_building_address_and_city(
        self, tenant, assignee, unit, org
    ):
        issue = self._make_issue(org, unit, tenant, assignee)
        client = APIClient()
        client.force_authenticate(user=tenant)

        response = client.get(f"/api/v1/issues/{issue.id}/")
        assert response.status_code == 200

        data = response.json().get("issue", response.json())
        assert data.get("building_address") == "вул. Шевченка, 1"
        assert data.get("city") == "Київ"

    def test_assignee_sees_building_address_and_city(
        self, tenant, assignee, unit, org
    ):
        issue = self._make_issue(org, unit, tenant, assignee)
        # NB: assignee is in the same org via membership; they are also
        # the assigned worker → must see address.
        client = APIClient()
        client.force_authenticate(user=assignee)

        response = client.get(f"/api/v1/issues/{issue.id}/")
        assert response.status_code == 200
        data = response.json().get("issue", response.json())
        assert data.get("building_address") == "вул. Шевченка, 1"
        assert data.get("city") == "Київ"

    def test_staff_sees_building_address_and_city(
        self, tenant, staff, unit, org
    ):
        issue = self._make_issue(org, unit, tenant)
        client = APIClient()
        client.force_authenticate(user=staff)

        response = client.get(f"/api/v1/issues/{issue.id}/")
        assert response.status_code == 200
        data = response.json().get("issue", response.json())
        assert data.get("building_address") == "вул. Шевченка, 1"
        assert data.get("city") == "Київ"

    def test_third_party_tenant_does_not_see_building_address(
        self, tenant, third_party_tenant, unit, org
    ):
        """Same-org tenant who is neither reporter nor assignee — they
        normally cannot retrieve the issue at all (queryset filters them
        out → 404).  This test makes them the assignee to bypass the
        404, then re-checks the address: assignee SHOULD see it.

        The actual privacy invariant — non-party same-org tenant cannot
        retrieve detail at all — is covered by
        ``test_issue_detail_permission_edges.py``.  Here we only assert
        the serializer mechanics: the address fields are NOT in the
        plain ``IssueSerializer`` output for an unrelated user.

        We exercise this through the LIST endpoint where staff sees both
        rows; we then verify ``building_address`` is None for the
        unrelated row when serialized in the staff/non-party context
        — but staff IS allowed to see address.  Best assertion target
        is the serializer directly.
        """
        from apps.issues.serializers import IssueSerializer
        from rest_framework.test import APIRequestFactory

        issue = self._make_issue(org, unit, tenant)
        factory = APIRequestFactory()
        request = factory.get(f"/api/v1/issues/{issue.id}/")
        request.user = third_party_tenant

        data = IssueSerializer(issue, context={"request": request}).data
        assert data.get("building_address") is None
        assert data.get("city") is None
        # Sanity — building_name still visible (less sensitive than full address)
        assert data.get("building_name") == "PR15 Building"
