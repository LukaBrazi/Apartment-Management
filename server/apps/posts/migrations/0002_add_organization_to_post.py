# Generated migration for adding organization FK to Post

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
        ('posts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                help_text='Організація, до якої належить ця публікація',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='posts',
                to='organizations.organization',
            ),
        ),
        migrations.AddIndex(
            model_name='post',
            index=models.Index(fields=['organization'], name='post_organization_idx'),
        ),
        migrations.AddIndex(
            model_name='post',
            index=models.Index(fields=['author', 'created_at'], name='post_author_created_idx'),
        ),
    ]
