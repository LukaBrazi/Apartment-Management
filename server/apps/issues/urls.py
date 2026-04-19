# Imports
from apps.issues.views import (
    AssignedIssuesListAPIView,
    IssueAdminUpdateAPIView,
    IssueCreateAPIView,
    IssueDeleteAPIView,
    IssueDetailAPIView,
    IssueListAPIView,
    IssueUpdateAPIView,
    MyIssuesListAPIView,
)
from django.urls import path

# Set the url patterns
urlpatterns = [
    path("", IssueListAPIView.as_view(), name="list-issues"),
    path("assigned/", AssignedIssuesListAPIView.as_view(), name="list-assigned-issues"),
    path("my-issues/", MyIssuesListAPIView.as_view(), name="list-my-issues"),
    # PR-4: default path — resolves unit from request.user.profile.unit.
    path("create/", IssueCreateAPIView.as_view(), name="create-issue-default"),
    # Explicit Unit targeting (used by dispatchers reporting for a foreign unit).
    path(
        "create/unit/<uuid:unit_id>/",
        IssueCreateAPIView.as_view(),
        name="create-issue-by-unit",
    ),
    # Legacy Apartment-based path — retained for one release, removed in PR-6.
    path(
        "create/<uuid:apartment_id>/",
        IssueCreateAPIView.as_view(),
        name="create-issue",
    ),
    path("<uuid:id>/", IssueDetailAPIView.as_view(), name="detail-issue"),
    path("update/<uuid:id>/", IssueUpdateAPIView.as_view(), name="update-issue"),
    path("delete/<uuid:id>/", IssueDeleteAPIView.as_view(), name="delete-issue"),
    path("admin/update/<uuid:id>/", IssueAdminUpdateAPIView.as_view(), name="admin-update-issue"),
]
