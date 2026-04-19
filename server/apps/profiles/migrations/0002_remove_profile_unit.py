"""PR-11: drop the legacy ``Profile.unit`` FK.

After PR-10's Residency backfill the canonical link between a user and
their Unit lives in ``apartments.Residency`` (``is_primary=True``) —
``Profile.unit`` is no longer read by any view or serializer.  This
migration removes the column.

Depends on ``apartments.0009_backfill_residency_from_profile`` so the
Residency rows are in place *before* the FK is dropped — rolling back
PR-11 requires rolling back PR-10's data migration manually (the
reverse of 0009 is intentionally a no-op).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0001_initial"),
        ("apartments", "0009_backfill_residency_from_profile"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="unit",
        ),
    ]
