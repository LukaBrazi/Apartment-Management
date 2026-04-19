"""Tests for issue filtering, ordering, and permission scoping."""
from uuid import uuid4

import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from apps.organizations.models import Organization, OrganizationMembership, OrgRole
from apps.tests.factories import (
    AdminUserFactory,
    BuildingFactory,
    CategoryFactory,
    EntranceFactory,
    IssueFactory,
    UnitFactory,
    UserFactory,
)


def _org(slug: str = "org") -> Organization:
    suffix = uuid4().hex[:6]
    return Organization.objects.create(
        name=f"Org-{suffix}", slug=f"{slug}-{suffix}", is_active=True
    )


def _add_membership(user, org, role: str = OrgRole.RESIDENT) -> OrganizationMembership:
    return OrganizationMembership.objects.create(
        user=user, organization=org, role=role, is_active=True
    )


@pytest.fixture
def org(db):
    return _org("shared")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def superuser_client():
    client = APIClient()
    client.force_authenticate(user=AdminUserFactory())
    return client


@pytest.fixture
def staff_client(org):
    client = APIClient()
    user = UserFactory(is_staff=True)
    _add_membership(user, org, role=OrgRole.ADMIN)
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def tenant_client(org):
    client = APIClient()
    user = UserFactory()
    _add_membership(user, org)
    client.force_authenticate(user=user)
    return client, user


LIST_URL = "/api/v1/issues/"
MY_ISSUES_URL = "/api/v1/issues/my-issues/"


# ─── Permission tests ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestIssuePermissions:
    def test_tenant_cannot_access_all_issues(self, tenant_client):
        client, _ = tenant_client
        resp = client.get(LIST_URL)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_access_all_issues(self, api_client):
        resp = api_client.get(LIST_URL)
        assert resp.status_code == 401

    def test_staff_can_access_all_issues(self, staff_client):
        client, _ = staff_client
        IssueFactory.create_batch(3)
        resp = client.get(LIST_URL)
        assert resp.status_code == 200

    def test_superuser_can_access_all_issues(self, superuser_client):
        IssueFactory.create_batch(3)
        resp = superuser_client.get(LIST_URL)
        assert resp.status_code == 200

    def test_tenant_can_access_my_issues(self, tenant_client):
        client, _ = tenant_client
        resp = client.get(MY_ISSUES_URL)
        assert resp.status_code == 200

    def test_tenant_sees_only_own_issues(self, tenant_client, org):
        client, user = tenant_client
        IssueFactory(reported_by=user, organization=org)
        IssueFactory()  # another user's issue — no org, scoped out by strict filter
        resp = client.get(MY_ISSUES_URL)
        assert resp.status_code == 200
        data = resp.json()
        issues = data.get("my_issues", {}).get("results", [])
        assert len(issues) == 1

    def test_detail_tenant_sees_own_issue(self, tenant_client):
        client, user = tenant_client
        issue = IssueFactory(reported_by=user)
        resp = client.get(f"/api/v1/issues/{issue.id}/")
        assert resp.status_code == 200

    def test_detail_tenant_cannot_see_others_issue(self, tenant_client):
        client, _ = tenant_client
        issue = IssueFactory()
        resp = client.get(f"/api/v1/issues/{issue.id}/")
        assert resp.status_code == 403


# ─── Building scoping for staff ───────────────────────────────────────────────

@pytest.mark.django_db
class TestIssueStaffBuildingScope:
    def test_staff_with_one_building_sees_only_that_building(self):
        """Staff assigned to one building sees only issues from it."""
        org = _org("scope1")
        building_a = BuildingFactory()
        building_b = BuildingFactory()

        unit_a = UnitFactory(entrance=EntranceFactory(building=building_a))
        unit_b = UnitFactory(entrance=EntranceFactory(building=building_b))

        issue_a = IssueFactory(unit=unit_a, organization=org)
        IssueFactory(unit=unit_b, organization=org)  # in-org but off-building — hidden

        staff_user = UserFactory(is_staff=True)
        _add_membership(staff_user, org, role=OrgRole.ADMIN)
        staff_user.profile.buildings.add(building_a)

        client = APIClient()
        client.force_authenticate(user=staff_user)

        resp = client.get(LIST_URL)
        assert resp.status_code == 200
        results = resp.json().get("issues", {}).get("results", [])
        assert len(results) == 1
        assert str(results[0]["id"]) == str(issue_a.id)

    def test_staff_with_multiple_buildings_sees_all_assigned(self):
        """Dispatcher assigned to multiple buildings sees all their issues."""
        org = _org("scope2")
        building_a = BuildingFactory()
        building_b = BuildingFactory()
        building_c = BuildingFactory()

        unit_a = UnitFactory(entrance=EntranceFactory(building=building_a))
        unit_b = UnitFactory(entrance=EntranceFactory(building=building_b))
        unit_c = UnitFactory(entrance=EntranceFactory(building=building_c))

        issue_a = IssueFactory(unit=unit_a, organization=org)
        issue_b = IssueFactory(unit=unit_b, organization=org)
        IssueFactory(unit=unit_c, organization=org)  # off-building — hidden

        staff_user = UserFactory(is_staff=True)
        _add_membership(staff_user, org, role=OrgRole.ADMIN)
        staff_user.profile.buildings.add(building_a, building_b)

        client = APIClient()
        client.force_authenticate(user=staff_user)

        resp = client.get(LIST_URL)
        assert resp.status_code == 200
        results = resp.json().get("issues", {}).get("results", [])
        ids = {r["id"] for r in results}
        assert str(issue_a.id) in ids
        assert str(issue_b.id) in ids
        assert len(ids) == 2

    def test_staff_without_buildings_sees_all_org_issues(self):
        """Staff with no buildings assigned sees every issue in their org."""
        org = _org("scope3")
        IssueFactory.create_batch(3, organization=org)
        staff_user = UserFactory(is_staff=True)
        _add_membership(staff_user, org, role=OrgRole.ADMIN)
        # no buildings (M2M empty) — queryset falls through to org-only filter

        client = APIClient()
        client.force_authenticate(user=staff_user)

        resp = client.get(LIST_URL)
        assert resp.status_code == 200
        results = resp.json().get("issues", {}).get("results", [])
        assert len(results) == 3

    def test_superuser_sees_all_regardless_of_buildings(self):
        """Superuser always sees all issues regardless of buildings."""
        building = BuildingFactory()
        unit = UnitFactory(entrance=EntranceFactory(building=building))
        IssueFactory(unit=unit)
        IssueFactory()

        superuser = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=superuser)

        resp = client.get(LIST_URL)
        assert resp.status_code == 200
        results = resp.json().get("issues", {}).get("results", [])
        assert len(results) == 2


# ─── Filtering ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestIssueFiltering:
    def test_filter_by_status(self, superuser_client):
        IssueFactory(status="reported")
        IssueFactory(status="done")
        resp = superuser_client.get(LIST_URL + "?status=reported")
        data = resp.json()
        results = data["issues"]["results"]
        assert all(r["status"] == "reported" for r in results)
        assert len(results) == 1

    def test_filter_by_priority(self, superuser_client):
        IssueFactory(priority="low")
        IssueFactory(priority="high")
        resp = superuser_client.get(LIST_URL + "?priority=high")
        data = resp.json()
        results = data["issues"]["results"]
        # Must filter down to exactly the priority=high row, and the row
        # must actually report priority=high — not just "not None".
        assert len(results) == 1
        assert results[0]["priority"] == "high", (
            f"Expected priority=high, got {results[0].get('priority')!r}"
        )

    def test_filter_by_category(self, superuser_client):
        cat_a = CategoryFactory()
        cat_b = CategoryFactory()
        IssueFactory(category=cat_a)
        IssueFactory(category=cat_b)
        resp = superuser_client.get(LIST_URL + f"?category={cat_a.pk}")
        data = resp.json()
        results = data["issues"]["results"]
        assert len(results) == 1
        assert results[0]["category_name"] == cat_a.name

    def test_filter_by_building(self, superuser_client):
        building = BuildingFactory()
        entrance = EntranceFactory(building=building)
        unit = UnitFactory(entrance=entrance)
        issue_in = IssueFactory(unit=unit)
        IssueFactory()  # outside building

        resp = superuser_client.get(LIST_URL + f"?building={building.pk}")
        data = resp.json()
        results = data["issues"]["results"]
        assert len(results) == 1
        assert str(results[0]["id"]) == str(issue_in.id)

    def test_filter_is_overdue_true(self, superuser_client):
        past = timezone.now() - timedelta(hours=1)
        overdue = IssueFactory(status="reported")
        overdue.due_at = past
        overdue.save()
        IssueFactory(status="reported")  # no due_at, not overdue

        resp = superuser_client.get(LIST_URL + "?is_overdue=true")
        data = resp.json()
        results = data["issues"]["results"]
        assert len(results) == 1
        assert results[0]["is_overdue"] is True

    def test_filter_is_overdue_false(self, superuser_client):
        past = timezone.now() - timedelta(hours=1)
        overdue = IssueFactory(status="reported")
        overdue.due_at = past
        overdue.save()
        not_overdue = IssueFactory(status="reported")  # no due_at

        resp = superuser_client.get(LIST_URL + "?is_overdue=false")
        data = resp.json()
        results = data["issues"]["results"]
        ids = [r["id"] for r in results]
        assert str(not_overdue.id) in ids
        assert str(overdue.id) not in ids

    def test_search_by_title(self, superuser_client):
        IssueFactory(title="Протікає кран")
        IssueFactory(title="Зламаний ліфт")
        resp = superuser_client.get(LIST_URL + "?search=кран")
        data = resp.json()
        results = data["issues"]["results"]
        assert len(results) == 1
        assert "кран" in results[0]["title"].lower()

    def test_ordering_by_priority(self, superuser_client):
        IssueFactory(priority="low")
        IssueFactory(priority="high")
        IssueFactory(priority="medium")
        resp = superuser_client.get(LIST_URL + "?ordering=priority")
        data = resp.json()
        results = data["issues"]["results"]
        priorities = [r["priority"] for r in results]
        assert priorities == sorted(priorities)


# ─── Profile unit/building fields ─────────────────────────────────────────────

@pytest.mark.django_db
class TestProfileUnitBuilding:
    def test_profile_unit_field_null_by_default(self):
        user = UserFactory()
        # PR-11: ``Profile.unit`` FK dropped — the canonical accessor is
        # ``primary_unit`` via Residency.
        assert user.profile.primary_unit is None

    def test_profile_buildings_empty_by_default(self):
        user = UserFactory()
        assert user.profile.buildings.count() == 0

    def test_assign_unit_to_profile(self):
        from apps.tests.factories import ResidencyFactory

        user = UserFactory()
        unit = UnitFactory()
        ResidencyFactory(user=user, unit=unit, is_primary=True)
        user.profile.refresh_from_db()
        assert user.profile.primary_unit == unit

    def test_assign_one_building_to_staff_profile(self):
        staff = UserFactory(is_staff=True)
        building = BuildingFactory()
        staff.profile.buildings.add(building)
        assert staff.profile.buildings.count() == 1
        assert building in staff.profile.buildings.all()

    def test_assign_multiple_buildings_to_staff_profile(self):
        staff = UserFactory(is_staff=True)
        b1, b2, b3 = BuildingFactory(), BuildingFactory(), BuildingFactory()
        staff.profile.buildings.add(b1, b2, b3)
        assert staff.profile.buildings.count() == 3
