from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0005_organizationbot_default_bot_must_have_no_org"),
    ]
    operations = [
        migrations.AddField(
            model_name="telegramprofile",
            name="notify_emergency",
            field=models.BooleanField(default=True, verbose_name="Emergency alerts"),
        ),
        migrations.AddField(
            model_name="telegramprofile",
            name="notify_visits",
            field=models.BooleanField(default=False, verbose_name="Visit notifications"),
        ),
        migrations.AddField(
            model_name="telegramprofile",
            name="telegram_username",
            field=models.CharField(
                blank=True,
                help_text="Cached Telegram @username from /start command.",
                max_length=64,
                null=True,
                verbose_name="Telegram username",
            ),
        ),
    ]
