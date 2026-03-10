"""Tests for issue filtering, ordering, and permission scoping."""
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from apps.tests.factories import (
    AdminUserFactory,
    ApartmentFactory,
    BuildingFactory,
    CategoryFactory,
    EntranceFactory,
    IssueFactory,
    UnitFactory,
    UserFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def superuser_client():
    client = APIClient()
    client.force_authenticate(user=AdminUserFactory())
    return client


@pytest.fixture
def staff_client():
    client = APIClient()
    user = UserFactory(is_staff=True)
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def tenant_client():
    client = APIClient()
    user = UserFactory()
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

    def test_tenant_sees_only_own_issues(self, tenant_client):
        client, user = tenant_client
        apt = ApartmentFactory(tenant=user)
        IssueFactory(apartment=apt, reported_by=user)
        IssueFactory()  # another user's issue
        resp = client.get(MY_ISSUES_URL)
        assert resp.status_code == 200
        data = resp.json()
        issues = data.get("my_issues", {}).get("results", [])
        assert len(issues) == 1

    def test_detail_tenant_sees_own_issue(self, tenant_client):
        client, user = tenant_client
        apt = ApartmentFactory(tenant=user)
        issue = IssueFactory(apartment=apt, reported_by=user)
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
    def test_staff_with_building_sees_only_building_issues(self):
        """Staff assigned to a building should only see issues from that building."""
        building_a = BuildingFactory()
        building_b = BuildingFactory()

        entrance_a = EntranceFactory(building=building_a)
        entrance_b = EntranceFactory(building=building_b)
        unit_a = UnitFactory(entrance=entrance_a)
        unit_b = UnitFactory(entrance=entrance_b)

        issue_a = IssueFactory(unit=unit_a)
        IssueFactory(unit=unit_b)  # should NOT appear

        staff_user = UserFactory(is_staff=True)
        staff_user.profile.building = building_a
        staff_user.profile.save()

        client = APIClient()
        client.force_authenticate(user=staff_user)

        resp = client.get(LIST_URL)
        assert resp.status_code == 200
        data = resp.json()
        results = data.get("issues", {}).get("results", [])
        ids = [r["id"] for r in results]
        assert str(issue_a.id) in ids
        assert len(ids) == 1

    def test_staff_without_building_sees_all_issues(self):
        """Staff with no building assigned sees all issues."""
        IssueFactory.create_batch(3)
        staff_user = UserFactory(is_staff=True)
        # no building assigned (profile.building = None by default)

        client = APIClient()
        client.force_authenticate(user=staff_user)

        resp = client.get(LIST_URL)
        assert resp.status_code == 200
        data = resp.json()
        results = data.get("issues", {}).get("results", [])
        assert len(results) == 3

    def test_superuser_sees_all_despite_building(self):
        """Superuser always sees all issues regardless of building."""
        building = BuildingFactory()
        entrance = EntranceFactory(building=building)
        unit = UnitFactory(entrance=entrance)

        IssueFactory(unit=unit)
        IssueFactory()  # no unit / different building

        superuser = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=superuser)

        resp = client.get(LIST_URL)
        assert resp.status_code == 200
        data = resp.json()
        results = data.get("issues", {}).get("results", [])
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
        assert all(r["status"] is not None for r in results)
        assert len(results) == 1

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
        assert user.profile.unit is None

    def test_profile_building_field_null_by_default(self):
        user = UserFactory()
        assert user.profile.building is None

    def test_assign_unit_to_profile(self):
        user = UserFactory()
        unit = UnitFactory()
        user.profile.unit = unit
        user.profile.save()
        user.profile.refresh_from_db()
        assert user.profile.unit == unit

    def test_assign_building_to_staff_profile(self):
        staff = UserFactory(is_staff=True)
        building = BuildingFactory()
        staff.profile.building = building
        staff.profile.save()
        staff.profile.refresh_from_db()
        assert staff.profile.building == building
