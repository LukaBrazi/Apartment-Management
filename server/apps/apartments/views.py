# Imports
from apps.apartments.models import Building, Entrance, Residency, Unit
from apps.apartments.serializers import (
    BuildingSerializer,
    EntranceDetailSerializer,
    EntranceSerializer,
    EntranceWriteSerializer,
    UnitSerializer,
)
from apps.common.renderers import GenericJSONRenderer
from django.db import IntegrityError, transaction
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


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


def _resolve_caller_organization(user):
    """Return the org that should own newly-created admin rows.

    Behaviour matrix:

    * superuser with at least one active org → that org (first);
    * superuser with no orgs (legacy ``AdminUserFactory`` test setup) →
      ``None`` — let the row be saved without ``organization`` so we
      don't break ~50 existing tests that lean on this fixture;
    * non-superuser staff with at least one active org → that org;
    * non-superuser staff with no orgs → ``ValidationError`` —
      otherwise the freshly-created row would be invisible to its
      creator (Bug 1: organization filter excludes ``NULL``).
    """
    from apps.organizations.utils import get_user_organizations

    orgs = get_user_organizations(user)
    org = orgs.first() if orgs.exists() else None
    if org is None and not user.is_superuser:
        raise serializers.ValidationError(
            "У адміна нема організації — створіть її в Django Admin спочатку"
        )
    return org


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

    PR-14 Bug 1 fix: ``perform_create`` now pins the new building's
    ``organization`` FK to the caller's first active org.  Without this
    the row was saved with ``organization=None`` and immediately
    disappeared from the same view's GET response (which filters by
    org membership).
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

    def perform_create(self, serializer):
        org = _resolve_caller_organization(self.request.user)
        serializer.save(organization=org)


class BuildingCreateAPIView(generics.CreateAPIView):
    """Legacy create endpoint — frontend currently posts here.

    Same Bug 1 fix is applied: pin ``organization`` from the caller's
    first active org so the row is visible to its creator.
    """

    serializer_class = BuildingSerializer
    permission_classes = [IsAdminUser]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "building"

    def perform_create(self, serializer):
        org = _resolve_caller_organization(self.request.user)
        serializer.save(organization=org)


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


# ── PR-14: admin entrance CRUD ──────────────────────────────────────────────


def _scope_admin_buildings(user):
    """Buildings visible to a staff caller — including inactive ones."""
    from apps.organizations.utils import get_user_organizations

    base = Building.objects.select_related("organization")
    if user.is_superuser:
        return base
    return base.filter(organization__in=get_user_organizations(user))


def _scope_admin_entrances(user):
    """Entrances scoped to the caller's orgs.

    Filter is on ``building__organization__in=...`` — NOT
    ``entrance.organization`` — because entrances created via legacy
    paths (or before the 0011 backfill) may carry ``organization=None``
    even though their parent building does not.
    """
    from apps.organizations.utils import get_user_organizations

    base = Entrance.objects.select_related("building", "building__organization")
    if user.is_superuser:
        return base
    return base.filter(
        building__organization__in=get_user_organizations(user),
    )


class AdminEntranceListCreateAPIView(generics.ListCreateAPIView):
    """List entrances of a building / create a new entrance under it.

    URL: ``/api/v1/apartments/buildings/<int:building_pkid>/entrances/``.
    Body for POST: ``{"name": "Б", "apartments_count": 12}``.
    """

    serializer_class = EntranceDetailSerializer
    permission_classes = [IsAdminUser]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "entrances"
    pagination_class = None

    def _get_building(self):
        building_pkid = self.kwargs["building_pkid"]
        try:
            return _scope_admin_buildings(self.request.user).get(pkid=building_pkid)
        except Building.DoesNotExist as exc:
            from rest_framework.exceptions import NotFound
            raise NotFound("Building not found") from exc

    def get_queryset(self):
        building = self._get_building()
        return (
            _scope_admin_entrances(self.request.user)
            .filter(building=building)
            .order_by("name")
        )

    def create(self, request, *args, **kwargs):
        building = self._get_building()
        write_serializer = EntranceWriteSerializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        name = write_serializer.validated_data["name"]
        apartments_count = write_serializer.validated_data["apartments_count"]

        if Entrance.objects.filter(building=building, name=name).exists():
            return Response(
                {"detail": f"Підʼїзд '{name}' вже існує у будинку."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Race-safety: between the .exists() pre-check and the create()
        # below another concurrent request can race in and grab the same
        # (building, name) tuple.  unique_together would then bubble up
        # IntegrityError → 500.  Wrap the atomic block and translate to
        # a clean 400 so the client sees the same message either path.
        try:
            with transaction.atomic():
                entrance = Entrance.objects.create(
                    building=building,
                    name=name,
                    organization=building.organization,
                )
                units = [
                    Unit(
                        entrance=entrance,
                        number=str(n),
                        organization=building.organization,
                    )
                    for n in range(1, apartments_count + 1)
                ]
                Unit.objects.bulk_create(units)
        except IntegrityError:
            return Response(
                {"detail": f"Підʼїзд '{name}' вже існує у будинку."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        out = EntranceDetailSerializer(entrance).data
        return Response(out, status=status.HTTP_201_CREATED)


class AdminEntranceUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Rename / delete an entrance.

    URL: ``/api/v1/apartments/entrances/<uuid:id>/``.

    DELETE is blocked with **409 Conflict** if any unit under the
    entrance currently has an active ``Residency`` — removing it would
    silently orphan a tenant's primary location.
    """

    serializer_class = EntranceDetailSerializer
    permission_classes = [IsAdminUser]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "entrance"
    lookup_field = "id"

    def get_queryset(self):
        return _scope_admin_entrances(self.request.user)

    def update(self, request, *args, **kwargs):
        # Rename via PATCH may collide with unique_together(building, name).
        # Translate the DB-level IntegrityError into a 400 with a clear
        # message instead of bubbling up as a 500.
        try:
            return super().update(request, *args, **kwargs)
        except IntegrityError:
            new_name = request.data.get("name", "")
            return Response(
                {"detail": f"Підʼїзд '{new_name}' вже існує у будинку."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if Residency.objects.filter(unit__entrance=instance).exists():
            return Response(
                {
                    "detail": (
                        "Не можна видалити підʼїзд з активними мешканцями. "
                        "Спершу переселіть/відключіть мешканців."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)


class AdminEntranceGrowAPIView(APIView):
    """Append N more apartments to an existing entrance.

    URL: ``/api/v1/apartments/entrances/<uuid:id>/grow/``.
    Body: ``{"delta": 5}`` — positive integer.

    Numbering continues from ``current_unit_count + 1``.  Hard cap:
    ``500`` total units per entrance (matches create-time validator).
    """

    permission_classes = [IsAdminUser]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "entrance"

    def post(self, request, *args, **kwargs):
        entrance_id = kwargs["id"]
        try:
            entrance = _scope_admin_entrances(request.user).get(id=entrance_id)
        except Entrance.DoesNotExist:
            return Response(
                {"detail": "Entrance not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            delta = int(request.data.get("delta", 0))
        except (TypeError, ValueError):
            return Response(
                {"delta": "Має бути додатнім цілим числом."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if delta < 1:
            return Response(
                {"delta": "Має бути додатнім цілим числом (>= 1)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current = entrance.units.count()
        total_after = current + delta
        if total_after > 500:
            return Response(
                {
                    "delta": (
                        f"Перевищено ліміт 500 квартир на підʼїзд "
                        f"(зараз: {current}, додаєте: {delta})."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        start = current + 1
        with transaction.atomic():
            units = [
                Unit(
                    entrance=entrance,
                    number=str(n),
                    organization=entrance.building.organization,
                )
                for n in range(start, start + delta)
            ]
            Unit.objects.bulk_create(units)

        out = EntranceDetailSerializer(entrance).data
        return Response(out, status=status.HTTP_200_OK)
