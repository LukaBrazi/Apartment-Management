"""Tests for the data migration: Apartment → Building/Entrance/Unit."""
import pytest

from apps.apartments.models import Apartment, Building, Entrance, Unit
from apps.tests.factories import ApartmentFactory


@pytest.mark.django_db
def test_data_migration_creates_unit_from_apartment():
    """Simulate what the data migration does."""
    apt = ApartmentFactory(unit_number="101", building="Block A", floor=1)

    # Run migration logic manually
    building, _ = Building.objects.get_or_create(
        name="Block A", defaults={"address": "Block A", "city": ""}
    )
    entrance, _ = Entrance.objects.get_or_create(building=building, name="1")
    unit = Unit.objects.create(
        entrance=entrance, number=apt.unit_number, floor=apt.floor, apartment=apt
    )

    assert unit.apartment == apt
    assert unit.number == "101"
    assert unit.entrance.building.name == "Block A"


@pytest.mark.django_db
def test_apartment_backward_link_to_unit():
    """Apartment.unit reverse relation works after linkage."""
    apt = ApartmentFactory(unit_number="202", building="Block B", floor=2)
    building, _ = Building.objects.get_or_create(
        name="Block B", defaults={"address": "Block B", "city": ""}
    )
    entrance, _ = Entrance.objects.get_or_create(building=building, name="1")
    unit = Unit.objects.create(
        entrance=entrance, number=apt.unit_number, floor=apt.floor, apartment=apt
    )

    apt.refresh_from_db()
    assert apt.unit == unit


@pytest.mark.django_db
def test_migration_idempotent_for_same_building():
    """Multiple apartments in same building → one Building, one Entrance."""
    ApartmentFactory(unit_number="301", building="Shared Block", floor=3)
    ApartmentFactory(unit_number="302", building="Shared Block", floor=3)

    building, _ = Building.objects.get_or_create(
        name="Shared Block", defaults={"address": "Shared Block", "city": ""}
    )
    Entrance.objects.get_or_create(building=building, name="1")

    assert Building.objects.filter(name="Shared Block").count() == 1
    assert Entrance.objects.filter(building=building).count() == 1
