"""PR-7: delete the legacy ``Apartment`` model.

Run after ``issues.0004_remove_issue_apartment`` so no FK references
``apartments.Apartment`` remain.  The ``Unit.apartment`` bridge is
dropped first (it's the only OneToOne on the Apartment table), then
the model itself is deleted.

After this migration the legacy columns/tables are gone; the
canonical chain is Organization → Building → Entrance → Unit, with
``Profile.unit`` holding tenant ownership.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("apartments", "0004_backfill_units_from_legacy_apartments"),
        ("issues", "0004_remove_issue_apartment"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="unit",
            name="apartment",
        ),
        migrations.DeleteModel(
            name="Apartment",
        ),
    ]
