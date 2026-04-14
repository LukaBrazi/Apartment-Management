# Imports
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.organizations.views import OrganizationMembershipViewSet, OrganizationViewSet

# Create a router and register viewsets
router = DefaultRouter()
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("memberships", OrganizationMembershipViewSet, basename="membership")

# Include router URLs
urlpatterns = [
    path("", include(router.urls)),
]
