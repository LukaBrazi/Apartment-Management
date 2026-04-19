"""PR-10 reader-cutover tests.

These tests verify that the three tenant-facing readers
(announcements, issues, passes) and the ``ProfileSerializer`` now
resolve the tenant's unit via the ``Residency`` through-model, with a
graceful fallback to the legacy ``Profile.unit`` FK while PR-10 is
live.

Scenarios:
  * Profile.primary_unit resolution order (Residency first, FK
    fallback).
  * Multi-unit tenant sees announcements for the building of their
    *primary* residency only.
  * Promoting a secondary residency to primary flips the visible
    building across all readers.
  * Multi-unit tenant can open an issue against any Unit they hold a
    Residency on (not only their primary one).
  * Pass creation uses the primary unit.
  * ProfileSerializer payload reflects the primary unit.
"""
from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.apartments.models import Residency, ResidencyRole
from apps.profiles.models import Profile
from apps.tests.factories import (
    BuildingFactory,
    EntranceFactory,
    ResidencyFactory,
    UnitFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_tenant_profile(user, occupation="tenant"):
    """Ensure the user has a tenant Profile (Profile is auto-created by
    the signal — just set occupation)."""
    profile = Profile.objects.get(user=user)
    profile.occupation = occupation
    profile.save(update_fields=["occupation"])
    return profile


def _authed(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ─── Profile.primary_unit ─────────────────────────────────────────────────────


def test_primary_unit_resolves_residency_first():
    user = UserFactory()
    _make_tenant_profile(user)
    unit_a = UnitFactory()
    unit_b = UnitFactory()

    # FK points at A but primary Residency points at B → B wins.
    profile = Profile.objects.get(user=user)
    profile._skip_residency_mirror = True  # don't auto-mirror the FK write
    profile.unit = unit_a
    profile.save()

    Residency.objects.create(
        user=user, unit=unit_b, is_primary=True, role=ResidencyRole.OWNER
    )

    profile.refresh_from_db()
    assert profile.primary_unit.pk == unit_b.pk


def test_primary_unit_falls_back_to_profile_unit_when_no_residency():
    user = UserFactory()
    _make_tenant_profile(user)
    unit = UnitFactory()

    profile = Profile.objects.get(user=user)
    profile._skip_residency_mirror = True
    profile.unit = unit
    profile.save()

    # Verify no Residency auto-created (mirror was skipped).
    assert Residency.objects.filter(user=user).count() == 0
    assert profile.primary_unit.pk == unit.pk


def test_primary_unit_returns_none_when_no_unit():
    user = UserFactory()
    _make_tenant_profile(user)
    profile = Profile.objects.get(user=user)
    assert profile.primary_unit is None


def test_profile_save_mirrors_fk_into_residency():
    """Setting ``profile.unit = X`` creates a Residency(is_primary=True)
    automatically via Profile.save()."""
    user = UserFactory()
    _make_tenant_profile(user)
    unit = UnitFactory()
    profile = Profile.objects.get(user=user)

    profile.unit = unit
    profile.save()

    residencies = Residency.objects.filter(user=user)
    assert residencies.count() == 1
    residency = residencies.first()
    assert residency.unit_id == unit.pk
    assert residency.is_primary is True
    assert residency.role == ResidencyRole.OWNER


# ─── Announcements: building visibility via primary residency ─────────────────


def test_tenant_sees_announcements_for_primary_building_only():
    """Multi-unit tenant sees announcements for the building of their
    *primary* residency, not for their secondary-unit building."""
    from apps.posts.models import Announcement

    tenant = UserFactory()
    _make_tenant_profile(tenant)

    building_primary = BuildingFactory()
    building_secondary = BuildingFactory()
    unit_primary = UnitFactory(entrance=EntranceFactory(building=building_primary))
    unit_secondary = UnitFactory(entrance=EntranceFactory(building=building_secondary))

    ResidencyFactory(user=tenant, unit=unit_primary, is_primary=True)
    ResidencyFactory(user=tenant, unit=unit_secondary, is_primary=False)

    Announcement.objects.create(
        building=building_primary, title="For primary", body="x", is_active=True
    )
    Announcement.objects.create(
        building=building_secondary, title="For secondary", body="x", is_active=True
    )

    resp = _authed(tenant).get(reverse("list-announcements"))
    assert resp.status_code == 200
    data = resp.json()
    items = data.get("results", data) if isinstance(data, dict) else data
    titles = [a["title"] for a in items]
    assert "For primary" in titles
    assert "For secondary" not in titles


def test_promoting_secondary_flips_announcement_visibility():
    """Promoting a secondary residency to primary switches which
    building's announcements the tenant sees."""
    from apps.posts.models import Announcement

    tenant = UserFactory()
    _make_tenant_profile(tenant)

    building_a = BuildingFactory()
    building_b = BuildingFactory()
    unit_a = UnitFactory(entrance=EntranceFactory(building=building_a))
    unit_b = UnitFactory(entrance=EntranceFactory(building=building_b))

    Residency.objects.create(user=tenant, unit=unit_a, is_primary=True)
    secondary = Residency.objects.create(user=tenant, unit=unit_b, is_primary=False)

    Announcement.objects.create(
        building=building_a, title="A", body="x", is_active=True
    )
    Announcement.objects.create(
        building=building_b, title="B", body="x", is_active=True
    )

    client = _authed(tenant)

    def _titles(response):
        data = response.json()
        items = data.get("results", data) if isinstance(data, dict) else data
        return [a["title"] for a in items]

    resp = client.get(reverse("list-announcements"))
    assert _titles(resp) == ["A"]

    # Promote B to primary — A is auto-demoted by Residency.save().
    secondary.is_primary = True
    secondary.save()

    resp = client.get(reverse("list-announcements"))
    assert _titles(resp) == ["B"]


# ─── Issues: multi-unit tenant may open issues for any held unit ──────────────


def test_tenant_can_open_issue_for_any_held_unit():
    """A multi-unit owner opens an issue via the explicit unit_id path
    — the view checks Residency, not just Profile.unit."""
    from apps.issues.models import Category

    tenant = UserFactory()
    _make_tenant_profile(tenant)

    unit_primary = UnitFactory()
    unit_secondary = UnitFactory()

    ResidencyFactory(user=tenant, unit=unit_primary, is_primary=True)
    ResidencyFactory(user=tenant, unit=unit_secondary, is_primary=False)

    category = Category.objects.create(name="Plumbing", sla_hours=72)

    client = _authed(tenant)
    resp = client.post(
        reverse("create-issue-by-unit", kwargs={"unit_id": str(unit_secondary.id)}),
        {"title": "Leaking tap", "description": "In kitchen", "category": category.pk},
        format="json",
    )
    assert resp.status_code == 201, resp.content


def test_tenant_cannot_open_issue_for_stranger_unit():
    """A tenant with two residencies still cannot open an issue for a
    third, unrelated unit."""
    from apps.issues.models import Category

    tenant = UserFactory()
    _make_tenant_profile(tenant)
    ResidencyFactory(user=tenant, unit=UnitFactory(), is_primary=True)

    stranger_unit = UnitFactory()
    category = Category.objects.create(name="Plumbing", sla_hours=72)

    client = _authed(tenant)
    resp = client.post(
        reverse("create-issue-by-unit", kwargs={"unit_id": str(stranger_unit.id)}),
        {"title": "x", "description": "y", "category": category.pk},
        format="json",
    )
    assert resp.status_code == 403


def test_default_issue_path_uses_primary_residency():
    """The default (no unit_id) path derives the Unit from the
    reporter's primary residency."""
    from apps.issues.models import Category, Issue

    tenant = UserFactory()
    _make_tenant_profile(tenant)

    unit_primary = UnitFactory()
    unit_secondary = UnitFactory()
    ResidencyFactory(user=tenant, unit=unit_primary, is_primary=True)
    ResidencyFactory(user=tenant, unit=unit_secondary, is_primary=False)

    category = Category.objects.create(name="Plumbing", sla_hours=72)

    client = _authed(tenant)
    resp = client.post(
        reverse("create-issue-default"),
        {"title": "Broken", "description": "x", "category": category.pk},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    issue = Issue.objects.get(title="Broken")
    assert issue.unit_id == unit_primary.pk


# ─── Passes: create uses primary residency ────────────────────────────────────


def test_pass_creation_uses_primary_residency():
    import datetime as dt
    from apps.passes.models import VehiclePass

    tenant = UserFactory()
    _make_tenant_profile(tenant)

    unit_primary = UnitFactory()
    unit_secondary = UnitFactory()
    ResidencyFactory(user=tenant, unit=unit_primary, is_primary=True)
    ResidencyFactory(user=tenant, unit=unit_secondary, is_primary=False)

    client = _authed(tenant)
    resp = client.post(
        reverse("vehicle-pass-list-create"),
        {
            "car_number": "AA1234BB",
            "comment": "Taxi",
            "visit_date": (dt.date.today() + dt.timedelta(days=1)).isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    veh_pass = VehiclePass.objects.get(car_number="AA1234BB")
    assert veh_pass.unit_id == unit_primary.pk


# ─── ProfileSerializer payload ────────────────────────────────────────────────


def test_profile_serializer_renders_primary_unit():
    tenant = UserFactory()
    _make_tenant_profile(tenant)

    unit_primary = UnitFactory()
    unit_secondary = UnitFactory()
    ResidencyFactory(user=tenant, unit=unit_primary, is_primary=True)
    ResidencyFactory(user=tenant, unit=unit_secondary, is_primary=False)

    client = _authed(tenant)
    resp = client.get(reverse("retrieve-my-profile"))
    assert resp.status_code == 200, resp.content
    body = resp.json()
    # Generic renderer wraps under a label — unwrap defensively.
    payload = body.get("profile", body)
    assert str(payload["unit_id"]) == str(unit_primary.id)
    assert payload["unit_number"] == unit_primary.number


def test_profile_serializer_falls_back_when_only_fk():
    """A profile with only ``unit`` (no Residency row) still produces
    the expected payload — compatibility during the migration
    window."""
    tenant = UserFactory()
    _make_tenant_profile(tenant)

    unit = UnitFactory()
    profile = Profile.objects.get(user=tenant)
    profile._skip_residency_mirror = True
    profile.unit = unit
    profile.save()

    assert Residency.objects.filter(user=tenant).count() == 0

    client = _authed(tenant)
    resp = client.get(reverse("retrieve-my-profile"))
    assert resp.status_code == 200
    body = resp.json()
    payload = body.get("profile", body)
    assert str(payload["unit_id"]) == str(unit.id)
    assert payload["unit_number"] == unit.number
