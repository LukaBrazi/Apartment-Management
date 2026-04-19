"""PR-8: drop ``Building.complex`` FK and delete ``ResidentialComplex``.

By the time this migration runs, the only two references to
``ResidentialComplex`` have been neutralised:

* ``SiteSettings.current_complex`` — removed in
  ``site_settings.0005_drop_current_complex``.
* ``Building.complex`` — removed as the first operation of this
  migration.

With all FKs gone, the ``DeleteModel`` can proceed safely.  Going
forward, buildings live under ``Organization`` exclusively; whitelabel
ЖК display copy lives as plain text on ``SiteSettings``
(``complex_name`` / ``complex_address`` / ``complex_description``).

Irreversible: we don't restore the FK column or recreate the model.
Roll forward from a pre-PR-8 backup if a rollback is ever needed.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("apartments", "0006_backfill_building_organization"),
        ("site_settings", "0005_drop_current_complex"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="building",
            name="complex",
        ),
        migrations.DeleteModel(
            name="ResidentialComplex",
        ),
    ]
