"""Tests for the PR-3 → PR-7 backend API cutover to Unit.

After PR-7 the legacy ``Apartment`` model and the
``unit_as_legacy_apartment`` shim are gone, so ``TestUnitAsLegacyApartment``
was dropped.  What's still worth locking in is the wire format of
``ProfileSerializer.apartment``: the frontend has not yet removed the
``profile.apartment`` field from its Profile type (the unit_*/building_*
aliases from PR-4 are preferred), so the payload contract must keep the
Unit-shaped dict stable.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.apartments.models import Building, Entrance, Unit
from apps.profiles.models import Profile
from apps.profiles.serializers import ProfileSerializer

User = get_user_model()


# ───────────────────────── fixtures ────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="u@example.com",
        username="u",
        first_name="U",
        last_name="X",
        password="x",  # noqa: S106
    )


@pytest.fixture
def unit(db):
    building = Building.objects.create(name="Block A", address="A")
    entrance = Entrance.objects.create(building=building, name="1")
    return Unit.objects.create(entrance=entrance, number="10", floor=2)


# ───────────────────────── Profile.apartment ───────────────────────────────


class TestProfileApartmentField:
    """ProfileSerializer.apartment must render profile.unit in the
    Apartment-shaped JSON the frontend still consumes."""

    EXPECTED_KEYS = {"id", "created_at", "unit_number", "building", "floor"}

    def test_renders_unit_in_apartment_shape(self, db, user, unit):
        profile = Profile.objects.get(user=user)
        profile.unit = unit
        profile.save()

        data = ProfileSerializer(profile).data

        assert data["apartment"] is not None
        assert set(data["apartment"].keys()) == self.EXPECTED_KEYS
        assert data["apartment"]["id"] == str(unit.id)
        assert data["apartment"]["unit_number"] == unit.number
        assert data["apartment"]["building"] == "Block A"
        assert data["apartment"]["floor"] == unit.floor

    def test_returns_none_when_no_unit(self, db, user):
        profile = Profile.objects.get(user=user)
        assert profile.unit_id is None

        data = ProfileSerializer(profile).data

        assert data["apartment"] is None
