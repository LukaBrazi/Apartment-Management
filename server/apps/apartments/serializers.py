# Imports
from apps.apartments.models import Building, Entrance, ResidentialComplex, Unit
from rest_framework import serializers


# PR-7 deleted ``ApartmentSerializer`` and ``unit_as_legacy_apartment``.
# The last internal reader was ``ProfileSerializer.apartment`` which now
# builds its Unit-shaped payload inline.  The frontend migrated off the
# legacy Apartment wire format in PR-4.


# ── Domain serializers ─────────────────────────────────────────────────────

class ResidentialComplexSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResidentialComplex
        fields = ["pkid", "id", "name", "address", "city", "description"]


class BuildingSerializer(serializers.ModelSerializer):
    pkid = serializers.IntegerField(read_only=True)
    complex_name = serializers.ReadOnlyField(source="complex.name")

    class Meta:
        model = Building
        fields = ["pkid", "id", "name", "address", "city", "is_active", "complex_name", "created_at"]


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

    class Meta:
        model = Unit
        fields = [
            "id",
            "unit_id",
            "number",
            "floor",
            "entrance",
            "entrance_name",
            "building_name",
            "created_at",
        ]
