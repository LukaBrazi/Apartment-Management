# Imports
from apps.apartments.models import Building, Entrance, Unit
from apps.apartments.serializers import (
    BuildingSerializer,
    EntranceSerializer,
    UnitSerializer,
)
from apps.common.renderers import GenericJSONRenderer
from rest_framework import generics
from rest_framework.permissions import IsAdminUser, IsAuthenticated


def _scope_buildings_to_user(user):
    """Return a ``Building`` queryset scoped to the caller's organisations.

    This is the single source of truth for cross-org isolation in the
    apartments app.  Three branches:

    * unauthenticated → empty queryset (defence-in-depth; views also
      enforce ``IsAuthenticated``);
    * superuser → all active buildings;
    * regular user → buildings whose ``organization`` is one of the user's
      active memberships.

    Buildings without an ``organization`` FK (legacy / fixtures) are
    excluded for non-superusers — there is no safe tenant they could
    belong to.
    """
    from apps.organizations.utils import get_user_organizations

    base = Building.objects.filter(is_active=True).select_related("organization")
    if not user.is_authenticated:
        return base.none()
    if user.is_superuser:
        return base
    return base.filter(organization__in=get_user_organizations(user))


# PR-6: ``ApartmentCreateAPIView``, ``ApartmentListAPIView`` and
# ``MyApartmentAPIView`` were removed — the tenant-facing apartment
# flow is gone now that Unit membership is admin-managed and the
# Profile endpoint exposes the canonical Unit/Building fields.  The
# legacy Apartment model itself is dropped in PR-7.


class BuildingListAPIView(generics.ListAPIView):
    """List buildings visible to the caller.

    Multi-tenant scoping: only buildings belonging to organizations the
    caller is an active member of are returned.  Superusers see all
    active buildings.  Previously this endpoint returned every active
    building regardless of organization, which leaked cross-tenant data
    (building names, addresses, organization metadata) to any
    authenticated user.

    PR-8: previously this endpoint filtered by ``SiteSettings.current_complex``;
    that FK and the ``ResidentialComplex`` model were removed.
    """

    serializer_class = BuildingSerializer
    permission_classes = [IsAuthenticated]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "buildings"
    pagination_class = None

    def get_queryset(self):
        return _scope_buildings_to_user(self.request.user)


class EntranceListAPIView(generics.ListAPIView):
    """List entrances for a given building.

    Multi-tenant scoping: the parent building must itself be visible to
    the caller via ``_scope_buildings_to_user``.  If the building is not
    in the caller's organisations, the endpoint returns an empty list
    (rather than 404) — indistinguishable from a building that simply
    has no entrances, which avoids leaking existence information
    across tenants.
    """

    serializer_class = EntranceSerializer
    permission_classes = [IsAuthenticated]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "entrances"
    pagination_class = None

    def get_queryset(self):
        building_id = self.kwargs.get("building_id")
        allowed_buildings = _scope_buildings_to_user(self.request.user)
        # ``building_id`` comes from the URL as a UUID (see
        # ``<uuid:building_id>`` in ``apps.apartments.urls``), so filter
        # against the ``Building.id`` UUID field, not the integer FK
        # ``Entrance.building_id`` column.
        return (
            Entrance.objects.filter(
                building__id=building_id,
                building__in=allowed_buildings,
            ).order_by("name")
        )


class UnitsByBuildingListAPIView(generics.ListAPIView):
    """List all units for a given building (across all entrances).

    Multi-tenant scoping: same rules as ``EntranceListAPIView`` — if the
    building isn't in the caller's organisations, the list is empty.
    """

    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "units"
    pagination_class = None

    def get_queryset(self):
        building_id = self.kwargs.get("building_id")
        allowed_buildings = _scope_buildings_to_user(self.request.user)
        # See ``EntranceListAPIView.get_queryset`` for the UUID caveat —
        # we filter on ``Building.id`` (UUID), not the integer FK column.
        return (
            Unit.objects.filter(
                entrance__building__id=building_id,
                entrance__building__in=allowed_buildings,
            )
            .select_related("entrance", "entrance__building")
            .order_by("entrance__name", "number")
        )


class AdminBuildingListCreateAPIView(generics.ListCreateAPIView):
    """Admin list/create buildings — scoped to the staff caller's orgs.

    ``IsAdminUser`` only checks Django's global ``is_staff`` flag, which
    is not the same thing as being an admin of your organisation.  The
    queryset is scoped to the caller's organisations so that a staff
    user from org A cannot enumerate org B's buildings.  Superusers see
    every building.
    """

    serializer_class = BuildingSerializer
    permission_classes = [IsAdminUser]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "buildings"
    pagination_class = None

    def get_queryset(self):
        # Note: ``_scope_buildings_to_user`` filters ``is_active=True``.
        # For admin views we want inactive buildings too so staff can
        # re-enable them — hence the rebuild below instead of reuse.
        from apps.organizations.utils import get_user_organizations

        base = Building.objects.select_related("organization")
        user = self.request.user
        if user.is_superuser:
            return base
        return base.filter(organization__in=get_user_organizations(user))


class BuildingCreateAPIView(generics.CreateAPIView):
    serializer_class = BuildingSerializer
    permission_classes = [IsAdminUser]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "building"


class BuildingUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Admin retrieve/update/destroy — scoped to the staff caller's orgs.

    Same rationale as ``AdminBuildingListCreateAPIView``: scoping the
    queryset prevents cross-tenant update/delete via ``pkid``
    enumeration.
    """

    serializer_class = BuildingSerializer
    permission_classes = [IsAdminUser]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "building"
    lookup_field = "pkid"

    def get_queryset(self):
        from apps.organizations.utils import get_user_organizations

        base = Building.objects.select_related("organization")
        user = self.request.user
        if user.is_superuser:
            return base
        return base.filter(organization__in=get_user_organizations(user))
