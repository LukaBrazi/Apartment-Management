"""
Invariants that the Apartment → Building/Entrance/Unit linkage model relies on.

Historical note: earlier versions of this file claimed to test a data migration
but only re-implemented `get_or_create` inline — so they were testing the ORM,
not the migration. The actual apartments migrations (0001, 0002, 0003) are
schema-only — no `RunPython` — so there is no migration logic to test.

What these tests cover instead (and what `seed_demo` and production code rely on):
- Apartment ↔ Unit is a OneToOne and the reverse accessor `apartment.unit` works.
- Linking the same unit.apartment twice is idempotent (no extra rows).
- Building(name) is effectively a natural key for `get_or_create` callers.
- Building → Entrance → Unit chain is traversable via reverse relations.

If any of these break, `seed_demo` and the tenant profile binding will silently
diverge from what the client expects.
"""
import pytest

from apps.apartments.models import Apartment, Building, Entrance, Unit
from apps.tests.factories import ApartmentFactory


@pytest.mark.django_db
def test_apartment_unit_onetoone_reverse_accessor_works():
    """Apartment.unit reverse accessor must resolve after Unit.apartment = apt."""
    apt = ApartmentFactory(unit_number="101", building="Block A", floor=1)
    building = Building.objects.create(name="Block A", address="Block A", city="")
    entrance = Entrance.objects.create(building=building, name="1")
    unit = Unit.objects.create(
        entrance=entrance, number=apt.unit_number, floor=apt.floor, apartment=apt
    )

    apt.refresh_from_db()
    assert apt.unit == unit, "Apartment.unit reverse accessor did not resolve"
    assert unit.apartment == apt


@pytest.mark.django_db
def test_unit_apartment_link_is_idempotent():
    """
    Re-assigning the same Apartment to a Unit does not duplicate anything.
    `seed_demo`'s `_link_unit_apartment` relies on this being a no-op.
    """
    apt = ApartmentFactory(unit_number="202", building="Block B", floor=2)
    building = Building.objects.create(name="Block B", address="Block B", city="")
    entrance = Entrance.objects.create(building=building, name="1")
    unit = Unit.objects.create(entrance=entrance, number="202", floor=2, apartment=apt)

    # Re-assign the same apartment; must NOT create a second Unit row.
    unit.apartment = apt
    unit.save(update_fields=["apartment"])

    assert Unit.objects.filter(entrance=entrance).count() == 1
    assert Apartment.objects.filter(unit_number="202").count() == 1


@pytest.mark.django_db
def test_building_name_is_natural_key_for_get_or_create():
    """
    `Building.objects.get_or_create(name=...)` must return the SAME row on
    repeat calls — `seed_demo` runs twice in CI and must not duplicate buildings.
    """
    b1, created1 = Building.objects.get_or_create(
        name="Shared Block", defaults={"address": "A", "city": "Kyiv"}
    )
    b2, created2 = Building.objects.get_or_create(
        name="Shared Block", defaults={"address": "IGNORED", "city": "IGNORED"}
    )
    assert created1 is True
    assert created2 is False, "Second get_or_create must return existing row, not create"
    assert b1.pk == b2.pk
    assert Building.objects.filter(name="Shared Block").count() == 1
    # `defaults` must NOT overwrite existing columns
    b1.refresh_from_db()
    assert b1.address == "A"
    assert b1.city == "Kyiv"


@pytest.mark.django_db
def test_building_entrance_unit_reverse_relations():
    """Reverse accessors building.entrances → entrance.units must work end-to-end."""
    building = Building.objects.create(name="Chain Block", address="X", city="Kyiv")
    entrance = Entrance.objects.create(building=building, name="1")
    u1 = Unit.objects.create(entrance=entrance, number="1", floor=1)
    u2 = Unit.objects.create(entrance=entrance, number="2", floor=1)

    assert list(building.entrances.all()) == [entrance]
    # Unit.related_name defaults to 'units' — assert via entrance-side reverse.
    unit_numbers = sorted(entrance.units.values_list("number", flat=True))
    assert unit_numbers == ["1", "2"]
    assert u1.entrance.building == building
    assert u2.entrance.building == building
