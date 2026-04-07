"""Add ResidentialComplex model and Building.complex FK."""

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apartments", "0004_data_migrate_apartments_to_units"),
    ]

    operations = [
        # 1. Create ResidentialComplex model
        migrations.CreateModel(
            name="ResidentialComplex",
            fields=[
                (
                    "pkid",
                    models.BigAutoField(
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "name",
                    models.CharField(
                        help_text="e.g. ЖК Сонячний",
                        max_length=200,
                        verbose_name="Name",
                    ),
                ),
                (
                    "address",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Main address or district of the complex",
                        max_length=300,
                        verbose_name="Address",
                    ),
                ),
                (
                    "city",
                    models.CharField(
                        blank=True, default="", max_length=100, verbose_name="City"
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, default="", verbose_name="Description"
                    ),
                ),
            ],
            options={
                "verbose_name": "Residential Complex",
                "verbose_name_plural": "Residential Complexes",
                "ordering": ["name"],
            },
        ),
        # 2. Add Building.complex FK (nullable for backward compat)
        migrations.AddField(
            model_name="building",
            name="complex",
            field=models.ForeignKey(
                blank=True,
                help_text="ЖК this building belongs to",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="buildings",
                to="apartments.residentialcomplex",
                verbose_name="Residential Complex",
            ),
        ),
    ]
