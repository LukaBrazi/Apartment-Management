"""PR-14 Phase 2 — Admin entrance CRUD API tests.

Endpoints under test:

* ``POST  /api/v1/apartments/buildings/<pkid>/entrances/admin/`` — list + create
* ``GET   /api/v1/apartments/buildings/<pkid>/entrances/admin/`` — list
* ``PATCH /api/v1/apartments/entrances/<uuid:id>/`` — rename
* ``DELETE /api/v1/apartments/entrances/<uuid:id>/`` — delete (409 if residency)
* ``POST  /api/v1/apartments/entrances/<uuid:id>/grow/`` — append N units

The fix lives in ``apps.apartments.views``
(``AdminEntranceListCreateAPIView``, ``AdminEntranceUpdateDestroyAPIView``,
``AdminEntranceGrowAPIView``) and is wired up in
``apps.apartments.urls``.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.apartments.models import Building, Entrance, Residency, Unit
from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrgRole,
)
from apps.tests.factories import AdminUserFactory, UserFactory


pytestmark = pytest.mark.django_db


# ── Helpers ──────────────────────────────────────────────────────────────────


def _client(user) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _list_create_url(pkid: int) -> str:
    return f"/api/v1/apartments/buildings/{pkid}/entrances/admin/"


def _detail_url(eid) -> str:
    return f"/api/v1/apartments/entrances/{eid}/"


def _grow_url(eid) -> str:
    return f"/api/v1/apartments/entrances/{eid}/grow/"


@pytest.fixture
def org_a():
    suffix = uuid4().hex[:6]
    return Organization.objects.create(
        name=f"Org-A-{suffix}", slug=f"a-{suffix}", is_active=True
    )


@pytest.fixture
def staff_in_org(org_a):
    user = UserFactory(username=f"staff-{uuid4().hex[:4]}")
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    OrganizationMembership.objects.create(
        user=user, organization=org_a, role=OrgRole.ADMIN, is_active=True
    )
    return user


@pytest.fixture
def building_a(org_a):
    return Building.objects.create(
        name="Buildling-A",
        address="вул. Тестова, 1",
        city="Київ",
        organization=org_a,
        is_active=True,
    )


@pytest.fixture
def entrance_a(building_a):
    return Entrance.objects.create(
        building=building_a,
        name="1",
        organization=building_a.organization,
    )


# ── Create entrance on existing building ─────────────────────────────────────


class TestEntranceCreate:
    def test_admin_entrance_create_on_existing_building(
        self, staff_in_org, org_a, building_a
    ):
        client = _client(staff_in_org)
        resp = client.post(
            _list_create_url(building_a.pkid),
            {"name": "2", "apartments_count": 10},
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        # Entrance present
        entrance = Entrance.objects.get(building=building_a, name="2")
        assert entrance.organization_id == org_a.pkid
        # Units numbered 1..10
        units = list(Unit.objects.filter(entrance=entrance))
        assert len(units) == 10
        assert {u.number for u in units} == {str(i) for i in range(1, 11)}
        # All units carry the same org as the building.
        assert all(u.organization_id == org_a.pkid for u in units)

    def test_admin_entrance_create_duplicate_name_rejected(
        self, staff_in_org, building_a, entrance_a
    ):
        client = _client(staff_in_org)
        resp = client.post(
            _list_create_url(building_a.pkid),
            {"name": entrance_a.name, "apartments_count": 5},
            format="json",
        )
        assert resp.status_code == 400

    def test_admin_entrance_list_under_building(
        self, staff_in_org, building_a, entrance_a
    ):
        client = _client(staff_in_org)
        resp = client.get(_list_create_url(building_a.pkid))
        assert resp.status_code == 200
        body = resp.json()
        entrances = body.get("entrances") or body
        ids = {e["id"] for e in entrances}
        assert str(entrance_a.id) in ids


# ── Grow apartments inside an entrance ───────────────────────────────────────


class TestEntranceGrow:
    def test_admin_entrance_grow_apartments(
        self, staff_in_org, building_a, entrance_a
    ):
        # Pre-seed 3 units numbered "1".."3"
        for n in range(1, 4):
            Unit.objects.create(
                entrance=entrance_a,
                number=str(n),
                organization=entrance_a.building.organization,
            )
        client = _client(staff_in_org)
        resp = client.post(_grow_url(entrance_a.id), {"delta": 5}, format="json")
        assert resp.status_code == 200, resp.json()
        units = list(Unit.objects.filter(entrance=entrance_a).order_by("number"))
        # 3 + 5 = 8 — numbered "1".."8"
        assert len(units) == 8
        assert {u.number for u in units} == {str(i) for i in range(1, 9)}

    def test_admin_entrance_grow_exceeds_500(
        self, staff_in_org, building_a, entrance_a
    ):
        # Pre-seed 498
        Unit.objects.bulk_create([
            Unit(
                entrance=entrance_a,
                number=str(n),
                organization=entrance_a.building.organization,
            )
            for n in range(1, 499)
        ])
        client = _client(staff_in_org)
        resp = client.post(_grow_url(entrance_a.id), {"delta": 5}, format="json")
        assert resp.status_code == 400
        # No new units written
        assert Unit.objects.filter(entrance=entrance_a).count() == 498

    def test_admin_entrance_grow_zero_delta_rejected(
        self, staff_in_org, entrance_a
    ):
        client = _client(staff_in_org)
        resp = client.post(_grow_url(entrance_a.id), {"delta": 0}, format="json")
        assert resp.status_code == 400


# ── Rename an entrance ───────────────────────────────────────────────────────


class TestEntranceRename:
    def test_admin_entrance_rename(self, staff_in_org, entrance_a):
        client = _client(staff_in_org)
        resp = client.patch(_detail_url(entrance_a.id), {"name": "Б"}, format="json")
        assert resp.status_code == 200
        entrance_a.refresh_from_db()
        assert entrance_a.name == "Б"


# ── Delete an entrance ───────────────────────────────────────────────────────


class TestEntranceDelete:
    def test_admin_entrance_delete_succeeds_without_residencies(
        self, staff_in_org, building_a, entrance_a
    ):
        # Add some units but no residencies.
        Unit.objects.create(
            entrance=entrance_a,
            number="1",
            organization=entrance_a.building.organization,
        )
        client = _client(staff_in_org)
        resp = client.delete(_detail_url(entrance_a.id))
        assert resp.status_code == 204
        assert not Entrance.objects.filter(id=entrance_a.id).exists()

    def test_admin_entrance_delete_blocks_with_residencies(
        self, staff_in_org, building_a, entrance_a
    ):
        # Seed a unit with an active residency.
        unit = Unit.objects.create(
            entrance=entrance_a,
            number="1",
            organization=entrance_a.building.organization,
        )
        resident = UserFactory(username=f"res-{uuid4().hex[:4]}")
        Residency.objects.create(user=resident, unit=unit, role="owner")

        client = _client(staff_in_org)
        resp = client.delete(_detail_url(entrance_a.id))
        assert resp.status_code == 409
        # Not deleted
        assert Entrance.objects.filter(id=entrance_a.id).exists()


# ── Cross-org isolation on entrance endpoints ────────────────────────────────


class TestEntranceCrossOrgIsolation:
    def test_staff_a_cannot_create_entrance_under_org_b_building(
        self, staff_in_org
    ):
        # Build an org-B building the staff_in_org user is NOT a member of.
        suffix = uuid4().hex[:6]
        org_b = Organization.objects.create(
            name=f"Org-B-{suffix}", slug=f"b-{suffix}", is_active=True
        )
        building_b = Building.objects.create(
            name="B", address="x", city="x", organization=org_b
        )

        client = _client(staff_in_org)
        resp = client.post(
            _list_create_url(building_b.pkid),
            {"name": "1", "apartments_count": 2},
            format="json",
        )
        assert resp.status_code == 404

    def test_superuser_can_create_anywhere(self, building_a):
        admin = AdminUserFactory(username=f"super-{uuid4().hex[:4]}")
        client = _client(admin)
        resp = client.post(
            _list_create_url(building_a.pkid),
            {"name": "Z", "apartments_count": 2},
            format="json",
        )
        assert resp.status_code == 201
