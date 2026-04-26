# Imports
from rest_framework import serializers

from apps.feedback.models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    """Feedback Serializer

    Serializes feedback data for the API.
    """

    class Meta:
        model = Feedback
        fields = ["id", "message", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_message(self, value: str) -> str:
        """Validate that the message is at least 10 characters long."""
        if len(value) < 10:
            raise serializers.ValidationError(
                "Повідомлення має містити щонайменше 10 символів."
            )
        return value
