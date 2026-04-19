"""Tests for Announcements — building-scoped visibility."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.profiles.models import Profile
from apps.tests.factories import (
    AdminUserFactory,
    AnnouncementFactory,
    BuildingFactory,
    EntranceFactory,
    UnitFactory,
    UserFactory,
)


def make_tenant_in_building(building):
    """Create a tenant user with Profile.unit linked to `building`.

    PR-7: announcements scope tenants by ``Profile.unit`` exclusively.
    """
    tenant = UserFactory()
    entrance = EntranceFactory(building=building)
    unit = UnitFactory(entrance=entrance)
    profile = Profile.objects.get(user=tenant)
    profile.unit = unit
    profile.save(update_fields=["unit"])
    # Bust any cached reverse-OneToOne descriptor on ``tenant`` so that
    # ``force_authenticate(user=tenant)`` in DRF sees the fresh profile
    # (otherwise ``user.profile.unit`` still reads as ``None`` in the view).
    if hasattr(tenant, "_state") and "profile" in getattr(tenant, "_state").fields_cache:
        tenant._state.fields_cache.pop("profile", None)
    return tenant


@pytest.mark.django_db
def test_tenant_sees_announcements_for_own_building():
    building = BuildingFactory()
    tenant = make_tenant_in_building(building)
    AnnouncementFactory(building=building, title="Вода буде відключена")
    AnnouncementFactory(building=building, title="Прибирання двору")

    client = APIClient()
    client.force_authenticate(user=tenant)
    resp = client.get(reverse("list-announcements"))

    assert resp.status_code == 200
    titles = [a["title"] for a in resp.data["results"]]
    assert "Вода буде відключена" in titles
    assert "Прибирання двору" in titles
    assert len(titles) == 2


@pytest.mark.django_db
def test_tenant_does_not_see_other_building_announcements():
    building1 = BuildingFactory()
    building2 = BuildingFactory()
    tenant = make_tenant_in_building(building1)
    AnnouncementFactory(building=building1, title="For building 1")
    AnnouncementFactory(building=building2, title="For building 2")

    client = APIClient()
    client.force_authenticate(user=tenant)
    resp = client.get(reverse("list-announcements"))

    assert resp.status_code == 200
    titles = [a["title"] for a in resp.data["results"]]
    assert "For building 1" in titles
    assert "For building 2" not in titles


@pytest.mark.django_db
def test_inactive_announcements_not_visible():
    building = BuildingFactory()
    tenant = make_tenant_in_building(building)
    AnnouncementFactory(building=building, is_active=True, title="Active")
    AnnouncementFactory(building=building, is_active=False, title="Inactive")

    client = APIClient()
    client.force_authenticate(user=tenant)
    resp = client.get(reverse("list-announcements"))

    titles = [a["title"] for a in resp.data["results"]]
    assert "Active" in titles
    assert "Inactive" not in titles


@pytest.mark.django_db
def test_admin_sees_all_active_announcements():
    building1 = BuildingFactory()
    building2 = BuildingFactory()
    AnnouncementFactory(building=building1, title="B1 notice")
    AnnouncementFactory(building=building2, title="B2 notice")
    admin = AdminUserFactory()

    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.get(reverse("list-announcements"))

    titles = [a["title"] for a in resp.data["results"]]
    assert "B1 notice" in titles
    assert "B2 notice" in titles


@pytest.mark.django_db
def test_tenant_without_unit_sees_no_announcements():
    building = BuildingFactory()
    AnnouncementFactory(building=building, title="Some notice")
    tenant = UserFactory()  # no unit linked

    client = APIClient()
    client.force_authenticate(user=tenant)
    resp = client.get(reverse("list-announcements"))

    assert resp.status_code == 200
    assert resp.data["count"] == 0
