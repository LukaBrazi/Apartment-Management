"""PR-12: add ``Building.is_demo`` flag + backfill the demo building row.

See the twin migration ``apps/users/migrations/0002_user_is_demo.py`` for
rationale. Without the backfill the nightly reset would stop matching
the current demo Building row after deploy (because the new scope filter
keys on ``is_demo=True`` in addition to the name).
"""
from __future__ import annotations

from django.db import migrations, models


def _flag_existing_demo_buildings(apps, schema_editor):
    Building = apps.get_model("apartments", "Building")
    # Mirror apps.common.seed.helpers.DEMO_BUILDING_NAME — inlined so
    # historical migrations stay self-contained.
    Building.objects.filter(
        name="Зелений Квартал — Демо",
    ).update(is_demo=True)


def _unflag_all_demo_buildings(apps, schema_editor):
    Building = apps.get_model("apartments", "Building")
    Building.objects.filter(is_demo=True).update(is_demo=False)


class Migration(migrations.Migration):

    dependencies = [
        ("apartments", "0009_backfill_residency_from_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="building",
            name="is_demo",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    "Marks seed-created demo buildings. The nightly reset "
                    "only deletes buildings with is_demo=True."
                ),
                verbose_name="Demo Building",
            ),
        ),
        migrations.RunPython(
            _flag_existing_demo_buildings,
            reverse_code=_unflag_all_demo_buildings,
        ),
    ]
