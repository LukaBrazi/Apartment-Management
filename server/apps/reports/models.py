# Imports
from apps.common.models import TimeStampedModel
from autoslug import AutoSlugField
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

# Get the user model
User = get_user_model()


# Report Model
class Report(TimeStampedModel):
    """Report

    Report class is used to represent a report in the database.

    Extends:
        TimeStampedModel

    Attributes:
        title (str): The title of the report.
        slug (AutoSlugField): The slug of the report.
        reported_by (ForeignKey): The user who reported the report.
        reported_user (ForeignKey): The user who was reported.
        description (str): The description of the report.

    Methods:
        __str__(): Return the string representation of the report.

    Meta Class:
        verbose_name (str): The human-readable name of the model.
        verbose_name_plural (str): The human-readable plural name of the model.
        ordering (list): The default ordering for the model.
    """

    # Attributes
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    slug = AutoSlugField(populate_from="title", unique=True, always_update=True)
    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_made",
        verbose_name=_("Reported by"),
    )
    reported_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_received",
        verbose_name=_("Reported user"),
    )
    reported_person_name = models.CharField(
        _("Reported person name"),
        max_length=255,
        blank=True,
        help_text=_(
            "Free-text name or description of the person being reported. "
            "Used when the reporter does not know the exact username."
        ),
    )
    description = models.TextField(verbose_name=_("Description"))
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="reports",
        null=True,
        blank=True,
        editable=False,
        help_text=_(
            "Organisation the report belongs to — auto-populated in "
            "``Report.save()`` from the reporter's primary "
            "OrganizationMembership.  May be null only when the "
            "reporter is a superuser without a membership; such rows "
            "are invisible to the multi-tenant admin/list views."
        ),
    )

    # String representation
    def __str__(self) -> str:
        """String Representation

        Returns:
            str: The string representation of the report.
        """

        # Return the string representation
        return f"Report by {self.reported_by.full_name} against {self.reported_user.full_name}"

    def save(self, *args, **kwargs) -> None:
        """Auto-populate ``organization`` from the reporter's primary membership."""
        if self.organization_id is None and self.reported_by_id is not None:
            from apps.organizations.utils import get_user_primary_organization

            self.organization = get_user_primary_organization(self.reported_by)
        super().save(*args, **kwargs)

    # Meta Class
    class Meta:
        """Meta Class

        Attributes:
            verbose_name (str): The human-readable name of the model.
            verbose_name_plural (str): The human-readable plural name of the model.
            ordering (list): The default ordering for the model.
        """

        # Attributes
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ["-created_at"]
