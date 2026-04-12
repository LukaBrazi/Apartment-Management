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
        unit = (
            Unit.objects.filter(apartment__tenant=user)
            .select_related("entrance__building")
            .first()
        )
        return VehiclePass.objects.create(tenant=user, unit=unit, **validated_data)


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
