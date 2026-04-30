# Imports
import logging
from typing import Dict

from apps.common.models import ContentView
from apps.issues.emails import send_resolution_email
from apps.issues.models import Issue, IssueReview
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
    # PR-15: ``building_address`` + ``city`` are exposed only to the
    # reporter, the assignee, and staff.  Other same-org tenants (if
    # they manage to retrieve the issue) get ``None`` so the exact
    # apartment address isn't broadcast.  ``building_name`` is
    # considered low-sensitivity and stays public within the org.
    building_address = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
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
            "building_address",
            "city",
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

    def _can_see_address(self, obj: Issue) -> bool:
        """Reporter / assignee / staff are allowed to see the full address."""
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        if user.is_staff or user.is_superuser:
            return True
        return user == obj.reported_by or user == obj.assigned_to

    def get_building_address(self, obj: Issue):
        if not self._can_see_address(obj):
            return None
        unit = getattr(obj, "unit", None)
        entrance = getattr(unit, "entrance", None) if unit else None
        building = getattr(entrance, "building", None) if entrance else None
        return getattr(building, "address", None)

    def get_city(self, obj: Issue):
        if not self._can_see_address(obj):
            return None
        unit = getattr(obj, "unit", None)
        entrance = getattr(unit, "entrance", None) if unit else None
        building = getattr(entrance, "building", None) if entrance else None
        return getattr(building, "city", None)

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
            # PR-15 fallback: superusers and other edge-case reporters
            # without a direct membership still produce issues that need
            # an org pin (otherwise tenants don't see them in their list,
            # see Bug 1 in PR-14).  Derive the org from the resolved
            # ``unit`` chain when membership lookup returns None.
            if not org:
                unit = validated_data.get("unit")
                if unit is not None:
                    org = (
                        getattr(unit, "organization", None)
                        or getattr(getattr(unit, "entrance", None), "organization", None)
                        or getattr(
                            getattr(getattr(unit, "entrance", None), "building", None),
                            "organization",
                            None,
                        )
                    )
            if org:  # only set if we resolved an org
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


class ReviewableIssueSerializer(serializers.ModelSerializer):
    """Read-only serializer for the tenant's "rate my worker" list.

    Returns done issues that have an assigned worker, annotated with
    ``my_review`` — the current user's review for this issue (null if
    they haven't rated yet).  The request context is required so the
    serializer knows which user to look up.
    """

    assigned_to_name = serializers.ReadOnlyField(source="assigned_to.get_full_name")
    assigned_to_username = serializers.ReadOnlyField(source="assigned_to.username")
    my_review = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            "id",
            "title",
            "assigned_to_name",
            "assigned_to_username",
            "resolved_on",
            "created_at",
            "my_review",
        ]

    def get_my_review(self, obj):
        request = self.context.get("request")
        if request is None:
            return None
        review = IssueReview.objects.filter(
            issue=obj, reviewer=request.user
        ).first()
        if review is None:
            return None
        return {
            "id": str(review.id),
            "rating": review.rating,
            "comment": review.comment or "",
        }


class IssueReviewSerializer(serializers.ModelSerializer):
    """Serializer for creating and reading IssueReview objects.

    On write:  accepts ``rating`` (1–5) and optional ``comment``.
    On read:   returns both fields plus reviewer/reviewee identifiers.
    """

    reviewer_name = serializers.CharField(
        source="reviewer.get_full_name", read_only=True
    )
    reviewee_name = serializers.CharField(
        source="reviewee.get_full_name", read_only=True
    )

    class Meta:
        model = IssueReview
        fields = [
            "id",
            "issue",
            "reviewer",
            "reviewer_name",
            "reviewee",
            "reviewee_name",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "issue",
            "reviewer",
            "reviewer_name",
            "reviewee",
            "reviewee_name",
            "created_at",
        ]
