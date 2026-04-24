from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("news", "0003_newsread"),
    ]

    operations = [
        migrations.AddField(
            model_name="news",
            name="notify_subscribers",
            field=models.BooleanField(
                default=False,
                help_text="Send Telegram notification to org subscribers when published",
                verbose_name="Notify Subscribers",
            ),
        ),
    ]
