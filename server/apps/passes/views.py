from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.throttles import WriteOnlyScopedThrottle
from apps.passes.filters import VehiclePassFilter
from apps.passes.models import VehiclePass
from apps.passes.permissions import IsGuardOrAdmin, IsTenant
from apps.passes.serializers import VehiclePassCreateSerializer, VehiclePassSerializer


class VehiclePassListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  — guard/admin: all passes, filterable by visit_date, building, tenant, status.
    POST — tenant: create a new pass request.
    """

    filter_backends = [DjangoFilterBackend]
    filterset_class = VehiclePassFilter
    # PR-8: cap *only* POSTs at 30/hour per user — GETs are issued by the
    # badge counter on every page load and must not burn the budget.
    # ``WriteOnlyScopedThrottle.get_cache_key`` returns ``None`` on safe
    # methods which DRF interprets as "skip throttling for this request".
    throttle_classes = [WriteOnlyScopedThrottle]
    throttle_scope = "pass_create"

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsTenant()]
        return [permissions.IsAuthenticated(), IsGuardOrAdmin()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return VehiclePassCreateSerializer
        return VehiclePassSerializer

    def get_queryset(self):
        """Strict multi-tenant scoping: a non-superuser without any
        active ``OrganizationMembership`` sees no passes.
        """
        qs = VehiclePass.objects.select_related(
            "tenant", "unit__entrance__building", "closed_by"
        )
        if self.request.user.is_superuser:
            return qs
        from apps.organizations.utils import get_user_organizations

        return qs.filter(organization__in=get_user_organizations(self.request.user))


class MyVehiclePassListAPIView(generics.ListAPIView):
    """Tenant sees their own pass requests.

    Supports ``?status=pending`` / ``?status=closed`` for badge counts.
    """

    serializer_class = VehiclePassSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = VehiclePassFilter

    def get_queryset(self):
        """Strict multi-tenant scoping: a non-superuser without any
        active ``OrganizationMembership`` sees no passes — even their
        own.
        """
        qs = VehiclePass.objects.filter(
            tenant=self.request.user
        ).select_related("unit__entrance__building", "closed_by")
        if self.request.user.is_superuser:
            return qs
        from apps.organizations.utils import get_user_organizations

        return qs.filter(organization__in=get_user_organizations(self.request.user))


class CloseVehiclePassAPIView(APIView):
    """Guard or admin marks a pass as closed (car has passed through)."""

    permission_classes = [permissions.IsAuthenticated, IsGuardOrAdmin]

    def post(self, request, pass_id):
        try:
            vehicle_pass = VehiclePass.objects.select_related("tenant").get(
                id=pass_id
            )
        except VehiclePass.DoesNotExist:
            return Response(
                {"error": "Pass not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if vehicle_pass.status == VehiclePass.Status.CLOSED:
            return Response(
                {"error": "Pass is already closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vehicle_pass.status = VehiclePass.Status.CLOSED
        vehicle_pass.closed_by = request.user
        vehicle_pass.closed_at = timezone.now()
        vehicle_pass.save(update_fields=["status", "closed_by_id", "closed_at"])

        return Response(VehiclePassSerializer(vehicle_pass).data)


class DeleteVehiclePassAPIView(APIView):
    """Only the pass creator (tenant) can delete their own pass."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pass_id):
        try:
            vehicle_pass = VehiclePass.objects.get(id=pass_id)
        except VehiclePass.DoesNotExist:
            return Response(
                {"error": "Pass not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Only the pass creator (tenant) can delete their own pass.
        # Staff and admins cannot delete on behalf of tenants.
        is_owner = vehicle_pass.tenant == request.user
        if not is_owner:
            return Response(
                {"error": "You do not have permission to delete this pass."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle_pass.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
