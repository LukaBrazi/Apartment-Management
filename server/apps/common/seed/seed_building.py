"""Seed the demo Building, its Entrances and Units.

Per plan §3:

* 1 ``Building(name=DEMO_BUILDING_NAME)`` in a dedicated ``ResidentialComplex``.
* 3 Entrances named "А", "Б", "В" — last one intentionally empty (showcase
  for the data model; some real buildings do have unused entrance shells).
* 4 × 6 = 24 Units in А, same in Б (48 units total).
* Every seeded Unit also gets a mirroring legacy ``Apartment`` row and the
  two are stitched via the ``Unit.apartment`` OneToOne — kept for
  backwards compatibility with the older API surface that still queries
  ``Apartment`` directly.

Idempotency: built on ``get_or_create`` with natural keys
(``Building.name``; ``Entrance (building, name)``; ``Unit (entrance, number)``;
``Apartment (building, unit_number)``).  Rerunning without ``--reset`` is a
no-op.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.db import transaction

from .helpers import (
    DEMO_BUILDING_NAME,
    FLOORS_PER_ENTRANCE,
    POPULATED_ENTRANCES,
    ENTRANCE_NAMES,
    UNITS_PER_FLOOR,
    unit_number_for,
)

if TYPE_CHECKING:  # pragma: no cover
    from apps.apartments.models import (
        Apartment,
        Building,
        Entrance,
        ResidentialComplex,
        Unit,
    )

logger = logging.getLogger(__name__)

# Fixed textual metadata — plan §3.1.
DEMO_COMPLEX_NAME = "ЖК Зелений Квартал"
DEMO_BUILDING_ADDRESS = "вул. Академіка Заболотного, 15"
DEMO_BUILDING_CITY = "Київ"


@dataclass
class BuildingSeedResult:
    """Handles + counts returned to the orchestrator."""

    complex: "ResidentialComplex" = field(repr=False)
    building: "Building" = field(repr=False)
    entrances: dict[str, "Entrance"] = field(default_factory=dict, repr=False)
    units_by_key: dict[tuple[str, str], "Unit"] = field(
        default_factory=dict, repr=False,
    )
    created_units: int = 0
    created_apartments: int = 0


@transaction.atomic
def seed() -> BuildingSeedResult:
    """Create (or update) the demo Building hierarchy.

    Returns
    -------
    BuildingSeedResult
        Fully-loaded handles — the orchestrator threads these into
        ``seed_users``, ``seed_issues``, etc. so later modules don't have to
        re-query the DB for the demo Building.
    """
    # Deferred imports — see note in reset_scope.py.
    from apps.apartments.models import (
        Apartment,
        Building,
        Entrance,
        ResidentialComplex,
        Unit,
    )

    complex_obj, _ = ResidentialComplex.objects.get_or_create(
        name=DEMO_COMPLEX_NAME,
        defaults={
            "address": DEMO_BUILDING_ADDRESS,
            "city": DEMO_BUILDING_CITY,
            "description": (
                "Демо-ЖК ApartmentOS — набір синтетичних даних для демонстрації "
                "функціоналу клієнтам. Скидається щодня о 23:00 Europe/Kyiv."
            ),
        },
    )

    building, _ = Building.objects.get_or_create(
        name=DEMO_BUILDING_NAME,
        defaults={
            "address": DEMO_BUILDING_ADDRESS,
            "city": DEMO_BUILDING_CITY,
            "is_active": True,
            "complex": complex_obj,
        },
    )
    # Defensive update: if the building existed but was detached or renamed,
    # re-attach to our complex.  Guard so we don't write on a no-op.
    if building.complex_id != complex_obj.pk or not building.is_active:
        building.complex = complex_obj
        building.is_active = True
        building.save(update_fields=["complex", "is_active"])

    result = BuildingSeedResult(complex=complex_obj, building=building)

    # Entrances ────────────────────────────────────────────────────────────────
    for name in ENTRANCE_NAMES:
        entrance, _ = Entrance.objects.get_or_create(
            building=building,
            name=name,
        )
        result.entrances[name] = entrance

    # Units + mirrored Apartment rows ─────────────────────────────────────────
    for entrance_name in POPULATED_ENTRANCES:
        entrance = result.entrances[entrance_name]
        for floor in range(1, FLOORS_PER_ENTRANCE + 1):
            for slot in range(1, UNITS_PER_FLOOR + 1):
                number = unit_number_for(floor, slot)
                unit, unit_created = Unit.objects.get_or_create(
                    entrance=entrance,
                    number=number,
                    defaults={"floor": floor},
                )
                if unit_created:
                    result.created_units += 1

                # Legacy Apartment has unique_together (building, unit_number)
                # and no Entrance concept — so we prefix the number with the
                # entrance letter to keep А-101 and Б-101 distinct legacy rows.
                legacy_number = f"{entrance_name}{number}"
                apt, apt_created = Apartment.objects.get_or_create(
                    unit_number=legacy_number,
                    building=building.name,
                    defaults={"floor": floor},
                )
                if apt_created:
                    result.created_apartments += 1

                _link_unit_apartment(unit, apt)
                result.units_by_key[(entrance_name, number)] = unit

    logger.info(
        "seed_building: complex=%s building=%s entrances=%d "
        "units_created=%d apartments_created=%d",
        complex_obj.name, building.name, len(result.entrances),
        result.created_units, result.created_apartments,
    )
    return result


# ───────────────────────────── internal helpers ──────────────────────────────


def _link_unit_apartment(unit: "Unit", apartment: "Apartment") -> None:
    """Attach ``apartment`` to ``unit`` if the OneToOne slot is free.

    OneToOne is SET_NULL on delete, so a previous reset may leave orphan
    apartments.  We also defensively check the current link — if the Unit is
    already pointing at the right Apartment, we skip the UPDATE entirely
    (keeps idempotent-rerun SQL output tidy).
    """
    unit.refresh_from_db(fields=["apartment"])
    if unit.apartment_id == apartment.pk:
        return
    if unit.apartment_id is not None:
        # Another apartment already claims this unit; don't clobber.
        return
    unit.apartment = apartment
    unit.save(update_fields=["apartment"])
