"""PR-7: drop the legacy ``Issue.apartment`` FK.

The Unit→Issue link has been canonical since PR-2 (dual-write) and
the read path cut over in PR-3.  Any remaining production rows with
``apartment_id IS NOT NULL AND unit_id IS NULL`` were repaired by the
PR-1 backfill (``apartments.0004_backfill_units_from_legacy_apartments``)
and gated by ``audit_legacy_apartments``.  Removing the column here
lets us DeleteModel(Apartment) in ``apartments.0005``.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("issues", "0003_make_apartment_nullable"),
        # Must run after the backfill so no live row still points at
        # Apartment only.  The FK on Unit→Apartment is dropped in the
        # next apartments migration, not here.
        ("apartments", "0004_backfill_units_from_legacy_apartments"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="issue",
            name="apartment",
        ),
    ]
