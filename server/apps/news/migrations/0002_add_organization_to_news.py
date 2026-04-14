# Generated migration for adding organization FK to News

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
        ('news', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='news',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                help_text='Організація (NULL = глобальна новина для всіх)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='news_articles',
                to='organizations.organization',
            ),
        ),
        migrations.AddIndex(
            model_name='news',
            index=models.Index(fields=['organization', 'is_published'], name='news_org_published_idx'),
        ),
        migrations.AddIndex(
            model_name='news',
            index=models.Index(fields=['-published_at'], name='news_published_date_idx'),
        ),
    ]
