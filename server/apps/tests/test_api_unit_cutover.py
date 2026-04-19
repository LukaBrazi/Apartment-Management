"""Wire-format lock for ``ProfileSerializer.apartment``.

The frontend still consumes ``profile.apartment`` as the legacy
Apartment-shaped dict (the ``unit_*`` / ``building_*`` aliases from
PR-4 are preferred, but older components remain).  This suite pins the
JSON contract.

Post-PR-11: the tenant's Unit comes from the canonical ``Residency``
row; ``Profile.unit`` has been dropped.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.apartments.models import Building, Entrance, Residency, ResidencyRole, Unit
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
    """ProfileSerializer.apartment must render the user's primary
    Residency's Unit in the Apartment-shaped JSON the frontend still
    consumes."""

    EXPECTED_KEYS = {"id", "created_at", "unit_number", "building", "floor"}

    def test_renders_unit_in_apartment_shape(self, db, user, unit):
        Residency.objects.create(
            user=user, unit=unit, is_primary=True, role=ResidencyRole.OWNER
        )
        profile = Profile.objects.get(user=user)

        data = ProfileSerializer(profile).data

        assert data["apartment"] is not None
        assert set(data["apartment"].keys()) == self.EXPECTED_KEYS
        assert data["apartment"]["id"] == str(unit.id)
        assert data["apartment"]["unit_number"] == unit.number
        assert data["apartment"]["building"] == "Block A"
        assert data["apartment"]["floor"] == unit.floor

    def test_returns_none_when_no_unit(self, db, user):
        profile = Profile.objects.get(user=user)
        assert profile.primary_unit is None

        data = ProfileSerializer(profile).data

        assert data["apartment"] is None
