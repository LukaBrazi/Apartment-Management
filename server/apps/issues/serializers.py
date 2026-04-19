# Imports
import logging
from typing import Dict

from apps.common.models import ContentView
from apps.issues.emails import send_resolution_email
from apps.issues.models import Issue
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework import serializers

User = get_user_model()

# Get the logger
logger = logging.getLogger(__name__)


# Issue Serializer
class IssueSerializer(serializers.ModelSerializer):
    """Issue serializer

    This class is used to serialize an issue.

    Extends:
        serializers.ModelSerializer

    Attributes:
        apartment_unit (ReadOnlyField): The unit number of the apartment.
        reported_by (ReadOnlyField): The user who reported the issue.
        assigned_to (ReadOnlyField): The user assigned to the issue.
        view_count (SerializerMethodField): The number of views the issue has.

    Meta Class:
        model (Issue): The issue model.
        fields (list): The fields to include in the serialized data.

    Methods:
        get_view_count(obj: Issue) -> int: Get the number
    """

    # Attributes
    unit_number = serializers.ReadOnlyField(source="unit.number")
    unit_id = serializers.UUIDField(source="unit.id", read_only=True)
    building_name = serializers.ReadOnlyField(source="unit.entrance.building.name")
    reported_by = serializers.ReadOnlyField(source="reported_by.full_name")
    assigned_to = serializers.ReadOnlyField(source="assigned_to.full_name")
    category_name = serializers.ReadOnlyField(source="category.name")
    due_at = serializers.DateTimeField(read_only=True)
    is_overdue = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()

    # Meta Class
    class Meta:
        model = Issue
        fields = [
            "id",
            "unit_id",
            "unit_number",
            "building_name",
            "reported_by",
            "assigned_to",
            "title",
            "description",
            "status",
            "priority",
            "category_name",
            "due_at",
            "is_overdue",
            "view_count",
        ]

    def get_is_overdue(self, obj):
        return obj.is_overdue

    # Method to get the view count
    def get_view_count(self, obj: Issue) -> int:
        """Get the number of views the issue has.

        Uses pre-annotated `view_count` if available (set by list views),
        otherwise falls back to a direct query (used on detail views).

        Args:
            obj (Issue): The issue.

        Returns:
            int: The number of views the issue has.
        """
        if hasattr(obj, "view_count"):
            return obj.view_count

        # Fallback for detail view (single query, acceptable)
        content_type = ContentType.objects.get_for_model(obj)
        return ContentView.objects.filter(
            content_type=content_type, object_id=obj.pkid
        ).count()


# Issue Create Serializer (tenant-facing — no status/priority, has location_note)
class IssueCreateSerializer(serializers.ModelSerializer):
    """Minimal serializer for tenant issue creation.

    Tenants only provide title, description, and an optional location note.
    Status and priority are set by the admin/dispatcher.
    The location_note is write-only and gets prepended to the description.
    """

    location_note = serializers.CharField(
        required=False, allow_blank=True, write_only=True, default=""
    )

    class Meta:
        model = Issue
        fields = ["title", "description", "location_note"]

    def validate(self, attrs):
        location_note = attrs.pop("location_note", "")
        if location_note:
            attrs["description"] = f"📍 Місце: {location_note}\n\n{attrs['description']}"
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and not validated_data.get("organization"):
            from apps.organizations.utils import get_user_primary_organization
            org = get_user_primary_organization(request.user)
            if org:  # only set if user has an org
                validated_data["organization"] = org
        return super().create(validated_data)


# Issue Status Update Serializer
class IssueStatusUpdateSerializer(serializers.ModelSerializer):
    """Issue status update serializer

    This class is used to serialize the status update of an issue.

    Extends:
        serializers.ModelSerializer

    Attributes:
        apartment (ReadOnlyField): The unit number of the apartment.
        reported_by (ReadOnlyField): The user who reported the issue.
        resolved_by (ReadOnlyField): The user who resolved the issue.

    Meta Class:
        model (Issue): The issue model.
        fields (list): The fields to include in the serialized data.

    Methods:
        update(instance: Issue, validated_data: Dict) -> Issue: Update the issue.

    Raises:
        Exception: If the email sending fails.
    """

    # Attributes
    unit_number = serializers.ReadOnlyField(source="unit.number")
    reported_by = serializers.ReadOnlyField(source="reported_by.full_name")
    resolved_by = serializers.ReadOnlyField(source="assigned_to.full_name")

    # Meta Class
    class Meta:
        model = Issue
        fields = [
            "title",
            "description",
            "unit_number",
            "reported_by",
            "status",
            "resolved_by",
            "resolved_on",
        ]

    # Method to update the issue
    def update(self, instance: Issue, validated_data: Dict) -> Issue:
        """Update the issue.

        Args:
            instance (Issue): The issue instance.
            validated_data (dict): The validated data.

        Returns:
            Issue: The updated issue.

        Raises:
            Exception: If the email sending fails.
        """

        # Check if the status transitioned to DONE
        status_was_resolved = (
            validated_data.get("status") == Issue.IssueStatus.DONE
            and instance.status != Issue.IssueStatus.DONE
        )

        # Update the issue
        instance = super().update(instance, validated_data)

        # If the status was resolved
        if status_was_resolved:
            # Update the resolved on date
            instance.resolved_on = timezone.now().date()

            # Save the issue
            instance.save()

            # Send the resolution email
            send_resolution_email(instance)

        # Return the updated issue
        return instance


# IssueAdminUpdateSerializer
class IssueAdminUpdateSerializer(serializers.ModelSerializer):
    """Admin issue update — allows setting status (direct), priority, and assignee."""

    assigned_to_username = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        source="assigned_to",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Issue
        fields = ["status", "priority", "assigned_to_username"]

    def validate_assigned_to_username(self, user):
        if user is not None:
            from apps.profiles.models import Profile

            try:
                if user.profile.occupation == Profile.Occupation.TENANT:
                    raise serializers.ValidationError(
                        "Мешканця не можна призначити виконавцем заявки."
                    )
            except Profile.DoesNotExist:
                pass
        return user
