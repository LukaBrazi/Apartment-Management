# Imports
from apps.apartments.models import Building, Entrance, Unit
from rest_framework import serializers


# PR-7 deleted ``ApartmentSerializer`` and ``unit_as_legacy_apartment``.
# PR-8 deleted ``ResidentialComplexSerializer`` along with the
# ``ResidentialComplex`` model — buildings now expose
# ``organization_name`` instead of ``complex_name``.


# ── Domain serializers ─────────────────────────────────────────────────────


class BuildingSerializer(serializers.ModelSerializer):
    pkid = serializers.IntegerField(read_only=True)
    organization_name = serializers.ReadOnlyField(source="organization.name")

    class Meta:
        model = Building
        fields = [
            "pkid",
            "id",
            "name",
            "address",
            "city",
            "is_active",
            "organization_name",
            "created_at",
        ]


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
