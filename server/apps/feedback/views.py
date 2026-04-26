# Imports
import logging

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.feedback.serializers import FeedbackSerializer
from apps.feedback.throttles import FeedbackRateThrottle

# Get the logger
logger = logging.getLogger(__name__)


class FeedbackCreateAPIView(generics.CreateAPIView):
    """Feedback Create API View

    Allows authenticated users to submit feedback about the application.

    Extends:
        generics.CreateAPIView

    Attributes:
        serializer_class: The serializer class.
        permission_classes: The permission classes.
        throttle_classes: The throttle classes.
    """

    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [FeedbackRateThrottle]

    def perform_create(self, serializer):
        """Save feedback with the current user and trigger notification task."""
        from apps.feedback.tasks import send_feedback_notification_task

        feedback = serializer.save(user=self.request.user)
        send_feedback_notification_task.delay(feedback.pkid)
