import apps.notifications.models
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TelegramProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chat_id", models.BigIntegerField(unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("notify_issues", models.BooleanField(default=True, verbose_name="Issue updates")),
                ("notify_passes", models.BooleanField(default=True, verbose_name="Pass updates")),
                ("notify_announcements", models.BooleanField(default=True, verbose_name="Announcements")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="telegram_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Telegram Profile", "verbose_name_plural": "Telegram Profiles"},
        ),
        migrations.CreateModel(
            name="TelegramVerificationToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("is_used", models.BooleanField(default=False)),
                ("expires_at", models.DateTimeField(default=apps.notifications.models.token_expires_at)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="telegram_tokens", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Telegram Verification Token", "verbose_name_plural": "Telegram Verification Tokens", "ordering": ["-created_at"]},
        ),
    ]
