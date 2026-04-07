"""Add SiteSettings.current_complex FK to ResidentialComplex."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("site_settings", "0001_initial"),
        ("apartments", "0005_add_residential_complex"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="current_complex",
            field=models.ForeignKey(
                blank=True,
                help_text="The ЖК this installation serves. Buildings are scoped to it.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="apartments.residentialcomplex",
                verbose_name="Active Residential Complex",
            ),
        ),
    ]
