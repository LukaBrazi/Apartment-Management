# Imports
from apps.issues.views import (
    AssignedIssuesListAPIView,
    IssueAdminUpdateAPIView,
    IssueCreateAPIView,
    IssueDeleteAPIView,
    IssueDetailAPIView,
    IssueListAPIView,
    IssueReviewAPIView,
    IssueUpdateAPIView,
    MyIssuesListAPIView,
    MyReviewableIssuesAPIView,
)
from django.urls import path

# Set the url patterns
urlpatterns = [
    path("", IssueListAPIView.as_view(), name="list-issues"),
    path("assigned/", AssignedIssuesListAPIView.as_view(), name="list-assigned-issues"),
    path("my-issues/", MyIssuesListAPIView.as_view(), name="list-my-issues"),
    path("my/reviewable/", MyReviewableIssuesAPIView.as_view(), name="my-reviewable-issues"),
    # PR-4: default path — resolves unit from request.user.profile.unit.
    path("create/", IssueCreateAPIView.as_view(), name="create-issue-default"),
    # Explicit Unit targeting (used by dispatchers reporting for a foreign unit).
    path(
        "create/unit/<uuid:unit_id>/",
        IssueCreateAPIView.as_view(),
        name="create-issue-by-unit",
    ),
    # PR-6 removed ``create/<uuid:apartment_id>/`` — the frontend no
    # longer sends apartment IDs and the legacy Apartment model itself
    # is being dropped in PR-7.
    path("<uuid:id>/", IssueDetailAPIView.as_view(), name="detail-issue"),
    path("update/<uuid:id>/", IssueUpdateAPIView.as_view(), name="update-issue"),
    path("delete/<uuid:id>/", IssueDeleteAPIView.as_view(), name="delete-issue"),
    path("admin/update/<uuid:id>/", IssueAdminUpdateAPIView.as_view(), name="admin-update-issue"),
    # Issue reviews — mutual rating after issue is closed (done)
    path("<uuid:id>/review/", IssueReviewAPIView.as_view(), name="issue-review"),
    path("<uuid:id>/reviews/", IssueReviewAPIView.as_view(), name="issue-reviews"),
]
