"""Seed the demo Building, its Entrances and Units.

Per plan §3:

* 1 ``Building(name=DEMO_BUILDING_NAME)``.
* 3 Entrances named "А", "Б", "В" — last one intentionally empty (showcase
  for the data model; some real buildings do have unused entrance shells).
* 4 × 6 = 24 Units in А, same in Б (48 units total).

Historical notes:
* **PR-5** stopped mirroring every Unit into a legacy ``Apartment`` row;
  Unit is the single source of truth post PR-3.
* **PR-7** deleted the ``Apartment`` model entirely.
* **PR-8** deleted the ``ResidentialComplex`` (ЖК) model — buildings are
  scoped to ``Organization`` exclusively now.  The seed no longer creates
  a complex; ЖК display copy lives on ``SiteSettings.complex_name``.

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
        Unit,
    )

logger = logging.getLogger(__name__)

# Fixed textual metadata — plan §3.1.
DEMO_BUILDING_ADDRESS = "вул. Академіка Заболотного, 15"
DEMO_BUILDING_CITY = "Київ"


@dataclass
class BuildingSeedResult:
    """Handles + counts returned to the orchestrator."""

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
        Unit,
    )

    building, _ = Building.objects.get_or_create(
        name=DEMO_BUILDING_NAME,
        defaults={
            "address": DEMO_BUILDING_ADDRESS,
            "city": DEMO_BUILDING_CITY,
            "is_active": True,
        },
    )
    # Defensive update: if the building existed but was deactivated or
    # moved, re-assert the demo metadata.  Guard so we don't write on a
    # no-op.
    if not building.is_active:
        building.is_active = True
        building.save(update_fields=["is_active"])

    result = BuildingSeedResult(building=building)

    # Entrances ────────────────────────────────────────────────────────────────
    for name in ENTRANCE_NAMES:
        entrance, _ = Entrance.objects.get_or_create(
            building=building,
            name=name,
        )
        result.entrances[name] = entrance

    # Units ───────────────────────────────────────────────────────────────────
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
        "seed_building: building=%s entrances=%d units_created=%d",
        building.name, len(result.entrances), result.created_units,
    )
    return result
