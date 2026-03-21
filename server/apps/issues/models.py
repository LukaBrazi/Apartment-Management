# Imports
import logging
from datetime import timedelta
from typing import Dict

from apps.apartments.models import Apartment, Unit
from apps.common.models import ContentView, TimeStampedModel
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

# Get the user model
User = get_user_model()


# Get the logger
logger = logging.getLogger(__name__)


# ── Category Model (with SLA) ──────────────────────────────────────────────

class Category(TimeStampedModel):
    """Service request category with SLA hours."""

    name = models.CharField(_("Name"), max_length=100, unique=True)
    sla_hours = models.PositiveIntegerField(
        _("SLA Hours"),
        default=72,
        help_text="Hours within which the issue must be resolved.",
    )

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="category_name_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} (SLA: {self.sla_hours}h)"


# ── Allowed status transitions ─────────────────────────────────────────────
ALLOWED_TRANSITIONS = {
    "reported": {"accepted", "rejected"},
    "accepted": {"in_progress", "rejected"},
    "in_progress": {"done", "rejected"},
    "done": set(),
    "rejected": set(),
    # Legacy statuses → map to new ones
    "resolved": set(),
}


# ── Issue Model ─────────────────────────────────────────────────────────────

class Issue(TimeStampedModel):
    """Issue

    Issue class is used to represent an issue in the database.

    Extends:
        TimeStampedModel

    Attributes:
        apartment (ForeignKey): The apartment the issue belongs to.
        reported_by (ForeignKey): The user who reported the issue.
        assigned_to (ForeignKey): The user assigned to the issue.
        title (str): The title of the issue.
        description (str): The description of the issue.
        status (str): The status of the issue.
        priority (str): The priority of the issue.
        resolved_on (Date): The date when the issue was resolved.

    Methods:
        __str__(): Return the string representation of the issue.
        save(*args, **kwargs): Save the issue and notify the assigned user.
        notify_assigned_user(): Notify the assigned user.

    Constants:
        IssueStatus: The status of the issue.
        Priority: The priority of the issue.
    """

    # Constants for the issue status (extended for SLA flow)
    class IssueStatus(models.TextChoices):
        REPORTED = ("reported", _("Reported"))
        ACCEPTED = ("accepted", _("Accepted"))
        IN_PROGRESS = ("in_progress", _("In Progress"))
        DONE = ("done", _("Done"))
        REJECTED = ("rejected", _("Rejected"))
        # Legacy kept for backward compat
        RESOLVED = ("resolved", _("Resolved"))

    # Constants for the issue priority
    class Priority(models.TextChoices):
        LOW = ("low", _("Low"))
        MEDIUM = ("medium", _("Medium"))
        HIGH = ("high", _("High"))

    # Attributes
    apartment = models.ForeignKey(
        Apartment,
        on_delete=models.CASCADE,
        related_name="issues",
        verbose_name=_("Apartment"),
    )
    # New: link to Unit (preferred over apartment FK going forward)
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issues",
        verbose_name=_("Unit"),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issues",
        verbose_name=_("Category"),
    )
    due_at = models.DateTimeField(_("Due At"), null=True, blank=True)
    reported_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reported_by_issues",
        verbose_name=_("Reported By"),
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_to_issues",
        verbose_name=_("Assigned To"),
    )
    title = models.CharField(_("Issue Title"), max_length=255)
    description = models.TextField(_("Issue Description"))
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=IssueStatus.choices,
        default=IssueStatus.REPORTED,
    )
    priority = models.CharField(
        _("Priority"),
        max_length=20,
        choices=Priority.choices,
        default=Priority.LOW,
    )
    resolved_on = models.DateField(_("Resolved On"), null=True, blank=True)
    content_views = GenericRelation(ContentView, related_query_name="issues")

    class Meta(TimeStampedModel.Meta):
        verbose_name = _("Issue")
        verbose_name_plural = _("Issues")
        indexes = [
            models.Index(fields=["status"], name="issue_status_idx"),
            models.Index(fields=["priority"], name="issue_priority_idx"),
            models.Index(fields=["status", "priority"], name="issue_status_priority_idx"),
            models.Index(fields=["reported_by", "status"], name="issue_reporter_status_idx"),
            models.Index(fields=["assigned_to", "status"], name="issue_assignee_status_idx"),
        ]

    # String Representation
    def __str__(self) -> str:
        return self.title

    @property
    def is_overdue(self) -> bool:
        """True if due_at is set and has passed without being done/resolved."""
        if not self.due_at:
            return False
        if self.status in (self.IssueStatus.DONE, self.IssueStatus.RESOLVED):
            return False
        return timezone.now() > self.due_at

    def transition_to(self, new_status: str) -> None:
        """Perform a status transition, raising ValueError for invalid moves."""
        allowed = ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from '{self.status}' to '{new_status}'. "
                f"Allowed: {allowed or 'none (terminal state)'}."
            )
        self.status = new_status
        if new_status in (self.IssueStatus.DONE, self.IssueStatus.RESOLVED):
            self.resolved_on = timezone.now().date()
        self.save(update_fields=["status", "resolved_on"])

    # Save Method
    def save(self, *args: Dict, **kwargs: Dict) -> None:
        """Save the issue and notify the assigned user.

        Args:
            *args (dict): The arguments.
            **kwargs (dict): The keyword arguments.

        Raises:
            Exception: If the email sending fails.
        """

        # Compute due_at on first save when category is set
        is_existing = self.pk is not None
        if not is_existing and self.category and not self.due_at:
            self.due_at = timezone.now() + timedelta(hours=self.category.sla_hours)

        # Check if the issue is existing (re-use variable from above)

        # Get the old assigned user
        old_assigned_to = None

        # If the issue is existing
        if is_existing:
            # Get the old issue
            old_issue = Issue.objects.get(pk=self.pk)

            # Update the old assigned user
            old_assigned_to = old_issue.assigned_to

        # Save the issue
        super().save(*args, **kwargs)

        # If the issue is existing and the assigned user has changed
        if (
            is_existing
            and old_assigned_to != self.assigned_to
            and self.assigned_to is not None
        ):
            # Send the notification
            self.notify_assigned_user()

    # Notify Assigned User Method
    def notify_assigned_user(self) -> None:
        """Notify the assigned user.

        Raises:
            Exception: If the email sending fails.
        """

        # Try
        try:
            # Set the subject, from email, and recipient list
            subject = f"New Issue Assigned: {self.title}"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [self.assigned_to.email]

            # Set the context
            context = {
                "issue": self,
                "site_name": settings.SITE_NAME,
            }

            # Set the HTML and text email
            html_email = render_to_string(
                "issues/issue_assignment_notification_email.html", context
            )
            text_email = strip_tags(html_email)

            # Create the email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_email,
                from_email=from_email,
                to=recipient_list,
            )
            email.attach_alternative(html_email, "text/html")

            # Send the email
            email.send()

        # Except
        except Exception as e:
            # Log the error
            logger.error(
                f"Failed to send issue assignment email for issue '{self.title}': {e}"
            )
