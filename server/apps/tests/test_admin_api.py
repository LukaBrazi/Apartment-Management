"""Tests for admin-only API endpoints: user creation, building CRUD."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.tests.factories import AdminUserFactory, BuildingFactory, UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_client():
    client = APIClient()
    admin = AdminUserFactory()
    client.force_authenticate(user=admin)
    return client


@pytest.fixture
def tenant_client():
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    return client


# ─── Admin Create User ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAdminCreateUser:
    url = "/api/v1/profiles/admin/create-user/"

    def _payload(self, **overrides):
        return {
            "email": "newuser@test.com",
            "username": "newuser",
            "first_name": "Тест",
            "last_name": "Юзер",
            "password": "StrongPass1!",
            "occupation": "tenant",
            **overrides,
        }

    def test_admin_can_create_tenant(self, admin_client):
        resp = admin_client.post(self.url, self._payload(), format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert "profile" in data
        assert data["profile"]["occupation"] == "tenant"

    def test_admin_can_create_worker(self, admin_client):
        resp = admin_client.post(
            self.url, self._payload(email="plumber@test.com", username="plumber1", occupation="plumber"), format="json"
        )
        assert resp.status_code == 201
        assert resp.json()["profile"]["occupation"] == "plumber"

    def test_admin_can_create_guard(self, admin_client):
        resp = admin_client.post(
            self.url, self._payload(email="guard@test.com", username="guard1", occupation="guard"), format="json"
        )
        assert resp.status_code == 201
        assert resp.json()["profile"]["occupation"] == "guard"

    def test_non_admin_cannot_create_user(self, tenant_client):
        resp = tenant_client.post(self.url, self._payload(), format="json")
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_user(self, api_client):
        resp = api_client.post(self.url, self._payload(), format="json")
        assert resp.status_code == 401

    def test_duplicate_email_rejected(self, admin_client):
        admin_client.post(self.url, self._payload(), format="json")
        resp = admin_client.post(self.url, self._payload(username="other"), format="json")
        assert resp.status_code == 400

    def test_duplicate_username_rejected(self, admin_client):
        admin_client.post(self.url, self._payload(), format="json")
        resp = admin_client.post(self.url, self._payload(email="other@test.com"), format="json")
        assert resp.status_code == 400

    def test_invalid_occupation_rejected(self, admin_client):
        resp = admin_client.post(self.url, self._payload(occupation="invalid_role"), format="json")
        assert resp.status_code == 400

    def test_missing_required_field_rejected(self, admin_client):
        payload = self._payload()
        del payload["password"]
        resp = admin_client.post(self.url, payload, format="json")
        assert resp.status_code == 400


# ─── Admin Building CRUD ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAdminBuildingCreate:
    url = "/api/v1/apartments/buildings/create/"

    def _payload(self, **overrides):
        return {
            "name": "ЖК Тестовий",
            "address": "вул. Тестова, 1",
            "city": "Київ",
            "is_active": True,
            **overrides,
        }

    def test_admin_can_create_building(self, admin_client):
        resp = admin_client.post(self.url, self._payload(), format="json")
        assert resp.status_code == 201
        data = resp.json()
        # DRF renderer wraps payloads — accept both shapes, but one of them
        # MUST be present (no `or True` fallback that makes the assertion vacuous).
        payload = data.get("building") or data
        assert payload.get("name") == "ЖК Тестовий", (
            f"Expected created building in response body, got: {data}"
        )
        # Verify building was persisted
        from apps.apartments.models import Building
        assert Building.objects.filter(name="ЖК Тестовий").exists()

    def test_non_admin_cannot_create_building(self, tenant_client):
        resp = tenant_client.post(self.url, self._payload(), format="json")
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_building(self, api_client):
        resp = api_client.post(self.url, self._payload(), format="json")
        assert resp.status_code == 401

    def test_missing_name_rejected(self, admin_client):
        payload = self._payload()
        del payload["name"]
        resp = admin_client.post(self.url, payload, format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestAdminBuildingUpdateDestroy:
    def _url(self, pkid):
        return f"/api/v1/apartments/buildings/{pkid}/"

    def test_admin_can_update_building(self, admin_client):
        building = BuildingFactory()
        resp = admin_client.patch(self._url(building.pkid), {"name": "Нова назва"}, format="json")
        assert resp.status_code == 200
        building.refresh_from_db()
        assert building.name == "Нова назва"

    def test_admin_can_deactivate_building(self, admin_client):
        building = BuildingFactory(is_active=True)
        resp = admin_client.patch(self._url(building.pkid), {"is_active": False}, format="json")
        assert resp.status_code == 200
        building.refresh_from_db()
        assert building.is_active is False

    def test_admin_can_delete_building(self, admin_client):
        building = BuildingFactory()
        pkid = building.pkid
        resp = admin_client.delete(self._url(pkid))
        assert resp.status_code == 204
        from apps.apartments.models import Building
        assert not Building.objects.filter(pkid=pkid).exists()

    def test_non_admin_cannot_update_building(self, tenant_client):
        building = BuildingFactory()
        resp = tenant_client.patch(self._url(building.pkid), {"name": "Хак"}, format="json")
        assert resp.status_code == 403

    def test_non_admin_cannot_delete_building(self, tenant_client):
        building = BuildingFactory()
        resp = tenant_client.delete(self._url(building.pkid))
        assert resp.status_code == 403

    def test_admin_can_retrieve_building(self, admin_client):
        building = BuildingFactory(name="Мій ЖК")
        resp = admin_client.get(self._url(building.pkid))
        assert resp.status_code == 200

    def test_404_for_missing_building(self, admin_client):
        resp = admin_client.get(self._url(99999))
        assert resp.status_code == 404


# ─── Admin Profile List ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAdminProfileList:
    url = "/api/v1/profiles/admin/all/"

    def test_admin_can_list_all_profiles(self, admin_client):
        UserFactory.create_batch(3)
        resp = admin_client.get(self.url)
        assert resp.status_code == 200

    def test_non_admin_cannot_list_all_profiles(self, tenant_client):
        resp = tenant_client.get(self.url)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_list_profiles(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == 401


# ─── Admin Profile Update ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAdminProfileUpdate:
    def _url(self, slug):
        return f"/api/v1/profiles/admin/{slug}/update/"

    def test_admin_can_update_occupation(self, admin_client):
        user = UserFactory()
        resp = admin_client.patch(self._url(user.profile.slug), {"occupation": "plumber"}, format="json")
        assert resp.status_code == 200
        user.profile.refresh_from_db()
        assert user.profile.occupation == "plumber"

    def test_non_admin_cannot_update_profile(self, tenant_client):
        user = UserFactory()
        resp = tenant_client.patch(self._url(user.profile.slug), {"occupation": "plumber"}, format="json")
        assert resp.status_code == 403

    def test_admin_can_retrieve_profile(self, admin_client):
        user = UserFactory()
        resp = admin_client.get(self._url(user.profile.slug))
        assert resp.status_code == 200
