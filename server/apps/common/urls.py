"""URL routes for the common app — GDPR consent endpoints (PR-5) +
health probe (PR-7)."""
from django.urls import path

from apps.common.health import HealthCheckAPIView
from apps.common.views import ConsentCreateAPIView, ConsentMeAPIView

urlpatterns = [
    # Load-balancer health probe — DB + cache round-trip, no auth.
    path("health/", HealthCheckAPIView.as_view(), name="health"),
    path("consent/", ConsentCreateAPIView.as_view(), name="consent-create"),
    path("consent/me/", ConsentMeAPIView.as_view(), name="consent-me"),
]
