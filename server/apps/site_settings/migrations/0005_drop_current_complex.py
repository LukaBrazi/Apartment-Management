"""PR-8: absorb ``current_complex`` into plain SiteSettings text fields.

``SiteSettings.current_complex`` was a FK into ``apartments.ResidentialComplex``
— the last live reference to that model.  Before we delete it in
``apartments.0007_delete_residentialcomplex``, this migration copies
the linked complex's ``name`` and ``address`` into the already-existing
``complex_name`` / ``complex_address`` text fields on SiteSettings (if
and only if the text field is empty), then drops the FK column.

After this migration the ЖК display values live as plain strings on the
SiteSettings row — the same fields the admin already exposes in the
"Complex Information" fieldset.  The separate ``ResidentialComplex``
model is no longer needed for runtime lookups.

Idempotent: re-running is a no-op because the text fields are only
updated when empty.  The reverse is a no-op — we won't synthesise
``ResidentialComplex`` rows back from free-form text.
"""

from django.db import migrations


def absorb_current_complex(apps, schema_editor):
    SiteSettings = apps.get_model("site_settings", "SiteSettings")

    for settings in SiteSettings.objects.filter(current_complex__isnull=False):
        complex_obj = settings.current_complex
        changed_fields = []
        if not settings.complex_name and complex_obj.name:
            settings.complex_name = complex_obj.name
            changed_fields.append("complex_name")
        if not settings.complex_address and complex_obj.address:
            settings.complex_address = complex_obj.address
            changed_fields.append("complex_address")
        if (
            not settings.complex_description
            and getattr(complex_obj, "description", "")
        ):
            settings.complex_description = complex_obj.description
            changed_fields.append("complex_description")
        if changed_fields:
            settings.save(update_fields=changed_fields)


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("site_settings", "0004_rebrand_apartmentos"),
        ("apartments", "0005_remove_unit_apartment_delete_apartment"),
    ]

    operations = [
        migrations.RunPython(absorb_current_complex, reverse_code=noop_reverse),
        migrations.RemoveField(
            model_name="sitesettings",
            name="current_complex",
        ),
    ]
