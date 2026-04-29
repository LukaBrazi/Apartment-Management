"""PR-14 Phase 1 — Backend visibility fix + nested create tests.

Covers two related bugs:

1. **Bug 1 (visibility regression):**  ``AdminBuildingListCreateAPIView``
   does not override ``perform_create`` and ``BuildingSerializer.fields``
   does not list ``organization`` — so a freshly created building lands
   with ``organization=None`` and disappears for the staff caller whose
   queryset filters by their orgs.

2. **Bug 2 (feature gap):** the create endpoint accepts only
   name/address/city/is_active and offers no way to seed entrances and
   units. Phase 1 adds a write-only ``entrances`` payload (list of
   ``{name, apartments_count}``) so the form can create the full
   Building → Entrance → Unit hierarchy in a single request.

The fix lives in ``apps.apartments.views.AdminBuildingListCreateAPIView``
and ``apps.apartments.serializers.BuildingSerializer``.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.apartments.models import Building, Entrance, Unit
from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrgRole,
)
from apps.tests.factories import AdminUserFactory, UserFactory


pytestmark = pytest.mark.django_db


# ── Helpers ──────────────────────────────────────────────────────────────────


def make_org(slug_prefix: str = "org") -> Organization:
    suffix = uuid4().hex[:6]
    return Organization.objects.create(
        name=f"Org-{suffix}",
        slug=f"{slug_prefix}-{suffix}",
        is_active=True,
    )


def add_membership(user, org, role: str = OrgRole.ADMIN, is_active: bool = True):
    return OrganizationMembership.objects.create(
        user=user,
        organization=org,
        role=role,
        is_active=is_active,
    )


def _client(user) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def org_a():
    return make_org("a")


@pytest.fixture
def staff_in_org(org_a):
    """Staff user (is_staff=True) but NOT a superuser. Member of org_a."""
    user = UserFactory(username=f"staff-{uuid4().hex[:4]}")
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    add_membership(user, org_a, role=OrgRole.ADMIN)
    return user


@pytest.fixture
def superuser():
    return AdminUserFactory(username=f"super-{uuid4().hex[:4]}")


# ── URLs ─────────────────────────────────────────────────────────────────────

ADMIN_LIST_CREATE_URL = "/api/v1/apartments/buildings/admin/"
LEGACY_CREATE_URL = "/api/v1/apartments/buildings/create/"


# ── Tests ────────────────────────────────────────────────────────────────────


def _basic_payload(**overrides):
    return {
        "name": "ЖК Тестовий",
        "address": "вул. Тестова, 1",
        "city": "Київ",
        "is_active": True,
        **overrides,
    }


def _unwrap(resp):
    """``GenericJSONRenderer`` envelopes the body under ``object_label``."""
    body = resp.json()
    return body.get("buildings") or body.get("building") or body


class TestVisibilityFix:
    """Regression: created building MUST be visible to its non-superuser
    creator immediately after the POST, not magically filtered out."""

    def test_admin_building_visible_in_list_after_create_for_staff_in_org(
        self, staff_in_org, org_a
    ):
        client = _client(staff_in_org)

        # Create through the *admin* nested endpoint.
        resp = client.post(
            ADMIN_LIST_CREATE_URL, _basic_payload(name="Visible-After-Create"), format="json"
        )
        assert resp.status_code == 201, resp.json()

        # The list view (same view, GET) must include the freshly created row.
        list_resp = client.get(ADMIN_LIST_CREATE_URL)
        assert list_resp.status_code == 200
        names = {b["name"] for b in _unwrap(list_resp)}
        assert "Visible-After-Create" in names, (
            "Created building was filtered out — visibility bug is back."
        )

        # And the persisted row should carry the correct organization FK.
        building = Building.objects.get(name="Visible-After-Create")
        assert building.organization_id == org_a.pkid

    def test_legacy_create_endpoint_also_assigns_organization(
        self, staff_in_org, org_a
    ):
        """The frontend currently posts to ``/buildings/create/`` (legacy
        ``BuildingCreateAPIView``).  That endpoint must apply the same
        org-assignment logic — otherwise the original Bug 1 still fires
        for users on the unmigrated form."""
        client = _client(staff_in_org)
        resp = client.post(
            LEGACY_CREATE_URL, _basic_payload(name="Legacy-Endpoint"), format="json"
        )
        assert resp.status_code == 201, resp.json()
        building = Building.objects.get(name="Legacy-Endpoint")
        assert building.organization_id == org_a.pkid


class TestOrganizationAssignment:
    def test_admin_building_creation_assigns_organization_from_caller(
        self, staff_in_org, org_a
    ):
        client = _client(staff_in_org)
        resp = client.post(
            ADMIN_LIST_CREATE_URL, _basic_payload(name="Org-Assigned"), format="json"
        )
        assert resp.status_code == 201
        building = Building.objects.get(name="Org-Assigned")
        assert building.organization_id == org_a.pkid

    def test_admin_building_creation_rejects_staff_without_org(self):
        """Staff (is_staff=True) but NO org membership must NOT silently
        create an org-less building (which would then be invisible to
        them and unowned by anyone). Reject with 400."""
        user = UserFactory(username=f"orphan-{uuid4().hex[:4]}")
        user.is_staff = True
        user.save(update_fields=["is_staff"])

        client = _client(user)
        resp = client.post(ADMIN_LIST_CREATE_URL, _basic_payload(), format="json")
        assert resp.status_code == 400
        assert not Building.objects.filter(name="ЖК Тестовий").exists()

    def test_admin_building_creation_for_superuser_without_org_succeeds(
        self, superuser
    ):
        """Superuser without orgs is the legacy / dev-superuser case
        (``AdminUserFactory``) — they may create buildings with
        ``organization=None``.  Existing tests rely on this."""
        client = _client(superuser)
        # Wipe any auto-created orgs so we genuinely test the no-orgs branch.
        Organization.objects.all().delete()
        resp = client.post(
            ADMIN_LIST_CREATE_URL, _basic_payload(name="Super-NoOrg"), format="json"
        )
        assert resp.status_code == 201
        building = Building.objects.get(name="Super-NoOrg")
        assert building.organization_id is None


class TestNestedEntrancesCreation:
    def test_admin_building_creation_with_nested_entrances_and_units(
        self, staff_in_org, org_a
    ):
        client = _client(staff_in_org)
        payload = _basic_payload(
            name="Nested",
            entrances=[{"name": "1", "apartments_count": 20}],
        )
        resp = client.post(ADMIN_LIST_CREATE_URL, payload, format="json")
        assert resp.status_code == 201, resp.json()

        building = Building.objects.get(name="Nested")
        assert building.organization_id == org_a.pkid
        entrances = list(building.entrances.all())
        assert len(entrances) == 1
        e = entrances[0]
        assert e.name == "1"
        assert e.organization_id == org_a.pkid
        units = list(Unit.objects.filter(entrance=e).order_by("number"))
        assert len(units) == 20
        # Sequential numbering "1".."20".
        numbers = [u.number for u in units]
        # Order may be lexicographic — just verify the SET of expected numbers.
        assert set(numbers) == {str(i) for i in range(1, 21)}
        # Org propagated to every unit too.
        assert all(u.organization_id == org_a.pkid for u in units)

    def test_admin_building_creation_with_two_entrances(
        self, staff_in_org, org_a
    ):
        client = _client(staff_in_org)
        payload = _basic_payload(
            name="Two-Entrances",
            entrances=[
                {"name": "1", "apartments_count": 5},
                {"name": "2", "apartments_count": 3},
            ],
        )
        resp = client.post(ADMIN_LIST_CREATE_URL, payload, format="json")
        assert resp.status_code == 201, resp.json()

        building = Building.objects.get(name="Two-Entrances")
        assert building.entrances.count() == 2
        total_units = Unit.objects.filter(entrance__building=building).count()
        assert total_units == 8

    def test_admin_building_creation_max_500_units_per_entrance(
        self, staff_in_org
    ):
        client = _client(staff_in_org)
        payload = _basic_payload(
            name="Too-Big",
            entrances=[{"name": "1", "apartments_count": 501}],
        )
        resp = client.post(ADMIN_LIST_CREATE_URL, payload, format="json")
        assert resp.status_code == 400
        assert not Building.objects.filter(name="Too-Big").exists()

    def test_admin_building_creation_duplicate_entrance_names_in_payload(
        self, staff_in_org
    ):
        client = _client(staff_in_org)
        payload = _basic_payload(
            name="Dup-Names",
            entrances=[
                {"name": "1", "apartments_count": 2},
                {"name": "1", "apartments_count": 2},
            ],
        )
        resp = client.post(ADMIN_LIST_CREATE_URL, payload, format="json")
        assert resp.status_code == 400
        assert not Building.objects.filter(name="Dup-Names").exists()

    def test_admin_building_creation_without_entrances_payload_works(
        self, staff_in_org
    ):
        """Backwards compatibility — if the client doesn't send
        ``entrances`` at all, building is created without any."""
        client = _client(staff_in_org)
        resp = client.post(
            ADMIN_LIST_CREATE_URL, _basic_payload(name="No-Entrances"), format="json"
        )
        assert resp.status_code == 201
        building = Building.objects.get(name="No-Entrances")
        assert building.entrances.count() == 0

    def test_admin_building_creation_apartments_count_zero_rejected(
        self, staff_in_org
    ):
        client = _client(staff_in_org)
        payload = _basic_payload(
            name="Zero",
            entrances=[{"name": "1", "apartments_count": 0}],
        )
        resp = client.post(ADMIN_LIST_CREATE_URL, payload, format="json")
        assert resp.status_code == 400
