"""PR-8: backfill ``Building.organization`` for any straggler rows.

``apartments.0004_backfill_units_from_legacy_apartments`` already runs
the sole-organization adoption during the main legacy sweep.  This
migration is a belt-and-suspenders re-run right before we drop
``Building.complex`` and ``ResidentialComplex``: any environment that
produced a Building row *between* PR-1 and PR-8 (e.g. via the admin or
the demo seeder) with ``organization=NULL`` gets one final chance to be
adopted.

Rules:
- if exactly **one** ``Organization`` exists, every orphan Building is
  attached to it;
- otherwise the migration is a no-op and the operator must assign
  organizations by hand before the follow-up schema migration
  (``0007_delete_residentialcomplex``) would leave orphan rows behind.

This migration is idempotent (re-running changes nothing) and has a
no-op reverse — there is no meaningful way to undo "we gave this
Building an organization" without restoring from backup.
"""

from django.db import migrations


def backfill_building_org(apps, schema_editor):
    Building = apps.get_model("apartments", "Building")
    Organization = apps.get_model("organizations", "Organization")

    orgs = list(Organization.objects.all()[:2])
    if len(orgs) != 1:
        return
    sole_org = orgs[0]
    Building.objects.filter(organization__isnull=True).update(
        organization_id=sole_org.pkid
    )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("apartments", "0005_remove_unit_apartment_delete_apartment"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_building_org, reverse_code=noop_reverse),
    ]
