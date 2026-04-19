"""PR-9 schema tests: new informational fields on Organization / Building / Unit.

These fields are informational (no permission / scoping impact) — the
tests assert defaults, choice membership, clean() validation on area
fields, and that the new ``Organization.Type.SINGLE_BUILDING`` choice
round-trips through the DB.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.apartments.models import Building, BuildingType, Unit
from apps.organizations.models import Organization, OrganizationType
from apps.tests.factories import BuildingFactory, EntranceFactory, UnitFactory

pytestmark = pytest.mark.django_db


# ─── Building.type ────────────────────────────────────────────────────────────


def test_building_type_default_is_apartment_block():
    b = BuildingFactory()
    assert b.type == BuildingType.APARTMENT_BUILDING


def test_building_type_accepts_cottage():
    b = BuildingFactory(type=BuildingType.COTTAGE)
    b.refresh_from_db()
    assert b.type == BuildingType.COTTAGE


def test_building_type_choices_are_exactly_two():
    """Guard against accidental proliferation — if a new type is added
    the decision should be explicit.  Bump this test then."""
    assert set(BuildingType.values) == {"apartment_building", "cottage"}


# ─── Building.total_area ──────────────────────────────────────────────────────


def test_building_total_area_defaults_to_null():
    b = BuildingFactory()
    assert b.total_area is None


def test_building_total_area_accepts_decimal():
    b = BuildingFactory(total_area=Decimal("250.75"))
    b.refresh_from_db()
    assert b.total_area == Decimal("250.75")


def test_building_clean_rejects_negative_total_area():
    b = Building(name="x", address="y", total_area=Decimal("-1.00"))
    with pytest.raises(ValidationError) as exc:
        b.clean()
    assert "total_area" in exc.value.message_dict


# ─── Unit.area ────────────────────────────────────────────────────────────────


def test_unit_area_defaults_to_null():
    u = UnitFactory()
    assert u.area is None


def test_unit_area_accepts_decimal():
    u = UnitFactory(area=Decimal("58.40"))
    u.refresh_from_db()
    assert u.area == Decimal("58.40")


def test_unit_clean_rejects_negative_area():
    u = Unit(
        entrance=EntranceFactory(),
        number="X",
        area=Decimal("-5.00"),
    )
    with pytest.raises(ValidationError) as exc:
        u.clean()
    assert "area" in exc.value.message_dict


# ─── Unit uniqueness invariant (regression guard) ─────────────────────────────


def test_same_number_different_entrance_allowed():
    """The user's spec: 'номер може бути однаковий для двох різних
    під'їздів, але не може бути два однакових у одному під'їзді'."""
    b = BuildingFactory()
    ent_a = EntranceFactory(building=b, name="A")
    ent_b = EntranceFactory(building=b, name="B")
    UnitFactory(entrance=ent_a, number="1")
    UnitFactory(entrance=ent_b, number="1")  # same number, different entrance
    assert Unit.objects.filter(number="1").count() == 2


def test_duplicate_number_same_entrance_rejected():
    ent = EntranceFactory()
    UnitFactory(entrance=ent, number="1")
    with pytest.raises(Exception):  # IntegrityError under the hood
        UnitFactory(entrance=ent, number="1")


# ─── Organization.Type.SINGLE_BUILDING ────────────────────────────────────────


def test_organization_single_building_choice_available():
    assert "single_building" in OrganizationType.values


def test_organization_accepts_single_building_type():
    org = Organization.objects.create(
        name="One House Inc.",
        slug="one-house-inc",
        type=OrganizationType.SINGLE_BUILDING,
    )
    org.refresh_from_db()
    assert org.type == OrganizationType.SINGLE_BUILDING


def test_organization_type_choices_include_all_four():
    assert set(OrganizationType.values) == {
        "housing_complex",
        "cottage_village",
        "single_building",
        "management_company",
    }
