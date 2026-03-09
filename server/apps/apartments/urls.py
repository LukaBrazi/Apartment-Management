# Imports
from apps.apartments.views import (
    ApartmentCreateAPIView,
    ApartmentListAPIView,
    BuildingListAPIView,
    EntranceListAPIView,
)
from django.urls import path


# Set the url patterns
urlpatterns = [
    path("add/", ApartmentCreateAPIView.as_view(), name="add-apartment"),
    path("my-apartments/", ApartmentListAPIView.as_view(), name="list-my-apartments"),
    path("buildings/", BuildingListAPIView.as_view(), name="list-buildings"),
    path("buildings/<uuid:building_id>/entrances/", EntranceListAPIView.as_view(), name="list-entrances"),
]
