# Imports
import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

# Get the user model
User = get_user_model()


# TimeStampedModel
class TimeStampedModel(models.Model):
    """Time-Stamped Model

    This class is used to add time-stamp fields to the models.

    Extends:
        models.Model

    Attributes:
        pkid (models.BigAutoField): The primary key of the model.
        id (models.UUIDField): The UUID of the model.
        created_at (models.DateTimeField): The timestamp when the model was created.
        updated_at (models.DateTimeField): The timestamp when the model was updated.

    Meta Class:
        abstract (bool): Whether the model is abstract or not.
        ordering (list): The default ordering.
    """

    # Attributes
    pkid = models.BigAutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    # Meta Class
    class Meta:
        """Meta Class

        Attributes:
            abstract (bool): Whether the model is abstract or not.
            ordering (list): The default ordering.
        """

        # Attributes
        abstract = True
        ordering = ["-created_at", "-updated_at"]


# ContentView Model
class ContentView(TimeStampedModel):
    """Content View Model

    This class is used to represent a view of a content object.

    Extends:
        TimeStampedModel

    Attributes:
        content_type (ForeignKey): The content type of the object.
        object_id (PositiveIntegerField): The object ID.
        content_object (GenericForeignKey): The content object.
        user (ForeignKey): The user who viewed the content.
        viewer_ip (GenericIPAddressField): The IP address of the viewer.
        last_viewed (DateTimeField): The timestamp when the content was last viewed.

    Meta Class:
        verbose_name (str): The human-readable name of the model.
        verbose_name_plural (str): The human-readable plural name of the model.
        unique_together (list): The unique constraints of the model.
        ordering (list): The default ordering.

    Methods:
        __str__(): Return the string representation of the model.
    """

    # Attributes
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, verbose_name=_("Content Type")
    )
    object_id = models.PositiveIntegerField(verbose_name=_("Object ID"))
    content_object = GenericForeignKey("content_type", "object_id")
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_views",
        verbose_name=_("User"),
    )
    viewer_ip = models.GenericIPAddressField(
        null=True, blank=True, verbose_name=_("Viewer IP")
    )
    last_viewed = models.DateTimeField(auto_now=True, verbose_name=_("Last Viewed At"))

    # Meta Class
    class Meta:
        """Meta Class

        Attributes:
            verbose_name (str): The human-readable name of the model.
            verbose_name_plural (str): The human-readable plural name of the model.
            unique_together (list): The unique constraints of the model.
            ordering (list): The default ordering.
        """

        # Attributes
        verbose_name = _("Content View")
        verbose_name_plural = _("Content Views")
        unique_together = ["content_type", "object_id", "user", "viewer_ip"]
        ordering = ["-last_viewed"]

    # String Representation
    def __str__(self) -> str:
        """Return the string representation of the model.

        Returns:
            str: The string representation of the model.
        """

        # Return the string representation
        return (
            f"{self.content_object} viewed by {self.user.full_name or self.viewer_ip}"
        )


# ── GDPR: ConsentLog ──────────────────────────────────────────────────────────

class ConsentLog(models.Model):
    """ConsentLog

    GDPR Art. 7 — Records each time a user gives or withdraws consent
    for a specific purpose (e.g. marketing emails, analytics tracking).

    Immutable: records are never updated, only appended.

    Attributes:
        user (ForeignKey): The user who gave/withdrew consent.
        purpose (str): A short machine-readable key (e.g. "marketing", "analytics").
        given (bool): True = consent given, False = consent withdrawn.
        ip_address (str): IP address at time of consent action.
        user_agent (str): Browser UA string at time of consent action.
        timestamp (DateTimeField): When the action occurred (auto-set).
    """

    class Purpose(models.TextChoices):
        MARKETING = ("marketing", _("Marketing emails"))
        ANALYTICS = ("analytics", _("Usage analytics"))
        NOTIFICATIONS = ("notifications", _("Push notifications"))
        TERMS = ("terms", _("Terms of service"))

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consent_logs",
        verbose_name=_("User"),
    )
    purpose = models.CharField(
        _("Purpose"),
        max_length=50,
        choices=Purpose.choices,
        db_index=True,
    )
    given = models.BooleanField(
        _("Consent Given"),
        help_text=_("True = consent given, False = consent withdrawn."),
    )
    ip_address = models.GenericIPAddressField(
        _("IP Address"), null=True, blank=True
    )
    user_agent = models.TextField(_("User Agent"), blank=True, default="")
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Consent Log")
        verbose_name_plural = _("Consent Logs")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "purpose"], name="consent_user_purpose_idx"),
            models.Index(fields=["purpose", "timestamp"], name="consent_purpose_ts_idx"),
        ]

    def __str__(self) -> str:
        action = "gave" if self.given else "withdrew"
        return f"{self.user} {action} consent for '{self.purpose}' at {self.timestamp}"


# ── GDPR: GDPRAuditLog ────────────────────────────────────────────────────────

class GDPRAuditLog(models.Model):
    """GDPRAuditLog

    Immutable audit trail for all GDPR-related actions performed on or by a user.
    Used for accountability (Art. 5(2) GDPR) and DPO auditing.

    Events logged:
    - DATA_EXPORT: user requested data export
    - ERASURE_REQUEST: user requested erasure
    - ACCOUNT_ANONYMIZED: account was pseudonymized
    - CONSENT_GIVEN / CONSENT_WITHDRAWN: consent changes
    - ADMIN_ACCESS: staff accessed user data

    Attributes:
        actor (ForeignKey): Who performed the action (may be system/None).
        subject (ForeignKey): Whose data was affected.
        event (str): Event type (choices from EventType).
        detail (str): Optional free-text detail.
        ip_address (str): IP of actor.
        timestamp (DateTimeField): When the action occurred (auto-set).
    """

    class EventType(models.TextChoices):
        DATA_EXPORT = ("data_export", _("Data Export Requested"))
        ERASURE_REQUEST = ("erasure_request", _("Erasure Requested"))
        ACCOUNT_ANONYMIZED = ("account_anonymized", _("Account Anonymized"))
        CONSENT_GIVEN = ("consent_given", _("Consent Given"))
        CONSENT_WITHDRAWN = ("consent_withdrawn", _("Consent Withdrawn"))
        ADMIN_ACCESS = ("admin_access", _("Admin Data Access"))
        PASSWORD_RESET = ("password_reset", _("Password Reset"))
        LOGIN = ("login", _("Login"))

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gdpr_actions_performed",
        verbose_name=_("Actor"),
    )
    subject = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gdpr_events",
        verbose_name=_("Subject User"),
    )
    event = models.CharField(
        _("Event"),
        max_length=30,
        choices=EventType.choices,
        db_index=True,
    )
    detail = models.TextField(_("Detail"), blank=True, default="")
    ip_address = models.GenericIPAddressField(
        _("IP Address"), null=True, blank=True
    )
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("GDPR Audit Log")
        verbose_name_plural = _("GDPR Audit Logs")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["subject", "event"], name="gdpr_subject_event_idx"),
            models.Index(fields=["event", "timestamp"], name="gdpr_event_ts_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.event}] actor={self.actor} subject={self.subject} @ {self.timestamp}"

    @classmethod
    def log(
        cls,
        event: str,
        subject=None,
        actor=None,
        detail: str = "",
        ip_address: str = None,
    ) -> "GDPRAuditLog":
        """Convenience method to create an audit log entry.

        Args:
            event (str): One of EventType choices.
            subject: User whose data is affected.
            actor: User performing the action (can be same as subject or staff).
            detail (str): Optional context.
            ip_address (str): IP of actor.

        Returns:
            GDPRAuditLog: The created entry.
        """
        return cls.objects.create(
            event=event,
            subject=subject,
            actor=actor,
            detail=detail,
            ip_address=ip_address,
        )
