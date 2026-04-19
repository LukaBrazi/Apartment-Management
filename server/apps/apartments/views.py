# Imports
from apps.apartments.models import Building, Entrance, Unit
from apps.apartments.serializers import (
    BuildingSerializer,
    EntranceSerializer,
    UnitSerializer,
)
from apps.common.renderers import GenericJSONRenderer
from rest_framework import generics
from rest_framework.permissions import IsAdminUser


# PR-6: ``ApartmentCreateAPIView``, ``ApartmentListAPIView`` and
# ``MyApartmentAPIView`` were removed — the tenant-facing apartment
# flow is gone now that Unit membership is admin-managed and the
# Profile endpoint exposes the canonical Unit/Building fields.  The
# legacy Apartment model itself is dropped in PR-7.


class BuildingListAPIView(generics.ListAPIView):
    """List active buildings.

    PR-8: previously this endpoint filtered by ``SiteSettings.current_complex``;
    that FK and the ``ResidentialComplex`` model were removed.  Buildings
    are now scoped to ``Organization`` — the organization-level filtering
    for authenticated users happens at the app boundary via
    ``get_user_organizations``; this public list returns every active
    building, which is fine because there is no sensitive data in the
    Building payload itself.
    """

    serializer_class = BuildingSerializer
    renderer_classes = (GenericJSONRenderer,)
    object_label = "buildings"
    pagination_class = None

    def get_queryset(self):
        return (
            Building.objects.filter(is_active=True)
            .select_related("organization")
        )


class EntranceListAPIView(generics.ListAPIView):
    """List entrances for a given building."""

    serializer_class = EntranceSerializer
    renderer_classes = (GenericJSONRenderer,)
    object_label = "entrances"
    pagination_class = None

    def get_queryset(self):
        building_id = self.kwargs.get("building_id")
        return Entrance.objects.filter(building_id=building_id).order_by("name")


class UnitsByBuildingListAPIView(generics.ListAPIView):
    """List all units for a given building (across all entrances)."""

    serializer_class = UnitSerializer
    renderer_classes = (GenericJSONRenderer,)
    object_label = "units"
    pagination_class = None

    def get_queryset(self):
        building_id = self.kwargs.get("building_id")
        return (
            Unit.objects.filter(entrance__building_id=building_id)
            .select_related("entrance", "entrance__building")
            .order_by("entrance__name", "number")
        )


class AdminBuildingListCreateAPIView(generics.ListCreateAPIView):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    permission_classes = [IsAdminUser]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "buildings"
    pagination_class = None


class BuildingCreateAPIView(generics.CreateAPIView):
    serializer_class = BuildingSerializer
    permission_classes = [IsAdminUser]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "building"


class BuildingUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    permission_classes = [IsAdminUser]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "building"
    lookup_field = "pkid"
