from datetime import date

from apps.apartments.models import Unit
from apps.passes.models import VehiclePass
from rest_framework import serializers


class VehiclePassCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehiclePass
        fields = ["id", "car_number", "comment", "visit_date"]

    def validate_visit_date(self, value):
        if value < date.today():
            raise serializers.ValidationError(
                "Дата відвідування не може бути в минулому."
            )
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        # PR-11: resolve the resident's unit via the primary
        # ``Residency`` — ``Profile.unit`` has been dropped.
        unit = None
        profile = getattr(user, "profile", None)
        primary = getattr(profile, "primary_unit", None) if profile is not None else None
        if primary is not None:
            unit = (
                Unit.objects.filter(pkid=primary.pk)
                .select_related("entrance__building")
                .first()
            )
        # Strict multi-tenant scoping: the pass MUST carry an organization
        # or the tenant's own ``/passes/my/`` list (filtered on
        # ``organization__in=get_user_organizations(user)``) will never
        # return it.  A Unit always belongs to exactly one Organization
        # (see ``Unit.save`` — org is auto-derived from the building), so
        # ``unit.organization`` is the authoritative source of truth here.
        # Only fall back to the membership lookup when the tenant has no
        # unit at all (``new1/new2@demo.com`` — "awaiting assignment").
        organization = validated_data.pop("organization", None)
        if organization is None and unit is not None:
            organization = unit.organization
        if organization is None:
            from apps.organizations.utils import get_user_primary_organization
            organization = get_user_primary_organization(user)
        return VehiclePass.objects.create(
            tenant=user, unit=unit, organization=organization, **validated_data,
        )


class VehiclePassSerializer(serializers.ModelSerializer):
    tenant_name = serializers.SerializerMethodField()
    tenant_username = serializers.ReadOnlyField(source="tenant.username")
    unit_label = serializers.SerializerMethodField()
    building_name = serializers.SerializerMethodField()
    closed_by_username = serializers.ReadOnlyField(source="closed_by.username")

    class Meta:
        model = VehiclePass
        fields = [
            "id",
            "tenant_name",
            "tenant_username",
            "unit_label",
            "building_name",
            "car_number",
            "comment",
            "visit_date",
            "status",
            "closed_by_username",
            "closed_at",
            "created_at",
        ]

    def get_tenant_name(self, obj):
        return obj.tenant.get_full_name() or obj.tenant.username

    def get_unit_label(self, obj):
        return str(obj.unit) if obj.unit else None

    def get_building_name(self, obj):
        if obj.unit and obj.unit.entrance:
            return obj.unit.entrance.building.name
        return None
