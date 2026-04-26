# Imports
import logging
from typing import Any, Dict

from apps.apartments.models import Unit
from apps.common.models import ContentView
from apps.common.renderers import GenericJSONRenderer
from apps.issues.emails import send_issue_confirmation_email
from apps.issues.filters import IssueFilter
from apps.issues.models import Issue, IssueReview
from apps.issues.serializers import IssueAdminUpdateSerializer, IssueCreateSerializer, IssueReviewSerializer, IssueSerializer, IssueStatusUpdateSerializer, ReviewableIssueSerializer
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.http import Http404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

# Get the logger
logger = logging.getLogger(__name__)


def _issue_base_qs():
    """Return the standard optimised Issue queryset used by all views."""
    return (
        Issue.objects.select_related(
            "unit__entrance__building",
            "category",
            "reported_by",
            "assigned_to",
        ).annotate(view_count=Count("content_views", distinct=True))
    )


# Custom permission class to check if the user is staff or superuser
class IsStaffOrSuperUser(permissions.BasePermission):
    """Custom permission class to check if the user is staff or superuser.

    Extends:
        permissions.BasePermission

    Attributes:
        message (str): The message attribute.

    Methods:
        has_permission: Method to check if the user is staff or superuser.
    """

    # Attributes
    def __init__(self) -> None:
        self.message = None

    # Method to check if the user is staff or superuser
    def has_permission(self, request: Request, view: Any) -> bool:
        """Method to check if the user is staff, superuser, or guard.

        Args:
            request (Request): The request object.
            view (Any): The view object.

        Returns:
            bool: The boolean value.
        """

        if not (request.user and request.user.is_authenticated):
            self.message = "Access to this information is restricted to staff and admin users only."
            return False

        # Staff and superusers always have access
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Guards can view issues (read-only for awareness)
        try:
            if request.user.profile.occupation == "guard":
                return True
        except Exception:
            pass

        self.message = "Access to this information is restricted to staff and admin users only."
        return False


# IssueListAPIView Class
class IssueListAPIView(generics.ListAPIView):
    """List issues. Superuser sees all; staff sees issues scoped to their managed
    buildings (profile.buildings M2M); if no buildings assigned — sees all.
    Tenants are blocked (IsStaffOrSuperUser).
    Supports filtering by status, priority, category, building, is_overdue.
    """

    serializer_class = IssueSerializer
    renderer_classes = (GenericJSONRenderer,)
    permission_classes = (IsStaffOrSuperUser,)
    object_label = "issues"
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = IssueFilter
    search_fields = ("title", "description")
    ordering_fields = ("created_at", "due_at", "priority", "status")
    ordering = ("-created_at",)

    def get_queryset(self):
        user = self.request.user
        base_qs = _issue_base_qs()
        if user.is_superuser:
            return base_qs

        # Narrow by buildings the staff profile manages, then by the
        # caller's active OrganizationMemberships.  A staff user without
        # any active membership sees nothing — there is no fallback.
        managed = user.profile.buildings.all()
        if managed.exists():
            base_qs = base_qs.filter(unit__entrance__building__in=managed).distinct()

        from apps.organizations.utils import get_user_organizations

        return base_qs.filter(organization__in=get_user_organizations(user))


# AssignedIssuesListAPIView Class
class AssignedIssuesListAPIView(generics.ListAPIView):
    """AssignedIssuesListAPIView

    AssignedIssuesListAPIView class is used to list the issues assigned to the user.

    Extends:
        generics.ListAPIView

    Attributes:
        queryset (QuerySet): The queryset of issues.
        serializer_class (IssueSerializer): The issue serializer class.
        renderer_classes (list): The list of renderer classes.
        object_label (str): The object label.

    Methods:
        get_queryset: Method to get the queryset of issues.
    """

    # Attributes
    serializer_class = IssueSerializer
    renderer_classes = (GenericJSONRenderer,)
    object_label = "assigned_issues"

    # Method to get the queryset of issues
    def get_queryset(self):
        """Method to get the queryset of issues.

        Returns:
            QuerySet: The queryset of issues assigned to the user.

        Strict multi-tenant scoping: a non-superuser without any active
        ``OrganizationMembership`` sees no issues — there is no fallback.
        """

        from apps.organizations.utils import get_user_organizations

        qs = _issue_base_qs().filter(assigned_to=self.request.user)
        if self.request.user.is_superuser:
            return qs
        return qs.filter(organization__in=get_user_organizations(self.request.user))


# MyIssuesListAPIView Class
class MyIssuesListAPIView(generics.ListAPIView):
    """List issues reported by the current user (tenant view).
    Supports filtering by status, priority, is_overdue and ordering.
    """

    serializer_class = IssueSerializer
    renderer_classes = (GenericJSONRenderer,)
    object_label = "my_issues"
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_class = IssueFilter
    ordering_fields = ("created_at", "due_at", "priority", "status")
    ordering = ("-created_at",)

    def get_queryset(self):
        """Strict multi-tenant scoping: a non-superuser without any
        active ``OrganizationMembership`` sees no issues.
        """
        from apps.organizations.utils import get_user_organizations

        qs = _issue_base_qs().filter(reported_by=self.request.user)
        if self.request.user.is_superuser:
            return qs
        return qs.filter(organization__in=get_user_organizations(self.request.user))


# IssueCreateAPIView Class
class IssueCreateAPIView(generics.CreateAPIView):
    """IssueCreateAPIView

    IssueCreateAPIView class is used to create an issue.

    Extends:
        generics.CreateAPIView

    Attributes:
        queryset (QuerySet): The queryset of issues.
        serializer_class (IssueSerializer): The issue serializer class.
        renderer_classes (list): The list of renderer classes.
        object_label (str): The object label.

    Methods:
        perform_create: Method to create an issue.

    Raises:
        ValidationError: The validation error.
        PermissionDenied: The permission denied error.
    """

    # Attributes
    queryset = Issue.objects.all()
    serializer_class = IssueCreateSerializer
    renderer_classes = (GenericJSONRenderer,)
    object_label = "issue"

    # Method to create an issue
    def perform_create(self, serializer: IssueCreateSerializer) -> None:
        """Create an issue.

        Resolution order (post-PR-11):
        1. Explicit ``unit_id`` in URL (dispatcher path) — the reporter
           must hold a ``Residency`` on that Unit unless they are
           staff.
        2. Default — primary ``Residency`` of ``request.user`` (tenant
           self-service).
        """

        unit_id = self.kwargs.get("unit_id")
        user = self.request.user

        profile = getattr(user, "profile", None)

        if unit_id:
            # Explicit Unit targeting.
            try:
                unit = Unit.objects.get(id=unit_id)
            except Unit.DoesNotExist:
                raise PermissionDenied("Unit not found.")
            if not (user.is_staff or user.is_superuser):
                # Multi-unit owners can open issues for any Unit they
                # hold a Residency on — authorization lives in the
                # through-model after PR-11.
                from apps.apartments.models import Residency

                owns_unit = Residency.objects.filter(
                    user_id=user.pk, unit_id=unit.pk
                ).exists()
                if not owns_unit:
                    raise PermissionDenied(
                        "You can only report issues for your own unit."
                    )
        else:
            # Default: derive Unit from the reporter's primary Residency.
            # `Profile.unit` FK was removed in PR-11; unit is now resolved
            # through the Residency through-model.
            from apps.apartments.models import Residency

            primary_residency = (
                Residency.objects.filter(user=user, is_primary=True)
                .select_related("unit")
                .first()
            )
            unit = primary_residency.unit if primary_residency else None
            if unit is None:
                raise ValidationError({
                    "detail": (
                        "Your profile has no unit assigned. "
                        "Contact an administrator."
                    )
                })

        issue = serializer.save(
            reported_by=user,
            unit=unit,
        )

        # Send the issue confirmation email
        send_issue_confirmation_email(issue)


# IssueDetailAPIView Class
class IssueDetailAPIView(generics.RetrieveAPIView):
    """IssueDetailAPIView

    IssueDetailAPIView class is used to retrieve an issue.

    Extends:
        generics.RetrieveAPIView

    Attributes:
        queryset (QuerySet): The queryset of issues.
        serializer_class (IssueSerializer): The issue serializer class.
        renderer_classes (list): The list of renderer classes.
        object_label (str): The object label.
        lookup_field (str): The lookup field.

    Methods:
        get_object: Method to get the issue object.
        record_issue_view: Method to record the issue view.
        get_client_ip: Method to get the

    Raises:
        PermissionDenied: The permission denied error.
    """

    # Attributes
    serializer_class = IssueSerializer
    renderer_classes = (GenericJSONRenderer,)
    object_label = "issue"
    lookup_field = "id"

    def get_queryset(self):
        if self.request.user.is_superuser:
            return _issue_base_qs()
        from apps.organizations.utils import get_user_organizations
        return _issue_base_qs().filter(
            organization__in=get_user_organizations(self.request.user)
        )

    # Method to get the issue object
    def get_object(self) -> Issue:
        """Method to get the issue object.

        Returns:
            Issue: The issue object.

        Raises:
            PermissionDenied: The permission denied error.
        """

        # Get the issue
        issue = super().get_object()

        # Get the user
        user = self.request.user

        # If the user is not the reporter, staff, or assignee
        if not (
            user == issue.reported_by or user.is_staff or user == issue.assigned_to
        ):
            # Raise the permission denied error
            raise PermissionDenied("You do not have permission to view this issue.")

        # Record the issue view
        self.record_issue_view(issue)

        # Return the issue
        return issue

    # Method to record the issue view
    def record_issue_view(self, issue: Issue) -> None:
        """Method to record the issue view.

        Args:
            issue (Issue): The issue object.
        """

        # Get the content type
        content_type = ContentType.objects.get_for_model(issue)

        # Get the viewer IP
        viewer_ip = self.get_client_ip()

        # Get the user
        user = self.request.user

        # Get or create the content view
        ContentView.objects.get_or_create(
            content_type=content_type,
            object_id=issue.pk,
            user=user,
            viewer_ip=viewer_ip,
            defaults={
                "last_viewed": timezone.now(),
            },
        )

    # Method to get the client IP
    def get_client_ip(self) -> str:
        """Method to get the client IP.

        Returns:
            str: The client IP.
        """

        # Get the X-Forwarded-For header
        x_forwarded_for = self.request.META.get("HTTP_X_FORWARDED_FOR")

        # If the X-Forwarded-For header is present
        if x_forwarded_for:
            # Get the IP address
            ip = x_forwarded_for.split(",")[0].strip()

        # If the X-Forwarded-For header is not present
        else:
            # Get the IP address
            ip = self.request.META.get("REMOTE_ADDR")

        # Return the IP address
        return ip


# IssueUpdateAPIView Class
class IssueUpdateAPIView(generics.UpdateAPIView):
    """IssueUpdateAPIView

    IssueUpdateAPIView class is used to update an issue.

    Extends:
        generics.UpdateAPIView

    Attributes:
        queryset (QuerySet): The queryset of issues.
        serializer_class (IssueStatusUpdateSerializer): The issue status update serializer class.
        renderer_classes (list): The list of renderer classes.
        object_label (str): The object label.

    Methods:
        get_object: Method to get the issue object.

    Raises:
        PermissionDenied: The permission denied error.
    """

    # Attributes
    lookup_field = "id"
    serializer_class = IssueStatusUpdateSerializer
    renderer_classes = (GenericJSONRenderer,)
    object_label = "issue"

    def get_queryset(self):
        if self.request.user.is_superuser:
            return _issue_base_qs()
        from apps.organizations.utils import get_user_organizations
        return _issue_base_qs().filter(
            organization__in=get_user_organizations(self.request.user)
        )

    # Method to get the issue object
    def get_object(self) -> Issue:
        """Method to get the issue object.

        Returns:
            Issue: The issue object.

        Raises:
            PermissionDenied: The permission denied error.
        """

        # Get the issue
        issue = super().get_object()

        # Get the user
        user = self.request.user

        # If the user is not staff or the assignee
        if not (user.is_staff or user == issue.assigned_to):
            # Log the unauthorized issue status update attempt
            logger.warning(
                f"Unauthorized issue status update attempt by the user {user.full_name} on issue {issue.title}"
            )

            # Raise the permission denied error
            raise PermissionDenied("You do not have permission to update the issue")

        # Return the issue
        return issue


# IssueAdminUpdateAPIView Class
class IssueAdminUpdateAPIView(generics.UpdateAPIView):
    """IssueAdminUpdateAPIView

    IssueAdminUpdateAPIView allows staff/superusers to directly set status,
    priority, and assignee on any issue without the normal transition rules.

    Extends:
        generics.UpdateAPIView

    Attributes:
        queryset (QuerySet): The queryset of issues.
        serializer_class (IssueAdminUpdateSerializer): The admin update serializer.
        renderer_classes (list): The list of renderer classes.
        permission_classes (list): The list of permission classes.
        object_label (str): The object label.
        lookup_field (str): The lookup field.
        http_method_names (list): Allowed HTTP methods (PATCH only).
    """

    # Attributes
    queryset = _issue_base_qs()
    lookup_field = "id"
    serializer_class = IssueAdminUpdateSerializer
    renderer_classes = (GenericJSONRenderer,)
    permission_classes = (IsStaffOrSuperUser,)
    object_label = "issue"
    http_method_names = ["patch"]


# IssueDeleteAPIView Class
class IssueDeleteAPIView(generics.DestroyAPIView):
    """IssueDeleteAPIView

    IssueDeleteAPIView class is used to delete an issue.

    Extends:
        generics.DestroyAPIView

    Attributes:
        queryset (QuerySet): The queryset of issues.
        serializer_class (IssueSerializer): The issue serializer class.
        lookup_field (str): The lookup field.

    Methods:
        get_object: Method to get the issue object.
        delete: Method to delete the issue.

    Raises:
        Http404: The HTTP 404 Not Found status code.
        PermissionDenied: The permission denied error
    """

    # Attributes
    lookup_field = "id"
    serializer_class = IssueSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return _issue_base_qs()
        from apps.organizations.utils import get_user_organizations
        return _issue_base_qs().filter(
            organization__in=get_user_organizations(self.request.user)
        )

    # Method to get the issue object
    def get_object(self) -> Issue:
        """Method to get the issue object.

        Returns:
            Issue: The issue object.

        Raises:
            Http404: The HTTP 404 Not Found status code.
            PermissionDenied: The permission denied error
        """

        # Try to get the issue
        try:
            issue = super().get_object()

        # If the issue does not exist
        except Http404:
            # Raise the HTTP 404 Not Found status code
            raise Http404("Issue not found")

        # Only the reporter can delete their own issue (staff/admin cannot).
        if self.request.user != issue.reported_by:
            # Log the unauthorized issue deletion attempt
            logger.warning(
                f"Unauthorized issue deletion attempt by {self.request.user} on issue {issue.title}"
            )

            # Raise the permission denied error
            raise PermissionDenied(
                "You do not have permission to delete this issue. Please contact the admin."
            )

        # Return the issue
        return issue

    # Method to delete the issue
    def delete(self, request: Request, *args: Dict, **kwargs: Dict) -> Response:
        """Method to delete the issue.

        Args:
            request (Request): The request object.
            *args (Dict): Variable length argument list.
            **kwargs (Dict): Arbitrary keyword arguments.

        Returns:
            Response: The response object.

        Raises:
            Http404: The HTTP 404 Not Found status code.
            PermissionDenied: The permission denied error
        """

        # Get the issue
        super().delete(request, *args, **kwargs)

        # Return the response
        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


class MyReviewableIssuesAPIView(generics.ListAPIView):
    """GET /issues/my/reviewable/

    Returns the current user's done issues that have an assigned worker.
    Each item includes ``my_review`` (null = not yet rated).
    Tenants use this list to rate the worker who resolved their request.

    Pagination is disabled — the list is small (resolved issues per user)
    and the client expects a plain JSON array, not a paginated envelope.
    """

    serializer_class = ReviewableIssueSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        from apps.organizations.utils import get_user_organizations

        qs = (
            Issue.objects.filter(
                reported_by=self.request.user,
                status=Issue.IssueStatus.DONE,
                assigned_to__isnull=False,
            )
            .select_related("assigned_to")
            .order_by("-resolved_on", "-created_at")
        )
        if self.request.user.is_superuser:
            return qs
        return qs.filter(organization__in=get_user_organizations(self.request.user))


class IssueReviewAPIView(APIView):
    """POST  /issues/<uuid:id>/review/  — submit a review for a closed issue.
    GET   /issues/<uuid:id>/reviews/ — fetch all reviews for an issue.

    Permission rules:
    - Only the reporter (author) or the assigned worker may POST a review.
    - The issue must have status ``done``.
    - Each party may leave exactly one review (unique_together enforced at DB level).
    - reviewer  = request.user
    - reviewee  = the other party (worker reviews author; author reviews worker)
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_issue(self, issue_uuid):
        try:
            return Issue.objects.select_related("reported_by", "assigned_to").get(
                id=issue_uuid
            )
        except Issue.DoesNotExist:
            raise NotFound("Заявку не знайдено.")

    def get(self, request, id, *args, **kwargs):
        """Return all reviews for the issue (reporter + assignee may see them)."""
        issue = self._get_issue(id)
        user = request.user
        is_participant = (
            user == issue.reported_by
            or user == issue.assigned_to
            or user.is_staff
        )
        if not is_participant:
            raise PermissionDenied("Доступ заборонено.")

        reviews = IssueReview.objects.filter(issue=issue).select_related(
            "reviewer", "reviewee"
        )
        serializer = IssueReviewSerializer(reviews, many=True)
        return Response({"reviews": serializer.data})

    def post(self, request, id, *args, **kwargs):
        """Create a review. Automatically sets reviewer and reviewee."""
        issue = self._get_issue(id)
        user = request.user

        if issue.status != Issue.IssueStatus.DONE:
            raise ValidationError("Оцінку можна залишити лише для закритої заявки.")

        is_author = user == issue.reported_by
        is_worker = issue.assigned_to and user == issue.assigned_to

        if not is_author and not is_worker:
            raise PermissionDenied(
                "Тільки автор або виконавець заявки може залишити оцінку."
            )

        # Reviewee = the other party
        if is_author:
            reviewee = issue.assigned_to
        else:
            reviewee = issue.reported_by

        if reviewee is None:
            raise ValidationError(
                "Неможливо залишити оцінку: протилежна сторона не визначена."
            )

        serializer = IssueReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from django.db import IntegrityError
        try:
            review = serializer.save(
                issue=issue,
                reviewer=user,
                reviewee=reviewee,
            )
        except IntegrityError:
            raise ValidationError("Ви вже залишили оцінку для цієї заявки.")

        return Response(
            IssueReviewSerializer(review).data,
            status=status.HTTP_201_CREATED,
        )
