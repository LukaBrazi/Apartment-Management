"""URL routes for the common app — GDPR consent endpoints (PR-5)."""
from django.urls import path

from apps.common.views import ConsentCreateAPIView, ConsentMeAPIView

urlpatterns = [
    path("consent/", ConsentCreateAPIView.as_view(), name="consent-create"),
    path("consent/me/", ConsentMeAPIView.as_view(), name="consent-me"),
]
