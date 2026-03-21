from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("passes", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="vehiclepass",
            index=models.Index(fields=["status"], name="pass_status_idx"),
        ),
        migrations.AddIndex(
            model_name="vehiclepass",
            index=models.Index(fields=["tenant", "status"], name="pass_tenant_status_idx"),
        ),
        migrations.AddIndex(
            model_name="vehiclepass",
            index=models.Index(fields=["visit_date"], name="pass_visit_date_idx"),
        ),
    ]
