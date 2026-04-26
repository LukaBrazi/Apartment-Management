# Imports
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel


class Feedback(TimeStampedModel):
    """Feedback Model

    Stores user feedback about the ApartmentOS application.

    Extends:
        TimeStampedModel

    Attributes:
        user (ForeignKey): The user who submitted the feedback.
        message (TextField): The feedback message.
        is_reviewed (BooleanField): Whether the feedback has been reviewed by admin.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feedbacks",
        verbose_name=_("User"),
    )
    message = models.TextField(
        max_length=2000,
        verbose_name=_("Message"),
    )
    is_reviewed = models.BooleanField(
        default=False,
        verbose_name=_("Is Reviewed"),
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Feedback")
        verbose_name_plural = _("Feedbacks")

    def __str__(self) -> str:
        return f"Feedback({self.user.email}, {self.created_at:%Y-%m-%d})"
