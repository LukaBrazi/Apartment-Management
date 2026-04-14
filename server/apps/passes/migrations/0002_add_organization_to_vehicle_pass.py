# Generated migration for adding organization FK to VehiclePass

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
        ('passes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiclepass',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                help_text='Організація, до якої належить цей пропуск',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='vehicle_passes',
                to='organizations.organization',
            ),
        ),
        migrations.AddIndex(
            model_name='vehiclepass',
            index=models.Index(fields=['organization', 'status'], name='pass_org_status_idx'),
        ),
    ]
