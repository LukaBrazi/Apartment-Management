"""Tests for VehiclePass feature (guard portal)."""
import datetime

import pytest
from rest_framework.test import APIClient

from apps.passes.models import VehiclePass
from apps.profiles.models import Profile
from apps.tests.factories import (
    BuildingFactory,
    EntranceFactory,
    UnitFactory,
    UserFactory,
)


def _make_profile(user, occupation):
    profile = user.profile
    profile.occupation = occupation
    profile.save(update_fields=["occupation"])
    return profile


def _make_tenant_with_unit():
    """Create a tenant wired to a Unit via ``Profile.unit`` (PR-7 canonical)."""
    user = UserFactory()
    _make_profile(user, "tenant")
    building = BuildingFactory()
    entrance = EntranceFactory(building=building)
    unit = UnitFactory(entrance=entrance)
    profile = Profile.objects.get(user=user)
    profile.unit = unit
    profile.save(update_fields=["unit"])
    # Bust any cached reverse OneToOne descriptor on the user
    if hasattr(user, "_state") and "profile" in getattr(user, "_state").fields_cache:
        user._state.fields_cache.pop("profile", None)
    return user, building


def _make_guard():
    user = UserFactory()
    _make_profile(user, "guard")
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


@pytest.mark.django_db
class TestVehiclePassList:
    def test_guard_can_list_passes(self):
        tenant, _ = _make_tenant_with_unit()
        guard = _make_guard()
        VehiclePass.objects.create(tenant=tenant, visit_date=datetime.date.today())
        resp = _api(guard).get(LIST_URL)
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_tenant_cannot_list_all_passes(self):
        tenant, _ = _make_tenant_with_unit()
        resp = _api(tenant).get(LIST_URL)
        assert resp.status_code == 403

    def test_guard_can_filter_by_date(self):
        tenant, _ = _make_tenant_with_unit()
        guard = _make_guard()
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        VehiclePass.objects.create(tenant=tenant, visit_date=today)
        VehiclePass.objects.create(tenant=tenant, visit_date=tomorrow)
        resp = _api(guard).get(LIST_URL, {"visit_date": str(today)})
        assert resp.status_code == 200
        assert resp.data["count"] == 1


@pytest.mark.django_db
class TestMyVehiclePasses:
    def test_tenant_sees_own_passes(self):
        tenant, _ = _make_tenant_with_unit()
        other_tenant, _ = _make_tenant_with_unit()
        VehiclePass.objects.create(tenant=tenant, visit_date=datetime.date.today())
        VehiclePass.objects.create(tenant=other_tenant, visit_date=datetime.date.today())
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
