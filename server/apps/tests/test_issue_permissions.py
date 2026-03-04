"""Tests for Issue permissions + Unit linkage."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.apartments.models import Unit
from apps.issues.models import Issue
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
    """Helper: create a Unit backed by an Apartment owned by `user`."""
    apt = ApartmentFactory(tenant=user)
    entrance = EntranceFactory(building=BuildingFactory())
    unit = UnitFactory(entrance=entrance, number=apt.unit_number, apartment=apt)
    return unit, apt


@pytest.mark.django_db
def test_tenant_can_create_issue_for_own_unit():
    tenant = UserFactory()
    unit, apt = make_unit_with_tenant(tenant)

    client = APIClient()
    client.force_authenticate(user=tenant)
    url = reverse("create-issue-by-unit", kwargs={"unit_id": unit.pk})
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
    url = reverse("create-issue-by-unit", kwargs={"unit_id": unit2.pk})
    resp = client.post(url, {
        "title": "Unauthorized issue",
        "description": "Should not be allowed",
        "priority": "low",
    })
    assert resp.status_code == 403


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
    url = reverse("create-issue-by-unit", kwargs={"unit_id": unit.pk})
    resp = client.post(url, {
        "title": "Elevator broken",
        "description": "Elevator is stuck on floor 3",
        "priority": "medium",
    })
    assert resp.status_code == 201
    issue = Issue.objects.first()
    assert issue.unit_id == unit.pk
    assert issue.apartment_id == apt.pk
