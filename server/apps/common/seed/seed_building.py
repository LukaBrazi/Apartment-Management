"""Seed the demo Building, its Entrances and Units.

Per plan §3:

* 1 ``Building(name=DEMO_BUILDING_NAME)`` in a dedicated ``ResidentialComplex``.
* 3 Entrances named "А", "Б", "В" — last one intentionally empty (showcase
  for the data model; some real buildings do have unused entrance shells).
* 4 × 6 = 24 Units in А, same in Б (48 units total).

Historical note (PR-5 of the legacy-Apartment removal):
Prior to PR-5 the seed mirrored every Unit into a legacy ``Apartment`` row
and stitched them via ``Unit.apartment``.  After PR-3 the backend reads
Unit directly, so the mirror is dead weight — we stopped producing it
here so PR-7 can drop the model without a cleanup dance.  Residual
Apartment rows left over from pre-PR-5 runs are swept by
``reset_scope.reset_demo_scope`` on the next ``--reset``.

Idempotency: built on ``get_or_create`` with natural keys
(``Building.name``; ``Entrance (building, name)``; ``Unit (entrance, number)``).
Rerunning without ``--reset`` is a no-op.
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

    # Units ───────────────────────────────────────────────────────────────────
    # PR-5: legacy Apartment mirroring was removed.  Unit is the single
    # source of truth post PR-3; any residual ``Unit.apartment`` FKs
    # pointing at pre-PR-5 Apartment rows stay SET_NULL after the next
    # reset sweeps those rows.
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
                result.units_by_key[(entrance_name, number)] = unit

    logger.info(
        "seed_building: complex=%s building=%s entrances=%d "
        "units_created=%d",
        complex_obj.name, building.name, len(result.entrances),
        result.created_units,
    )
    return result
