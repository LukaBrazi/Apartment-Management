from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0003_alter_report_organization"),
    ]

    operations = [
        migrations.AddField(
            model_name="report",
            name="reported_person_name",
            field=models.CharField(
                blank=True,
                help_text="Free-text name or description of the person being reported. Used when the reporter does not know the exact username.",
                max_length=255,
                verbose_name="Reported person name",
            ),
        ),
    ]
