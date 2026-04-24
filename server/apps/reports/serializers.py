# Imports
from apps.reports.models import Report
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class ReportSerializer(serializers.ModelSerializer):
    """Create a new report.

    ``reported_person_name`` is required — any free text describing the person
    (name, apartment number, role, etc.).  ``reported_user_username`` is
    optional: if provided and the username exists in the system, the FK
    ``reported_user`` is populated automatically; if the username is unknown
    the field is simply ignored and only the free-text name is stored.
    """

    # Optional username lookup — not validated against DB; best-effort only.
    reported_user_username = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        default="",
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "title",
            "description",
            "reported_person_name",
            "reported_user_username",
            "created_at",
        ]

    def create(self, validated_data: dict) -> Report:
        username = validated_data.pop("reported_user_username", "").strip()

        # Best-effort FK lookup — failure is not an error.
        reported_user = None
        if username:
            reported_user = User.objects.filter(username=username).first()

        report = Report.objects.create(
            reported_user=reported_user,
            **validated_data,
        )
        return report


class ReportListSerializer(serializers.ModelSerializer):
    """Read-only serializer for listing reports (staff/admin view)."""

    reported_user_username = serializers.CharField(
        source="reported_user.username", read_only=True
    )
    reported_user_full_name = serializers.CharField(
        source="reported_user.full_name", read_only=True
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "created_at",
            "title",
            "description",
            "reported_person_name",
            "reported_user_username",
            "reported_user_full_name",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "reported_person_name",
            "reported_user_username",
            "reported_user_full_name",
        ]
