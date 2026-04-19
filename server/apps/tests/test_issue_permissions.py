"""Tests for Issue permissions + Unit linkage.

Post-PR-7 the legacy ``Apartment`` model is gone.  The ownership check
keys on ``Profile.unit`` exclusively; no Apartment/tenant fallback
path remains.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.issues.models import Issue
from apps.profiles.models import Profile
from apps.tests.factories import (
    AdminUserFactory,
    BuildingFactory,
    EntranceFactory,
    IssueFactory,
    UnitFactory,
    UserFactory,
)


def make_unit_with_tenant(user):
    """Create a Unit owned by ``user`` via ``Profile.unit``."""
    entrance = EntranceFactory(building=BuildingFactory())
    unit = UnitFactory(entrance=entrance)
    # PR-4 canonical ownership: Profile.unit — save via instance so any
    # cached ``user.profile`` reverse descriptor is kept in sync.
    profile = Profile.objects.get(user=user)
    profile.unit = unit
    profile.save(update_fields=["unit"])
    # Bust the reverse-accessor cache on ``user`` if it's been populated.
    if hasattr(user, "_state") and "profile" in getattr(user, "_state").fields_cache:
        user._state.fields_cache.pop("profile", None)
    return unit


@pytest.mark.django_db
def test_tenant_can_create_issue_for_own_unit():
    tenant = UserFactory()
    unit = make_unit_with_tenant(tenant)

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
    unit2 = make_unit_with_tenant(tenant2)

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
    unit = make_unit_with_tenant(tenant)

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
    IssueFactory(reported_by=UserFactory())
    IssueFactory(reported_by=UserFactory())

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
    unit = make_unit_with_tenant(tenant)

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
