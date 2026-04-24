from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0002_add_organization_to_post"),
        ("apartments", "0011_backfill_unit_entrance_organization"),
        ("organizations", "0004_backfill_demo_organization"),
    ]

    operations = [
        migrations.AddField(
            model_name="announcement",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="announcements",
                to="organizations.organization",
                verbose_name="Organization",
                help_text="Required for org-wide announcements (when building is not set)",
            ),
        ),
        migrations.AddField(
            model_name="announcement",
            name="entrance",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="announcements",
                to="apartments.entrance",
                verbose_name="Entrance",
                help_text="If set, only residents of this entrance receive the notification",
            ),
        ),
        migrations.AddField(
            model_name="announcement",
            name="notify_subscribers",
            field=models.BooleanField(
                default=False,
                help_text="Send Telegram notification to matching subscribers when published",
                verbose_name="Notify Subscribers",
            ),
        ),
        migrations.AlterField(
            model_name="announcement",
            name="building",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="announcements",
                to="apartments.building",
                verbose_name="Building",
            ),
        ),
    ]
