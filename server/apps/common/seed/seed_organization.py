"""Seed the demo Organization (ОСББ).

Per plan ``docs/DEMO_SEED_PLAN.md`` PR-13: every demo Building belongs
to a single ``Organization`` of type ``SINGLE_BUILDING`` so the domain
model seen by customers in the demo UI matches the multi-tenant concept
the rest of the product is built on.

Idempotent by design — ``get_or_create`` keyed on the stable demo
``name``. Re-asserts ``is_demo=True`` and the non-nullable metadata on
rerun so a hand-edit in Django admin that toggles the flag off doesn't
silently let the org survive the next nightly reset.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.db import transaction

from .helpers import DEMO_ORGANIZATION_NAME

if TYPE_CHECKING:  # pragma: no cover
    from apps.organizations.models import Organization

logger = logging.getLogger(__name__)

# Public metadata for the demo ОСББ. Kept as module-level constants so
# the values are easy to eyeball during review — the demo shows up in
# customer pitches as "ось як виглядає ОСББ у портфелі" and the details
# should read like a plausible Kyiv housing co-op, not Faker noise.
DEMO_ORGANIZATION_ADDRESS = "вул. Академіка Заболотного, 15"
DEMO_ORGANIZATION_CITY = "Київ"
DEMO_ORGANIZATION_EMAIL = "osbb@demo.com"
DEMO_ORGANIZATION_PHONE = "+380441112233"
DEMO_ORGANIZATION_DESCRIPTION = (
    "Демонстраційна організація — ОСББ, що керує одним житловим "
    "будинком та показовим котеджем у демо-сценарії ApartmentOS."
)
# Feature flags — mirror the set a real customer sees on day one so the
# demo exercises the same UI toggles.
DEMO_ORGANIZATION_FEATURES: dict[str, bool] = {
    "issues": True,
    "posts": True,
    "announcements": True,
    "passes": True,
    "ratings": True,
}


@dataclass
class OrganizationSeedResult:
    """Handle returned to the orchestrator."""

    organization: "Organization" = field(repr=False)
    created: bool = False


@transaction.atomic
def seed() -> OrganizationSeedResult:
    """Create (or refresh) the demo Organization row.

    Returns
    -------
    OrganizationSeedResult
        Carries the freshly-ensured ``Organization`` handle so downstream
        seed modules (``seed_building``) can attach buildings to it
        without a second DB round-trip.
    """
    # Deferred import — see rationale in ``reset_scope.py``: keeps this
    # module importable even when the organizations app is not yet
    # registered in a given manage.py path (e.g. during test collection).
    from apps.organizations.models import Organization, OrganizationType

    org, created = Organization.objects.get_or_create(
        name=DEMO_ORGANIZATION_NAME,
        defaults={
            "type": OrganizationType.SINGLE_BUILDING,
            "address": DEMO_ORGANIZATION_ADDRESS,
            "city": DEMO_ORGANIZATION_CITY,
            "email": DEMO_ORGANIZATION_EMAIL,
            "phone": DEMO_ORGANIZATION_PHONE,
            "description": DEMO_ORGANIZATION_DESCRIPTION,
            "features": dict(DEMO_ORGANIZATION_FEATURES),
            "is_active": True,
            # PR-13 safety: always flip ``is_demo`` on at creation so
            # ``reset_scope`` can match the row.
            "is_demo": True,
        },
    )

    # Defensive update on rerun: if an admin edited the org and flipped
    # ``is_demo`` off, or deactivated it, re-assert the canonical values.
    # We do NOT overwrite the free-text description / phone because a
    # demo operator may have edited them to rehearse a pitch — those are
    # cosmetic and rolling them back would be surprising.
    dirty: list[str] = []
    if org.type != OrganizationType.SINGLE_BUILDING:
        org.type = OrganizationType.SINGLE_BUILDING
        dirty.append("type")
    if not org.is_demo:
        org.is_demo = True
        dirty.append("is_demo")
    if not org.is_active:
        org.is_active = True
        dirty.append("is_active")
    if dirty:
        org.save(update_fields=dirty)

    logger.info(
        "seed_organization: name=%s type=%s created=%s",
        org.name, org.type, created,
    )
    return OrganizationSeedResult(organization=org, created=created)
