from django.utils import timezone
from rest_framework import serializers
from .models import TelegramProfile, TelegramVerificationToken


class GenerateTokenSerializer(serializers.Serializer):
    """Response serializer for token generation."""
    token = serializers.UUIDField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    bot_username = serializers.CharField(read_only=True)
    deep_link = serializers.CharField(read_only=True)


class VerifyTokenSerializer(serializers.Serializer):
    """Request serializer for bot token verification."""
    token = serializers.UUIDField()
    chat_id = serializers.IntegerField()

    def validate_token(self, value):
        try:
            token_obj = TelegramVerificationToken.objects.select_related("user").get(token=value)
        except TelegramVerificationToken.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired token.")
        if not token_obj.is_valid:
            raise serializers.ValidationError("Token has expired or already been used.")
        self.context["token_obj"] = token_obj
        return value


class TelegramStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramProfile
        fields = ["chat_id", "is_active", "notify_issues", "notify_passes", "notify_announcements", "created_at"]
        read_only_fields = ["chat_id", "created_at"]


class TelegramSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramProfile
        fields = ["notify_issues", "notify_passes", "notify_announcements"]
