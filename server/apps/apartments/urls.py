# Imports
from apps.apartments.views import (
    AdminBuildingListCreateAPIView,
    ApartmentCreateAPIView,
    ApartmentListAPIView,
    BuildingCreateAPIView,
    BuildingListAPIView,
    BuildingUpdateDestroyAPIView,
    EntranceListAPIView,
)
from django.urls import path


# Set the url patterns
urlpatterns = [
    path("add/", ApartmentCreateAPIView.as_view(), name="add-apartment"),
    path("my-apartments/", ApartmentListAPIView.as_view(), name="list-my-apartments"),
    path("buildings/", BuildingListAPIView.as_view(), name="list-buildings"),
    path("buildings/admin/", AdminBuildingListCreateAPIView.as_view(), name="admin-list-create-buildings"),
    path("buildings/create/", BuildingCreateAPIView.as_view(), name="admin-create-building"),
    path("buildings/<int:pkid>/", BuildingUpdateDestroyAPIView.as_view(), name="admin-building-detail"),
    path("buildings/<uuid:building_id>/entrances/", EntranceListAPIView.as_view(), name="list-entrances"),
]
