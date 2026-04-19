"""Tests for Issue permissions + Unit linkage.

Post-PR-4 the ownership check keys on ``Profile.unit`` rather than the
legacy ``Unit.apartment.tenant`` path — the helper below wires both so
this suite survives into PR-6/PR-7 when the Apartment side is dropped.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.apartments.models import Unit
from apps.issues.models import Issue
from apps.profiles.models import Profile
from apps.tests.factories import (
    ApartmentFactory,
    BuildingFactory,
    EntranceFactory,
    UnitFactory,
    UserFactory,
    AdminUserFactory,
    IssueFactory,
)


def make_unit_with_tenant(user):
    """Create a Unit owned by ``user`` via both legacy and new paths."""
    apt = ApartmentFactory(tenant=user)
    entrance = EntranceFactory(building=BuildingFactory())
    unit = UnitFactory(entrance=entrance, number=apt.unit_number, apartment=apt)
    # PR-4 canonical ownership: Profile.unit — save via instance so any
    # cached ``user.profile`` reverse descriptor is kept in sync.
    profile = Profile.objects.get(user=user)
    profile.unit = unit
    profile.save(update_fields=["unit"])
    # Bust the reverse-accessor cache on ``user`` if it's been populated.
    if hasattr(user, "_state") and "profile" in getattr(user, "_state").fields_cache:
        user._state.fields_cache.pop("profile", None)
    return unit, apt


@pytest.mark.django_db
def test_tenant_can_create_issue_for_own_unit():
    tenant = UserFactory()
    unit, apt = make_unit_with_tenant(tenant)

    client = APIClient()
    client.force_authenticate(user=tenant)
    url = reverse("create-issue-by-unit", kwargs={"unit_id": unit.id})
    resp = client.post(url, {
        "title": "Broken pipe",
        "description": "Pipe leaks in bathroom",
        "priority": "high",
    })
    assert resp.status_code == 201, resp.data
    issue = Issue.objects.get()
    assert issue.unit == unit
    assert issue.reported_by == tenant


@pytest.mark.django_db
def test_tenant_cannot_create_issue_for_other_unit():
    tenant1 = UserFactory()
    tenant2 = UserFactory()
    # unit2 belongs to tenant2; tenant1 tries to report on it
    unit2, _ = make_unit_with_tenant(tenant2)

    client = APIClient()
    client.force_authenticate(user=tenant1)
    url = reverse("create-issue-by-unit", kwargs={"unit_id": unit2.id})
    resp = client.post(url, {
        "title": "Unauthorized issue",
        "description": "Should not be allowed",
        "priority": "low",
    })
    assert resp.status_code == 403


@pytest.mark.django_db
def test_tenant_can_create_issue_via_default_path():
    """PR-4: POST /issues/create/ resolves the Unit from profile.unit."""
    tenant = UserFactory()
    unit, apt = make_unit_with_tenant(tenant)

    client = APIClient()
    client.force_authenticate(user=tenant)
    url = reverse("create-issue-default")
    resp = client.post(url, {
        "title": "Leak in hallway",
        "description": "Water drips from the ceiling",
        "priority": "medium",
    })
    assert resp.status_code == 201, resp.data
    issue = Issue.objects.get()
    assert issue.unit == unit
    assert issue.apartment == apt
    assert issue.reported_by == tenant


@pytest.mark.django_db
def test_default_path_fails_without_profile_unit():
    """Tenant without a Unit gets a 400 instead of silently mis-creating."""
    tenant = UserFactory()
    # explicitly ensure no unit is bound
    Profile.objects.filter(user=tenant).update(unit=None)

    client = APIClient()
    client.force_authenticate(user=tenant)
    url = reverse("create-issue-default")
    resp = client.post(url, {
        "title": "No unit",
        "description": "Should fail",
        "priority": "low",
    })
    assert resp.status_code == 400


@pytest.mark.django_db
def test_admin_can_list_all_issues():
    admin = AdminUserFactory()
    apt1 = ApartmentFactory()
    apt2 = ApartmentFactory()
    IssueFactory(apartment=apt1, reported_by=UserFactory())
    IssueFactory(apartment=apt2, reported_by=UserFactory())

    client = APIClient()
    client.force_authenticate(user=admin)
    url = reverse("list-issues")
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.data["count"] == 2


@pytest.mark.django_db
def test_non_staff_cannot_list_all_issues():
    tenant = UserFactory()
    client = APIClient()
    client.force_authenticate(user=tenant)
    url = reverse("list-issues")
    resp = client.get(url)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_issue_unit_fk_saved_correctly():
    tenant = UserFactory()
    unit, apt = make_unit_with_tenant(tenant)

    client = APIClient()
    client.force_authenticate(user=tenant)
    url = reverse("create-issue-by-unit", kwargs={"unit_id": unit.id})
    resp = client.post(url, {
        "title": "Elevator broken",
        "description": "Elevator is stuck on floor 3",
        "priority": "medium",
    })
    assert resp.status_code == 201
    issue = Issue.objects.first()
    assert issue.unit_id == unit.pk
    assert issue.apartment_id == apt.pk
