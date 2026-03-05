from django.urls import path

from apps.passes.views import (
    CloseVehiclePassAPIView,
    MyVehiclePassListAPIView,
    VehiclePassListCreateAPIView,
)

urlpatterns = [
    path("", VehiclePassListCreateAPIView.as_view(), name="vehicle-pass-list-create"),
    path("my/", MyVehiclePassListAPIView.as_view(), name="my-vehicle-passes"),
    path(
        "<uuid:pass_id>/close/",
        CloseVehiclePassAPIView.as_view(),
        name="close-vehicle-pass",
    ),
]
