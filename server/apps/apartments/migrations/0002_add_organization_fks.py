# Generated migration to add organization foreign keys

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('apartments', '0001_initial'),
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='building',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='buildings', to='organizations.organization', help_text='Organization that owns this building'),
        ),
        migrations.AddField(
            model_name='entrance',
            name='organization',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='entrances', to='organizations.organization'),
        ),
        migrations.AddField(
            model_name='unit',
            name='organization',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='units', to='organizations.organization'),
        ),
    ]
