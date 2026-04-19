# Imports
from typing import Any

from apps.apartments.models import Apartment, Building, Entrance, Unit
from apps.apartments.serializers import (
    ApartmentSerializer,
    BuildingSerializer,
    EntranceSerializer,
    UnitSerializer,
    unit_as_legacy_apartment,
)
from apps.common.renderers import GenericJSONRenderer
from apps.profiles.models import Profile
from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response


# ApartmentCreateAPIView Class
class ApartmentCreateAPIView(generics.CreateAPIView):
    """ApartmentCreateAPIView

    ApartmentCreateAPIView class is used to create an apartment.

    Extends:
        generics.CreateAPIView

    Attributes:
        queryset (QuerySet): The queryset of apartments.
        serializer_class (ApartmentSerializer): The apartment serializer class.
        renderer_classes (list): The list of renderer classes.
        object_label (str): The object label.

    Methods:
        create: Method to create an apartment.

    Raises:
        Http403: The HTTP 403 Forbidden status code.
    """

    # Attributes
    queryset = Apartment.objects.all()
    serializer_class = ApartmentSerializer
    renderer_classes = (GenericJSONRenderer,)
    object_label = "apartment"

    # Method to create an apartment
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Method to create an apartment.

        Args:
            request (Request): The request object.
            *args (Any): Variable length argument list.
            **kwargs (Any): Arbitrary keyword arguments.

        Returns:
            Response: The response object.

        Raises:
            Http403: The HTTP 403 Forbidden status code.
        """

        # Get the user
        user = request.user

        # Check if the user is authorized to create an apartment
        if user.is_superuser or (
            hasattr(user, "profile")
            and user.profile.occupation
            in (Profile.Occupation.TENANT, Profile.Occupation.GUARD)
        ):
            # Create the apartment
            return super().create(request, *args, **kwargs)

        # Return the error response
        return Response(
            {"error": "You are not authorized to create an apartment."},
            status=status.HTTP_403_FORBIDDEN,
        )


# ApartmentDetailAPIView Class
class ApartmentListAPIView(generics.ListAPIView):
    """ApartmentListAPIView

    ApartmentListAPIView class is used to list the apartments.

    Extends:
        generics.ListAPIView

    Attributes:
        serializer_class (ApartmentSerializer): The apartment serializer class.
        renderer_classes (list): The list of renderer classes.
        object_label (str): The object label.

    Methods:
        get_queryset: Method to get the queryset.

    Raises:
        Http403: The HTTP 403 Forbidden status code.
    """

    # Attributes
    serializer_class = ApartmentSerializer
    renderer_classes = (GenericJSONRenderer,)
    object_label = "apartments"

    # Method to get the queryset
    def get_queryset(self):
        """Method to get the queryset.

        Returns:
            QuerySet: The queryset of apartments.
        """

        # Return the queryset
        return self.request.user.apartment.all()


class MyApartmentAPIView(generics.RetrieveAPIView):
    """Return the current tenant's first (and usually only) apartment.

    GET /apartments/my-apartment/
    → Renderer wraps as {"status_code": 200, "apartment": {...}}
    → null/empty when user has no apartment

    PR-3 cutover: prefers ``request.user.profile.unit`` (new canonical
    source) rendered in the legacy Apartment JSON shape via
    ``unit_as_legacy_apartment``.  Falls back to ``request.user.apartment
    .first()`` only for rows still unbridged after PR-1 (audit flags
    these).  JSON shape is byte-compatible with the previous contract
    so PR-4 can migrate the frontend independently.
    """

    serializer_class = ApartmentSerializer
    renderer_classes = (GenericJSONRenderer,)
    object_label = "apartment"

    def get_object(self):
        # Preferred: Profile.unit set by PR-1 backfill.
        profile = getattr(self.request.user, "profile", None)
        if profile is not None and profile.unit_id:
            return profile.unit
        # Legacy fallback
        return self.request.user.apartment.first()

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        instance = self.get_object()
        if instance is None:
            # Renderer will produce {"status_code": 200, "apartment": {}}
            # Frontend transformResponse → {apartment: {}} → apartment.id = undefined
            return Response({}, status=status.HTTP_200_OK)
        if isinstance(instance, Unit):
            data = unit_as_legacy_apartment(instance, tenant_id=request.user.id)
            return Response(data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BuildingListAPIView(generics.ListAPIView):
    """List active buildings scoped to the current ЖК.

    If SiteSettings.current_complex is set, returns only buildings
    belonging to that complex. Otherwise falls back to all active buildings.
    """

    serializer_class = BuildingSerializer
    renderer_classes = (GenericJSONRenderer,)
    object_label = "buildings"
    pagination_class = None

    def get_queryset(self):
        from apps.site_settings.models import SiteSettings

        qs = Building.objects.filter(is_active=True)
        site = SiteSettings.get()
        if site.current_complex_id:
            qs = qs.filter(complex=site.current_complex)
        return qs.select_related("complex")


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
