"""Data migration: backfill Unit/Entrance/Building from legacy Apartment rows.

This is PR-1 of the ``refactor/remove-legacy-apartment`` series — a
gap-filler that closes every blocker surfaced by
``manage.py audit_legacy_apartments`` **before** any code cutover runs.

Forward logic (idempotent, safe to re-run):

1. For every ``Apartment`` that has no reverse ``Unit`` bridge:
     a. ``get_or_create`` a ``Building`` by the (stripped) ``Apartment.building``
        string.  Address defaults to the same string so NOT NULL constraints
        pass; operators can rename/merge later.
     b. ``get_or_create`` an ``Entrance`` named ``"1"`` under that Building.
        (Legacy rows have no entrance concept; a single default entrance
        per building is the minimal lossless mapping.)
     c. ``Unit.objects.create`` with ``number=apartment.unit_number``,
        ``floor=apartment.floor``, ``apartment=apartment``.

2. For every ``Issue`` where ``apartment_id IS NOT NULL AND unit_id IS NULL``,
   set ``issue.unit_id = apartment.unit.pkid``.  PR-2 cutover relies on
   ``Issue.unit`` being the source of truth.

3. For every user with a legacy ``Apartment.tenant`` link, ensure
   ``Profile.unit`` points at ``Apartment.unit``.  Never overwrites an
   existing non-null ``Profile.unit`` — operator edits win.

4. If exactly one ``Organization`` exists and any ``Building`` has
   ``organization_id IS NULL``, adopt those buildings into that single
   organization.  Multi-org installations are left untouched (the audit
   command keeps flagging them until an operator resolves the ambiguity).

Reverse logic: intentionally a no-op.  Reversing this migration cannot
reconstruct the Apartment-only world without discarding the operator's
subsequent edits; rolling back should instead use a fresh backup restore.
"""
from __future__ import annotations

from django.db import migrations


def _stripped(s: str) -> str:
    return (s or "").strip()


def backfill_units(apps, schema_editor):
    Apartment = apps.get_model("apartments", "Apartment")
    Building = apps.get_model("apartments", "Building")
    Entrance = apps.get_model("apartments", "Entrance")
    Unit = apps.get_model("apartments", "Unit")
    Issue = apps.get_model("issues", "Issue")
    Profile = apps.get_model("profiles", "Profile")
    Organization = apps.get_model("organizations", "Organization")

    # ── 1. Synthesise Building/Entrance/Unit for unbridged Apartments ──
    unbridged = Apartment.objects.filter(unit__isnull=True)
    for apt in unbridged:
        building_name = _stripped(apt.building) or "Unknown"

        building, _ = Building.objects.get_or_create(
            name=building_name,
            defaults={
                "address": building_name,
                "city": "",
                "is_active": True,
            },
        )
        entrance, _ = Entrance.objects.get_or_create(
            building=building,
            name="1",
        )
        # Unit.number + entrance is unique_together, so create-or-attach-
        # by-natural-key to stay idempotent across retries.
        unit, created = Unit.objects.get_or_create(
            entrance=entrance,
            number=apt.unit_number,
            defaults={"floor": apt.floor, "apartment": apt},
        )
        if not created and unit.apartment_id is None:
            unit.apartment = apt
            unit.save(update_fields=["apartment"])

    # ── 2. Backfill Issue.unit from Issue.apartment.unit ───────────────
    gap_issues = Issue.objects.filter(
        apartment__isnull=False, unit__isnull=True
    ).select_related("apartment")
    for issue in gap_issues:
        # Unit was just created above (or already existed); access via
        # reverse OneToOne.  apartment.unit may still be None if the
        # Apartment is somehow orphaned — skip those rather than raise.
        unit = Unit.objects.filter(apartment_id=issue.apartment_id).first()
        if unit is not None:
            issue.unit_id = unit.pkid
            issue.save(update_fields=["unit"])

    # ── 3. Backfill Profile.unit from Apartment.tenant ─────────────────
    tenanted = Apartment.objects.filter(tenant__isnull=False).select_related(
        "tenant"
    )
    for apt in tenanted:
        unit = Unit.objects.filter(apartment_id=apt.pkid).first()
        if unit is None:
            continue
        profile = Profile.objects.filter(user_id=apt.tenant_id).first()
        if profile is None:
            # Profile is normally created via post_save signal on User, but
            # in case it isn't, skip rather than create one here — the
            # profiles app owns its own invariants.
            continue
        if profile.unit_id is None:
            profile.unit_id = unit.pkid
            profile.save(update_fields=["unit"])

    # ── 4. Adopt orphan Buildings into single Organization, if unambiguous ─
    orgs = list(Organization.objects.all()[:2])
    if len(orgs) == 1:
        sole_org = orgs[0]
        orphan_buildings = Building.objects.filter(organization__isnull=True)
        for b in orphan_buildings:
            b.organization_id = sole_org.pkid
            b.save(update_fields=["organization"])


def noop_reverse(apps, schema_editor):
    # Reversing would have to choose between destroying synthesised rows
    # (which may have been edited post-migration) and leaving them
    # orphaned from the Apartment side.  Neither is safe; restore from
    # backup instead.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("apartments", "0003_apartment_unique_per_building"),
        ("issues", "0003_make_apartment_nullable"),
        ("profiles", "0001_initial"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_units, reverse_code=noop_reverse),
    ]
