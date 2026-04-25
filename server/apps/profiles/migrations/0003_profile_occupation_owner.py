"""PR: add OWNER choice to Profile.Occupation.

Residents may now be either "tenant" (орендар) or "owner" (власник).
This is a pure choices-level change — the underlying VARCHAR column stays
the same width (max_length=20) so no schema migration is needed; Django
still generates an AlterField to keep the migration state in sync.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0002_remove_profile_unit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="occupation",
            field=models.CharField(
                choices=[
                    ("mason", "Mason"),
                    ("carpenter", "Carpenter"),
                    ("plumber", "Plumber"),
                    ("roofer", "Roofer"),
                    ("painter", "Painter"),
                    ("electrician", "Electrician"),
                    ("hvac", "HVAC"),
                    ("tenant", "Tenant"),
                    ("owner", "Owner"),
                    ("guard", "Guard"),
                ],
                default="tenant",
                max_length=20,
                verbose_name="Occupation",
            ),
        ),
    ]
