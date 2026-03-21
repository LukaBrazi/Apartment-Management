import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class TelegramProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_profile",
    )
    chat_id = models.BigIntegerField(unique=True)
    is_active = models.BooleanField(default=True)
    # Notification preferences
    notify_issues = models.BooleanField(default=True, verbose_name="Issue updates")
    notify_passes = models.BooleanField(default=True, verbose_name="Pass updates")
    notify_announcements = models.BooleanField(default=True, verbose_name="Announcements")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Telegram Profile"
        verbose_name_plural = "Telegram Profiles"

    def __str__(self):
        return f"TelegramProfile(user={self.user.email}, chat_id={self.chat_id})"


def token_expires_at():
    return timezone.now() + timedelta(minutes=15)


class TelegramVerificationToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_tokens",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField(default=token_expires_at)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Telegram Verification Token"
        verbose_name_plural = "Telegram Verification Tokens"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Token({self.user.email}, used={self.is_used})"

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
