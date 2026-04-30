from django.urls import path

from .views import (
    AdminContactListCreateAPIView,
    AdminContactUpdateDestroyAPIView,
    SiteSettingsAPIView,
    SuperAdminOrgsAPIView,
)

urlpatterns = [
    path("", SiteSettingsAPIView.as_view(), name="site-settings"),
    path("superadmin/orgs/", SuperAdminOrgsAPIView.as_view(), name="superadmin-orgs"),
    # PR-15: admin CRUD for ContactPerson rows.  ``organization`` is
    # pinned server-side via ``perform_create`` (Bug 1 prevention).
    path(
        "contacts/admin/",
        AdminContactListCreateAPIView.as_view(),
        name="admin-contacts-list-create",
    ),
    path(
        "contacts/admin/<int:id>/",
        AdminContactUpdateDestroyAPIView.as_view(),
        name="admin-contact-detail",
    ),
]
