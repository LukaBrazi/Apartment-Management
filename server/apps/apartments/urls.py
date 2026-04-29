# Imports
from apps.apartments.views import (
    AdminBuildingListCreateAPIView,
    AdminEntranceGrowAPIView,
    AdminEntranceListCreateAPIView,
    AdminEntranceUpdateDestroyAPIView,
    BuildingCreateAPIView,
    BuildingListAPIView,
    BuildingUpdateDestroyAPIView,
    EntranceListAPIView,
    UnitsByBuildingListAPIView,
)
from django.urls import path


# PR-6 removed the tenant-facing ``/add/``, ``/my-apartment/`` and
# ``/my-apartments/`` routes — Unit membership is admin-managed now and
# the Profile endpoint exposes the canonical Unit/Building fields.  Only
# the Building/Entrance/Unit lookups used by staff-side location pickers
# remain.
urlpatterns = [
    path(
        "buildings/",
        BuildingListAPIView.as_view(),
        name="list-buildings",
    ),
    path(
        "buildings/admin/",
        AdminBuildingListCreateAPIView.as_view(),
        name="admin-list-create-buildings",
    ),
    path(
        "buildings/create/",
        BuildingCreateAPIView.as_view(),
        name="admin-create-building",
    ),
    path(
        "buildings/<int:pkid>/",
        BuildingUpdateDestroyAPIView.as_view(),
        name="admin-building-detail",
    ),
    path(
        "buildings/<uuid:building_id>/entrances/",
        EntranceListAPIView.as_view(),
        name="list-entrances",
    ),
    path(
        "buildings/<uuid:building_id>/units/",
        UnitsByBuildingListAPIView.as_view(),
        name="list-units-by-building",
    ),
    # ── PR-14 admin entrance CRUD ──
    path(
        "buildings/<int:building_pkid>/entrances/admin/",
        AdminEntranceListCreateAPIView.as_view(),
        name="admin-list-create-entrances",
    ),
    path(
        "entrances/<uuid:id>/",
        AdminEntranceUpdateDestroyAPIView.as_view(),
        name="admin-entrance-detail",
    ),
    path(
        "entrances/<uuid:id>/grow/",
        AdminEntranceGrowAPIView.as_view(),
        name="admin-entrance-grow",
    ),
]
