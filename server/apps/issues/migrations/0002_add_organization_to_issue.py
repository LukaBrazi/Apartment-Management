# Generated migration for adding organization FK to Issue

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
        ('issues', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                help_text='Організація, до якої належить ця заявка',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='issues',
                to='organizations.organization',
            ),
        ),
        migrations.AddIndex(
            model_name='issue',
            index=models.Index(
                fields=['organization', 'status'],
                name='issue_org_status_idx',
            ),
        ),
    ]
