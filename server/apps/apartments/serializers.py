# Imports
from apps.apartments.models import Apartment, Building, Entrance, Unit
from rest_framework import serializers


# Apartment Serializer (legacy — kept for backward compat)
class ApartmentSerializer(serializers.ModelSerializer):
    tenant = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Apartment
        exclude = ("pkid", "updated_at")


# ── New domain serializers ─────────────────────────────────────────────────

class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = ["id", "name", "address", "city", "is_active", "created_at"]


class EntranceSerializer(serializers.ModelSerializer):
    building_name = serializers.ReadOnlyField(source="building.name")

    class Meta:
        model = Entrance
        fields = ["id", "building", "building_name", "name", "created_at"]


class UnitSerializer(serializers.ModelSerializer):
    entrance_name = serializers.ReadOnlyField(source="entrance.name")
    building_name = serializers.ReadOnlyField(source="entrance.building.name")
    # Alias: unit_id == id (stable API name going forward)
    unit_id = serializers.ReadOnlyField(source="id")
    # Backward-compat alias
    apartment_id = serializers.ReadOnlyField(source="apartment.id")

    class Meta:
        model = Unit
        fields = [
            "id",
            "unit_id",
            "apartment_id",
            "number",
            "floor",
            "entrance",
            "entrance_name",
            "building_name",
            "created_at",
        ]
