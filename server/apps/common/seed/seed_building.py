"""Seed the demo Buildings, their Entrances and Units.

Per plan §3 (PR-13):

* 1 primary ``Building`` (``DEMO_BUILDING_NAME``) of
  ``type=APARTMENT_BUILDING`` with three entrances — "А", "Б", "В" —
  the last one intentionally empty (showcase of the data model; some
  real buildings do have unused entrance shells).  4 × 6 = 24 Units
  in А, same in Б (48 units total). Every Unit carries a realistic
  ``area`` in square metres.
* 1 secondary ``Building`` (``DEMO_BUILDING_COTTAGE_NAME``) of
  ``type=COTTAGE`` — single entrance "Котедж", single Unit "1". This
  shows customers that the same schema supports a cottage village
  tenant without bending the model.
* Every Building is linked to the demo ``Organization`` so the
  tenant-scoping that production customers see is exercised by the
  demo UI end-to-end.

Historical notes:
* **PR-5** stopped mirroring every Unit into a legacy ``Apartment`` row;
  Unit is the single source of truth post PR-3.
* **PR-7** deleted the ``Apartment`` model entirely.
* **PR-8** deleted the ``ResidentialComplex`` (ЖК) model — buildings are
  scoped to ``Organization`` exclusively now.
* **PR-12** added ``Building.is_demo`` — defense-in-depth for the reset
  filter.
* **PR-13** adds Unit.area, Building.total_area, and the cottage +
  Organization link so the demo represents the concept 1:1.

Idempotency: built on ``get_or_create`` with natural keys
(``Building.name``; ``Entrance (building, name)``; ``Unit (entrance, number)``).
Rerunning without ``--reset`` is a no-op except for re-asserting the
defensive fields (``is_demo``, ``is_active``, ``organization``).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction

from .helpers import (
    DEMO_BUILDING_COTTAGE_NAME,
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
    from .seed_organization import OrganizationSeedResult

logger = logging.getLogger(__name__)

# Fixed textual metadata — plan §3.1.
DEMO_BUILDING_ADDRESS = "вул. Академіка Заболотного, 15"
DEMO_BUILDING_CITY = "Київ"

# Cottage metadata — a separate address one street away keeps the
# demo story believable ("ЖК має показовий котедж поряд") without
# needing a whole second map marker in the UI.
DEMO_COTTAGE_ADDRESS = "вул. Академіка Заболотного, 17"
DEMO_COTTAGE_CITY = DEMO_BUILDING_CITY
DEMO_COTTAGE_ENTRANCE_NAME = "Котедж"
DEMO_COTTAGE_UNIT_NUMBER = "1"
# A plausible two-storey 180 m² town cottage. Used for both
# ``Building.total_area`` and ``Unit.area`` — cottages genuinely carry
# a single-unit footprint equal to the building footprint, so we reuse
# the number instead of splitting it artificially.
DEMO_COTTAGE_AREA_M2 = Decimal("180.00")
# Apartment block total — derived from the per-unit areas below so the
# number reads as "arithmetically consistent" during the demo tour.
# 48 units × ~80 m² average ≈ 3840 m², plus ~12% common space = 4300.
DEMO_APARTMENT_TOTAL_AREA_M2 = Decimal("4300.00")


def _unit_area_for(floor: int, slot: int) -> Decimal:
    """Return a realistic m² area for a given ``(floor, slot)``.

    The demo wants units that *look* like real Kyiv apartments rather
    than uniform boxes. We pick deterministic, human-looking numbers
    with a light floor-based upgrade (penthouse slot on top floor) so
    filters and stats in the UI have something non-trivial to chew on.

    Layout (60–110 m² range):

    * slot 1 — corner studio    : 55 m²
    * slot 2 — 1-bed            : 68 m²
    * slot 3 — 2-bed small      : 74 m²
    * slot 4 — 2-bed large      : 82 m²
    * slot 5 — 3-bed            : 96 m²
    * slot 6 — 3-bed corner     : 108 m²

    Top-floor units get +6 m² to mimic attic / penthouse premium.
    """
    base_by_slot = {
        1: Decimal("55.00"),
        2: Decimal("68.00"),
        3: Decimal("74.00"),
        4: Decimal("82.00"),
        5: Decimal("96.00"),
        6: Decimal("108.00"),
    }
    area = base_by_slot[slot]
    if floor == FLOORS_PER_ENTRANCE:
        area += Decimal("6.00")  # top-floor bump
    return area


@dataclass
class BuildingSeedResult:
    """Handles + counts returned to the orchestrator.

    The primary ``building`` (apartment block) and its ``units_by_key``
    stay at the top of the dataclass because every downstream seed
    module (seed_users, seed_issues, seed_posts) still only cares about
    the apartment block. The cottage is optional and exposed on
    separate attributes so callers can opt-in without restructuring.
    """

    building: "Building" = field(repr=False)
    entrances: dict[str, "Entrance"] = field(default_factory=dict, repr=False)
    units_by_key: dict[tuple[str, str], "Unit"] = field(
        default_factory=dict, repr=False,
    )
    created_units: int = 0
    # PR-13 additions — cottage showcase. These are populated on every
    # run; callers that don't care (most seed modules) can ignore them.
    cottage_building: "Building | None" = field(default=None, repr=False)
    cottage_unit: "Unit | None" = field(default=None, repr=False)


@transaction.atomic
def seed(*, organization_result: "OrganizationSeedResult | None" = None) -> BuildingSeedResult:
    """Create (or update) the demo Building hierarchy.

    Parameters
    ----------
    organization_result:
        Output of ``seed_organization.seed()``. When present, every
        Building is linked to the demo Organization. Kept optional so
        unit tests that exercise ``seed_building`` in isolation don't
        need to stand up an Organization fixture.

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
        BuildingType,
        Entrance,
        Unit,
    )

    organization = (
        organization_result.organization if organization_result else None
    )

    building, _ = Building.objects.get_or_create(
        name=DEMO_BUILDING_NAME,
        defaults={
            "address": DEMO_BUILDING_ADDRESS,
            "city": DEMO_BUILDING_CITY,
            "is_active": True,
            # PR-12 safety: every seed-created building MUST carry the
            # demo marker so the reset filter can match it.
            "is_demo": True,
            # PR-13 concept alignment: the primary demo building is an
            # apartment block and carries a plausible total footprint.
            "type": BuildingType.APARTMENT_BUILDING,
            "total_area": DEMO_APARTMENT_TOTAL_AREA_M2,
            "organization": organization,
        },
    )
    # Defensive update: if the building existed but was deactivated or
    # moved, re-assert the demo metadata.  Also re-assert ``is_demo`` on
    # rerun — if a hand-edit ever toggled it off the reset would skip
    # this row indefinitely. PR-13 also re-asserts the typed-building
    # fields so existing demo rows pick up the concept alignment.
    dirty: list[str] = []
    if not building.is_active:
        building.is_active = True
        dirty.append("is_active")
    if not building.is_demo:
        building.is_demo = True
        dirty.append("is_demo")
    if building.type != BuildingType.APARTMENT_BUILDING:
        building.type = BuildingType.APARTMENT_BUILDING
        dirty.append("type")
    if building.total_area != DEMO_APARTMENT_TOTAL_AREA_M2:
        building.total_area = DEMO_APARTMENT_TOTAL_AREA_M2
        dirty.append("total_area")
    if organization is not None and building.organization_id != organization.pk:
        building.organization = organization
        dirty.append("organization")
    if dirty:
        building.save(update_fields=dirty)

    result = BuildingSeedResult(building=building)

    # Entrances ────────────────────────────────────────────────────────────────
    for name in ENTRANCE_NAMES:
        entrance, _ = Entrance.objects.get_or_create(
            building=building,
            name=name,
        )
        # Entrance.save() auto-propagates building.organization, but an
        # entrance created BEFORE the building had an organization
        # (historical rows) would still carry NULL. Re-assert defensively.
        if organization is not None and entrance.organization_id != organization.pk:
            entrance.organization = organization
            entrance.save(update_fields=["organization"])
        result.entrances[name] = entrance

    # Units ───────────────────────────────────────────────────────────────────
    for entrance_name in POPULATED_ENTRANCES:
        entrance = result.entrances[entrance_name]
        for floor in range(1, FLOORS_PER_ENTRANCE + 1):
            for slot in range(1, UNITS_PER_FLOOR + 1):
                number = unit_number_for(floor, slot)
                area = _unit_area_for(floor, slot)
                unit, unit_created = Unit.objects.get_or_create(
                    entrance=entrance,
                    number=number,
                    defaults={"floor": floor, "area": area},
                )
                if unit_created:
                    result.created_units += 1
                # PR-13: backfill area onto pre-existing units so the
                # demo statistics page shows square-metre data even on
                # DBs that were seeded before this PR landed.
                unit_dirty: list[str] = []
                if unit.area != area:
                    unit.area = area
                    unit_dirty.append("area")
                if unit.floor != floor:
                    unit.floor = floor
                    unit_dirty.append("floor")
                if unit_dirty:
                    unit.save(update_fields=unit_dirty)
                result.units_by_key[(entrance_name, number)] = unit

    # Cottage (PR-13) ─────────────────────────────────────────────────────────
    cottage_building, _ = Building.objects.get_or_create(
        name=DEMO_BUILDING_COTTAGE_NAME,
        defaults={
            "address": DEMO_COTTAGE_ADDRESS,
            "city": DEMO_COTTAGE_CITY,
            "is_active": True,
            "is_demo": True,
            "type": BuildingType.COTTAGE,
            "total_area": DEMO_COTTAGE_AREA_M2,
            "organization": organization,
        },
    )
    # Re-assert defensive fields on rerun.
    cottage_dirty: list[str] = []
    if not cottage_building.is_active:
        cottage_building.is_active = True
        cottage_dirty.append("is_active")
    if not cottage_building.is_demo:
        cottage_building.is_demo = True
        cottage_dirty.append("is_demo")
    if cottage_building.type != BuildingType.COTTAGE:
        cottage_building.type = BuildingType.COTTAGE
        cottage_dirty.append("type")
    if cottage_building.total_area != DEMO_COTTAGE_AREA_M2:
        cottage_building.total_area = DEMO_COTTAGE_AREA_M2
        cottage_dirty.append("total_area")
    if (
        organization is not None
        and cottage_building.organization_id != organization.pk
    ):
        cottage_building.organization = organization
        cottage_dirty.append("organization")
    if cottage_dirty:
        cottage_building.save(update_fields=cottage_dirty)

    cottage_entrance, _ = Entrance.objects.get_or_create(
        building=cottage_building,
        name=DEMO_COTTAGE_ENTRANCE_NAME,
    )
    if (
        organization is not None
        and cottage_entrance.organization_id != organization.pk
    ):
        cottage_entrance.organization = organization
        cottage_entrance.save(update_fields=["organization"])

    cottage_unit, cottage_unit_created = Unit.objects.get_or_create(
        entrance=cottage_entrance,
        number=DEMO_COTTAGE_UNIT_NUMBER,
        defaults={"floor": 1, "area": DEMO_COTTAGE_AREA_M2},
    )
    if cottage_unit_created:
        result.created_units += 1
    unit_dirty: list[str] = []
    if cottage_unit.area != DEMO_COTTAGE_AREA_M2:
        cottage_unit.area = DEMO_COTTAGE_AREA_M2
        unit_dirty.append("area")
    if cottage_unit.floor != 1:
        cottage_unit.floor = 1
        unit_dirty.append("floor")
    if unit_dirty:
        cottage_unit.save(update_fields=unit_dirty)

    result.cottage_building = cottage_building
    result.cottage_unit = cottage_unit

    logger.info(
        "seed_building: apartment=%s entrances=%d units_created=%d "
        "cottage=%s total_buildings=%d",
        building.name, len(result.entrances), result.created_units,
        cottage_building.name, 2,
    )
    return result
