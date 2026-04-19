"""Tests for the PR-3 backend API cutover to Unit.

PR-3 swapped the backend read path from legacy ``Apartment`` to
``Unit`` while preserving the wire format used by the frontend.  After
PR-6 the ``/apartments/my-apartment/`` endpoint is gone, so those
tests were removed; the remaining checks still lock in two contracts
the surviving serializers depend on:

1. ``unit_as_legacy_apartment`` renders a Unit with **exactly** the
   keys ``ApartmentSerializer`` returns, so any caller still using the
   shim sees no diff.
2. ``ProfileSerializer.apartment`` prefers ``profile.unit`` but falls
   back to the legacy ``Apartment`` for unbridged rows — the field
   stays in the payload until PR-7 drops the Apartment model.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.apartments.models import Apartment, Building, Entrance, Unit
from apps.apartments.serializers import (
    ApartmentSerializer,
    unit_as_legacy_apartment,
)
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
def bridged(db):
    apt = Apartment.objects.create(unit_number="10", building="Block A", floor=2)
    building = Building.objects.create(name="Block A", address="A")
    entrance = Entrance.objects.create(building=building, name="1")
    unit = Unit.objects.create(
        entrance=entrance, number="10", floor=2, apartment=apt
    )
    return apt, unit, building


# ───────────────────────── unit shim ───────────────────────────────────────


class TestUnitAsLegacyApartment:
    """Shim must produce byte-compatible JSON with ApartmentSerializer."""

    # ApartmentSerializer outputs exactly these keys (tenant is HiddenField,
    # updated_at/pkid are excluded in Meta).  The shim must match exactly.
    EXPECTED_KEYS = {"id", "created_at", "unit_number", "building", "floor"}

    def test_keys_match_legacy_serializer(self, db, user, bridged):
        apt, unit, _ = bridged
        apt.tenant = user
        apt.save()

        shim_data = unit_as_legacy_apartment(unit)
        legacy_data = ApartmentSerializer(apt).data

        assert set(shim_data.keys()) == self.EXPECTED_KEYS
        assert set(legacy_data.keys()) == self.EXPECTED_KEYS, (
            "Sanity: ApartmentSerializer contract unchanged."
        )

    def test_values_match_when_bridge_exists(self, db, user, bridged):
        apt, unit, _ = bridged
        apt.tenant = user
        apt.save()

        shim_data = unit_as_legacy_apartment(unit)

        assert shim_data["id"] == str(apt.id), "uses legacy Apartment UUID"
        assert shim_data["unit_number"] == apt.unit_number
        assert shim_data["building"] == "Block A"
        assert shim_data["floor"] == apt.floor

    def test_falls_back_to_unit_id_when_no_legacy_apt(self, db, user):
        """Post-PR-7 state: Unit without a legacy Apartment behind it."""
        building = Building.objects.create(name="B", address="x")
        entrance = Entrance.objects.create(building=building, name="1")
        unit = Unit.objects.create(entrance=entrance, number="77", floor=7)

        shim_data = unit_as_legacy_apartment(unit)

        assert shim_data["id"] == str(unit.id)
        assert shim_data["unit_number"] == "77"
        assert shim_data["building"] == "B"


# ───────────────────────── Profile.apartment ───────────────────────────────


class TestProfileApartmentField:
    """ProfileSerializer.apartment must prefer profile.unit over legacy."""

    def test_prefers_profile_unit(self, db, user, bridged):
        apt, unit, _ = bridged
        apt.tenant = user
        apt.save()
        profile = Profile.objects.get(user=user)
        profile.unit = unit
        profile.save()

        data = ProfileSerializer(profile).data

        assert data["apartment"] is not None
        assert data["apartment"]["unit_number"] == unit.number
        assert data["apartment"]["building"] == "Block A"
        assert data["apartment"]["id"] == str(apt.id)

    def test_legacy_fallback_when_profile_unit_unset(self, db, user):
        """Pre-backfill state: no profile.unit, but legacy apartment exists."""
        apt = Apartment.objects.create(
            unit_number="fallback", building="Legacy", floor=1, tenant=user
        )
        profile = Profile.objects.get(user=user)
        assert profile.unit_id is None

        data = ProfileSerializer(profile).data

        assert data["apartment"] is not None
        assert data["apartment"]["unit_number"] == apt.unit_number
        assert data["apartment"]["building"] == "Legacy"

    def test_returns_none_when_nothing_linked(self, db, user):
        profile = Profile.objects.get(user=user)
        data = ProfileSerializer(profile).data
        assert data["apartment"] is None
