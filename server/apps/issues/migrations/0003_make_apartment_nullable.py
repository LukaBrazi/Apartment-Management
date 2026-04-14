# Generated migration: Make Issue.apartment nullable

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('apartments', '0002_add_organization_fks'),
        ('issues', '0002_add_organization_to_issue'),
    ]

    operations = [
        migrations.AlterField(
            model_name='issue',
            name='apartment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='issues', to='apartments.apartment', verbose_name='Apartment'),
        ),
    ]
