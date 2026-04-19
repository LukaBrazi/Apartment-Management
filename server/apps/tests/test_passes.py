"""Tests for VehiclePass feature (guard portal)."""
import datetime
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.organizations.models import Organization, OrganizationMembership, OrgRole
from apps.passes.models import VehiclePass
from apps.tests.factories import (
    BuildingFactory,
    EntranceFactory,
    ResidencyFactory,
    UnitFactory,
    UserFactory,
)


def _make_org():
    suffix = uuid4().hex[:6]
    return Organization.objects.create(
        name=f"Org-{suffix}", slug=f"passes-{suffix}", is_active=True
    )


def _add_membership(user, org, role=OrgRole.RESIDENT):
    return OrganizationMembership.objects.create(
        user=user, organization=org, role=role, is_active=True
    )


def _make_profile(user, occupation):
    profile = user.profile
    profile.occupation = occupation
    profile.save(update_fields=["occupation"])
    return profile


def _make_tenant_with_unit(org=None):
    """Create a tenant wired to a Unit via a primary ``Residency`` (PR-11 canonical).

    When ``org`` is supplied, the tenant is also granted an active
    ``OrganizationMembership`` in that org — required for the strict
    multi-tenant list/filter endpoints to return any rows.
    """
    user = UserFactory()
    _make_profile(user, "tenant")
    building = BuildingFactory()
    entrance = EntranceFactory(building=building)
    unit = UnitFactory(entrance=entrance)
    ResidencyFactory(user=user, unit=unit, is_primary=True)
    if org is not None:
        _add_membership(user, org, role=OrgRole.RESIDENT)
    return user, building


def _make_guard(org=None):
    user = UserFactory()
    _make_profile(user, "guard")
    if org is not None:
        _add_membership(user, org, role=OrgRole.STAFF)
    return user


def _api(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user=user)
    return client


LIST_URL = "/api/v1/passes/"
MY_URL = "/api/v1/passes/my/"


@pytest.mark.django_db
class TestVehiclePassCreate:
    def test_tenant_can_create_pass(self):
        tenant, _ = _make_tenant_with_unit()
        resp = _api(tenant).post(
            LIST_URL,
            {"car_number": "AA1234BB", "comment": "My friend", "visit_date": str(datetime.date.today())},
            format="json",
        )
        assert resp.status_code == 201
        assert VehiclePass.objects.filter(tenant=tenant).exists()

    def test_tenant_can_create_pass_without_car_number(self):
        tenant, _ = _make_tenant_with_unit()
        resp = _api(tenant).post(
            LIST_URL,
            {"car_number": "", "comment": "Walk-in", "visit_date": str(datetime.date.today())},
            format="json",
        )
        assert resp.status_code == 201

    def test_guard_cannot_create_pass(self):
        guard = _make_guard()
        resp = _api(guard).post(
            LIST_URL,
            {"car_number": "XX9999", "comment": "", "visit_date": str(datetime.date.today())},
            format="json",
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_pass(self):
        resp = _api().post(
            LIST_URL,
            {"car_number": "AA0000", "comment": "", "visit_date": str(datetime.date.today())},
            format="json",
        )
        assert resp.status_code == 401

    def test_pass_created_via_api_is_scoped_to_unit_organization(self):
        """Regression: a tenant-created pass MUST carry ``organization``.

        ``MyVehiclePassListAPIView`` filters on
        ``organization__in=get_user_organizations(user)`` with no
        fallback — a pass written with ``organization=NULL`` is invisible
        to its own tenant.  Earlier the serializer only tried to resolve
        org via the membership lookup; if that silently returned None
        the pass was created orphaned.  The serializer now derives org
        from the unit (authoritative: Unit → Organization is 1:1), and
        ``VehiclePass.save`` repeats the derivation as a belt-and-braces
        safety net.
        """
        org = _make_org()
        # Build the full topology org → building → entrance → unit so
        # Unit.save() auto-derives unit.organization.
        building = BuildingFactory(organization=org)
        entrance = EntranceFactory(building=building)
        unit = UnitFactory(entrance=entrance)
        assert unit.organization_id == org.pkid  # sanity: auto-derivation fired

        tenant = UserFactory()
        _make_profile(tenant, "tenant")
        ResidencyFactory(user=tenant, unit=unit, is_primary=True)
        _add_membership(tenant, org, role=OrgRole.RESIDENT)

        resp = _api(tenant).post(
            LIST_URL,
            {
                "car_number": "AA1234BB",
                "comment": "regression test",
                "visit_date": str(datetime.date.today()),
            },
            format="json",
        )
        assert resp.status_code == 201
        created = VehiclePass.objects.get(tenant=tenant, car_number="AA1234BB")
        assert created.organization_id == org.pkid, (
            "pass must be tagged with the tenant's org or /passes/my/ will hide it"
        )

        # And the tenant must actually see it in their own list — the
        # end-to-end symptom the earlier bug produced.
        my_resp = _api(tenant).get(MY_URL)
        assert my_resp.status_code == 200
        assert my_resp.data["count"] == 1

    def test_pass_save_backfills_organization_from_unit(self):
        """Model-level safety net: direct ``VehiclePass.objects.create``
        with ``unit=`` but without ``organization=`` must still end up
        with the unit's org on the row.  Protects against future
        callers (signals, admin actions, ad-hoc scripts) that forget
        to set the FK explicitly.
        """
        org = _make_org()
        building = BuildingFactory(organization=org)
        entrance = EntranceFactory(building=building)
        unit = UnitFactory(entrance=entrance)

        tenant = UserFactory()
        vp = VehiclePass.objects.create(
            tenant=tenant, unit=unit, visit_date=datetime.date.today()
        )
        vp.refresh_from_db()
        assert vp.organization_id == org.pkid


@pytest.mark.django_db
class TestVehiclePassList:
    def test_guard_can_list_passes(self):
        org = _make_org()
        tenant, _ = _make_tenant_with_unit(org=org)
        guard = _make_guard(org=org)
        VehiclePass.objects.create(
            tenant=tenant, visit_date=datetime.date.today(), organization=org
        )
        resp = _api(guard).get(LIST_URL)
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_tenant_cannot_list_all_passes(self):
        tenant, _ = _make_tenant_with_unit()
        resp = _api(tenant).get(LIST_URL)
        assert resp.status_code == 403

    def test_guard_can_filter_by_date(self):
        org = _make_org()
        tenant, _ = _make_tenant_with_unit(org=org)
        guard = _make_guard(org=org)
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        VehiclePass.objects.create(tenant=tenant, visit_date=today, organization=org)
        VehiclePass.objects.create(
            tenant=tenant, visit_date=tomorrow, organization=org
        )
        resp = _api(guard).get(LIST_URL, {"visit_date": str(today)})
        assert resp.status_code == 200
        assert resp.data["count"] == 1


@pytest.mark.django_db
class TestMyVehiclePasses:
    def test_tenant_sees_own_passes(self):
        org = _make_org()
        tenant, _ = _make_tenant_with_unit(org=org)
        other_tenant, _ = _make_tenant_with_unit(org=org)
        VehiclePass.objects.create(
            tenant=tenant, visit_date=datetime.date.today(), organization=org
        )
        VehiclePass.objects.create(
            tenant=other_tenant, visit_date=datetime.date.today(), organization=org
        )
        resp = _api(tenant).get(MY_URL)
        assert resp.status_code == 200
        assert resp.data["count"] == 1


@pytest.mark.django_db
class TestCloseVehiclePass:
    def test_guard_can_close_pass(self):
        tenant, _ = _make_tenant_with_unit()
        guard = _make_guard()
        vp = VehiclePass.objects.create(tenant=tenant, visit_date=datetime.date.today())
        resp = _api(guard).post(f"/api/v1/passes/{vp.id}/close/")
        assert resp.status_code == 200
        vp.refresh_from_db()
        assert vp.status == "closed"
        assert vp.closed_by == guard

    def test_cannot_close_already_closed_pass(self):
        tenant, _ = _make_tenant_with_unit()
        guard = _make_guard()
        vp = VehiclePass.objects.create(
            tenant=tenant, visit_date=datetime.date.today(), status="closed"
        )
        resp = _api(guard).post(f"/api/v1/passes/{vp.id}/close/")
        assert resp.status_code == 400

    def test_tenant_cannot_close_pass(self):
        tenant, _ = _make_tenant_with_unit()
        vp = VehiclePass.objects.create(tenant=tenant, visit_date=datetime.date.today())
        resp = _api(tenant).post(f"/api/v1/passes/{vp.id}/close/")
        assert resp.status_code == 403
