"""Tests for Building / Entrance / Unit models."""
import pytest

from apps.apartments.models import Building, Entrance, Unit
from apps.tests.factories import BuildingFactory, EntranceFactory, UnitFactory


@pytest.mark.django_db
def test_building_creation():
    b = BuildingFactory(name="Тестовий будинок", address="вул. Хрещатик 1", city="Kyiv")
    assert b.pk is not None
    assert str(b) == "Тестовий будинок — вул. Хрещатик 1"
    assert b.is_active


@pytest.mark.django_db
def test_entrance_links_to_building():
    b = BuildingFactory()
    e = EntranceFactory(building=b, name="1")
    assert e.building == b
    assert "Entrance 1" in str(e)


@pytest.mark.django_db
def test_unit_creation():
    u = UnitFactory(number="42", floor=4)
    assert u.pk is not None
    assert u.number == "42"
    assert u.floor == 4


@pytest.mark.django_db
def test_building_has_multiple_entrances():
    b = BuildingFactory()
    EntranceFactory(building=b, name="1")
    EntranceFactory(building=b, name="2")
    assert b.entrances.count() == 2


@pytest.mark.django_db
def test_entrance_has_multiple_units():
    e = EntranceFactory()
    UnitFactory(entrance=e, number="1")
    UnitFactory(entrance=e, number="2")
    assert e.units.count() == 2


@pytest.mark.django_db
def test_unit_unique_per_entrance():
    from django.db import IntegrityError
    e = EntranceFactory()
    UnitFactory(entrance=e, number="10")
    with pytest.raises(IntegrityError):
        UnitFactory(entrance=e, number="10")
