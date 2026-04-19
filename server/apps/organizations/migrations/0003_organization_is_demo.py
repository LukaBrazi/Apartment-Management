"""PR-13: add ``Organization.is_demo`` flag.

Mirrors the PR-12 pattern used on ``User.is_demo`` and ``Building.is_demo``:
a dedicated marker column that the ``seed_demo --reset`` path keys on, so
a real customer organization is safe as long as the flag is False.

No backfill is necessary — PR-13 is the first time the seed creates an
Organization row, so there is no existing "demo organization" in the DB
to retro-flag. Every pre-PR-13 organization is a real customer tenant
and rightly stays ``is_demo=False``.
"""
from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0002_pr9_residency_plus_typed_buildings"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="is_demo",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    "Marks seed-created demo organizations. The nightly "
                    "reset only deletes organizations with is_demo=True."
                ),
                verbose_name="Demo Organization",
            ),
        ),
    ]
