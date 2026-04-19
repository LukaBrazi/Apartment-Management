# Imports
from apps.apartments.models import Apartment, Building, Entrance, ResidentialComplex, Unit
from rest_framework import serializers


# Apartment Serializer (legacy — kept for backward compat)
class ApartmentSerializer(serializers.ModelSerializer):
    tenant = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Apartment
        exclude = ("pkid", "updated_at")


# ── PR-3 compat shim ───────────────────────────────────────────────────────
#
# The client (Next.js RTK Query) reads ``profile.apartment`` and
# ``/apartments/my-apartment/`` as an Apartment-shaped object:
#
#     {"id": UUID, "created_at": iso8601, "unit_number": str,
#      "building": str, "floor": int}
#
# After PR-3 the source of truth is ``Unit`` + ``Profile.unit``; the
# legacy ``Apartment`` row may disappear in PR-7.  This helper renders
# a ``Unit`` in the legacy Apartment JSON shape so the frontend contract
# stays byte-identical until PR-4 migrates off it.
#
# ``tenant`` is intentionally omitted because ``ApartmentSerializer``
# declares ``tenant = HiddenField`` — the legacy wire format has no
# tenant key.  ``_apartment_fields`` below is the authoritative key set.
_APARTMENT_FIELDS = ("id", "created_at", "unit_number", "building", "floor")


def unit_as_legacy_apartment(unit: Unit, *, tenant_id=None) -> dict:
    """Return a dict that matches ApartmentSerializer's output shape.

    ``tenant_id`` is accepted for call-site documentation only — the
    legacy JSON has no tenant key — so callers don't have to branch on
    the shim vs. the real serializer.
    """
    del tenant_id  # intentionally unused; see docstring

    legacy_apt = getattr(unit, "apartment", None)
    # Prefer the legacy Apartment's UUID so existing frontend caches
    # stay hot during the transition; fall back to the Unit's UUID
    # once the Apartment row is gone (PR-7).
    primary_id = legacy_apt.id if legacy_apt is not None else unit.id

    building_name = ""
    if unit.entrance_id:
        building_name = unit.entrance.building.name

    return {
        "id": str(primary_id),
        "created_at": unit.created_at.isoformat() if unit.created_at else None,
        "unit_number": unit.number,
        "building": building_name,
        "floor": unit.floor,
    }


# ── New domain serializers ─────────────────────────────────────────────────

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
