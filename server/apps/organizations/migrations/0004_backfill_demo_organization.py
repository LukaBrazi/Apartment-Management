"""Backfill the demo ``Organization`` + link existing demo Buildings to it.

Context: PR-13 (commits 5367813 / c1d2304) introduced ``Organization`` as
the root of the demo tenant scope. From that point on ``seed_demo``
calls ``seed_organization.seed()`` first, then threads the resulting
organization through ``seed_building`` so every Building/Entrance/Unit is
FK-linked to it. However, environments that were seeded BEFORE PR-13
landed still carry the demo Building / Entrance / Unit rows with
``organization=NULL``, and no subsequent run of ``seed_demo`` has been
scheduled to heal them.

Symptom on prod: Django admin shows ``0 Organizations`` while
``/admin/apartments/building/`` has the demo row. Because every
``VehiclePass``-related view filters on
``organization__in=get_user_organizations(user)``, a tenant logged into
that unit sees an empty ``/passes/my/`` list — the bug tracked by
commits b9a99b6 / 5dcf957. Those two commits fixed the API layer to
auto-derive the pass's org from the unit; **this** migration closes the
remaining gap by ensuring the unit itself (and its ancestors) has an
organization to derive from.

What this migration does (idempotent, no-op reverse):

1. Creates the canonical demo Organization via ``get_or_create`` keyed
   on ``DEMO_ORGANIZATION_NAME`` (matches what ``seed_organization.py``
   would do). ``is_demo=True`` is asserted so the nightly reset knows
   the row belongs to the demo scope.
2. Links every demo Building (``name startswith`` the demo prefix) with
   ``organization_id IS NULL`` to the freshly-ensured org.
3. Cascades to Entrance rows under those buildings, then Unit rows
   under those entrances. ``apartments/0011_backfill_unit_entrance_organization``
   already runs this walk for rows whose parent Building has an org —
   the order of migrations (apartments runs unconditionally first, then
   organizations 0004) means we repeat the walk here for the newly-linked
   Buildings. Cheap query, strictly idempotent.

The migration deliberately does NOT create demo residents, issues,
posts, or any other row — that is the seed's job. The scope here is
narrow: fix the FK chain so the existing rows become visible and the
API-layer auto-derivation (in ``VehiclePass.save``) can actually
succeed. Anything else is recoverable by rerunning ``seed_demo``.
"""
from __future__ import annotations

from django.db import migrations


# Hard-coded mirrors of ``apps.common.seed.helpers`` constants. Migrations
# should not import from application code at module level — the seed module
# may pull in code that isn't importable at migration-replay time (fresh
# envs, downgrades). Keeping these as module-level strings here mirrors
# the same pattern used by ``reset_scope.py``'s safety constants.
DEMO_ORGANIZATION_NAME = "ОСББ «Зелений Квартал — Демо»"
DEMO_BUILDING_NAME_PREFIX = "Зелений Квартал — Демо"


# Organization defaults — copy of ``seed_organization.DEMO_ORGANIZATION_*``.
# Duplicated here so a replay of this migration on a fresh DB produces the
# same row the seed would have produced, without importing from the seed
# module (which requires the full Django app registry).
_ORG_DEFAULTS = {
    "type": "single_building",  # OrganizationType.SINGLE_BUILDING
    "address": "вул. Академіка Заболотного, 15",
    "city": "Київ",
    "email": "osbb@demo.com",
    "phone": "+380441112233",
    "description": (
        "Демонстраційна організація — ОСББ, що керує одним житловим "
        "будинком та показовим котеджем у демо-сценарії ApartmentOS."
    ),
    "features": {
        "issues": True,
        "posts": True,
        "announcements": True,
        "passes": True,
        "ratings": True,
    },
    "is_active": True,
    "is_demo": True,
}


def backfill_demo_org(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    Building = apps.get_model("apartments", "Building")
    Entrance = apps.get_model("apartments", "Entrance")
    Unit = apps.get_model("apartments", "Unit")

    # 1. Ensure the demo Organization exists. ``get_or_create`` is
    #    idempotent — if the seed has already landed on this DB the row
    #    is returned untouched; on pre-PR-13 envs it is created fresh
    #    with the canonical metadata.
    org, created = Organization.objects.get_or_create(
        name=DEMO_ORGANIZATION_NAME,
        defaults=_ORG_DEFAULTS,
    )
    # Defensive re-assertion of the demo marker — same pattern as
    # ``seed_organization.seed()``. If an admin ever flipped it off by
    # hand the nightly reset would skip the row forever.
    dirty: list[str] = []
    if not org.is_demo:
        org.is_demo = True
        dirty.append("is_demo")
    if not org.is_active:
        org.is_active = True
        dirty.append("is_active")
    if dirty:
        org.save(update_fields=dirty)

    # 2. Link demo Buildings (apartment block + cottage, matched by the
    #    shared name prefix) that still carry ``organization_id=NULL``.
    Building.objects.filter(
        name__startswith=DEMO_BUILDING_NAME_PREFIX,
        organization__isnull=True,
    ).update(organization=org)

    # 3. Cascade the org down to Entrance/Unit rows under the newly
    #    linked Buildings. ``apartments/0011`` already handles rows
    #    where the parent Building had a non-NULL org at the time 0011
    #    ran — but that migration has no knowledge of the new org, so
    #    anything under our demo Building would still be NULL. Walk the
    #    two levels explicitly to be sure.
    Entrance.objects.filter(
        building__organization=org,
        organization__isnull=True,
    ).update(organization=org)
    Unit.objects.filter(
        entrance__organization=org,
        organization__isnull=True,
    ).update(organization=org)


def noop_reverse(apps, schema_editor):
    # No reverse — the data we just wrote is what production needs to
    # see. Rolling it back would reintroduce the "invisible pass" bug.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0003_organization_is_demo"),
        # Must run AFTER the Entrance/Unit backfill added in
        # apartments/0011 so we don't step on its work, and because we
        # need the FK columns to exist on both models.
        ("apartments", "0011_backfill_unit_entrance_organization"),
    ]

    operations = [
        migrations.RunPython(backfill_demo_org, reverse_code=noop_reverse),
    ]
