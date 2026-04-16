from django.urls import path

from .views import SiteSettingsAPIView, SuperAdminOrgsAPIView

urlpatterns = [
    path("", SiteSettingsAPIView.as_view(), name="site-settings"),
    path("superadmin/orgs/", SuperAdminOrgsAPIView.as_view(), name="superadmin-orgs"),
]
