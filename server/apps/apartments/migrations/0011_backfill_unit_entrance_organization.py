"""Backfill ``Unit.organization`` and ``Entrance.organization`` for any
rows that slipped through.

Context: ``Unit.save()`` and ``Entrance.save()`` auto-derive the
``organization`` FK from the building on create, but rows that existed
BEFORE the FK was introduced (migration history: FK added in PR-38 /
sec-fix-org-scoping) were never rehydrated. Only Building got a
dedicated backfill (``0006_backfill_building_organization``), Unit and
Entrance were relying on implicit future ``save()`` calls that never
came — most seeded units are written once via ``get_or_create`` defaults
and never touched again.

Downstream symptom: ``VehiclePass`` creation tries to derive the pass's
organization from ``unit.organization``. With NULL on the unit the pass
ends up orphaned (``organization=NULL``) and invisible to the tenant's
own ``/passes/my/`` list (which filters on
``organization__in=get_user_organizations(user)``).

Fix: walk every Entrance/Unit where ``organization_id IS NULL`` and copy
the value from the parent Building. Idempotent, no-op reverse.
"""

from django.db import migrations


def backfill_entrance_and_unit_org(apps, schema_editor):
    Entrance = apps.get_model("apartments", "Entrance")
    Unit = apps.get_model("apartments", "Unit")

    # Entrance -> Building.organization
    # Subquery via F-expression isn't straightforward in ORM so we
    # iterate — scale here is small (demo: ~4 entrances, prod: tens).
    for entrance in Entrance.objects.filter(
        organization__isnull=True, building__organization__isnull=False
    ).select_related("building"):
        entrance.organization_id = entrance.building.organization_id
        entrance.save(update_fields=["organization"])

    # Unit -> Entrance.organization (which is now populated by the
    # block above, plus whatever was already correctly set).
    for unit in Unit.objects.filter(
        organization__isnull=True, entrance__organization__isnull=False
    ).select_related("entrance"):
        unit.organization_id = unit.entrance.organization_id
        unit.save(update_fields=["organization"])


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("apartments", "0010_building_is_demo"),
    ]

    operations = [
        migrations.RunPython(backfill_entrance_and_unit_org, reverse_code=noop_reverse),
    ]
