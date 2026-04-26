from apps.common.renderers import GenericJSONRenderer
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ContactPerson, SiteSettings
from .serializers import ContactPersonSerializer, SiteSettingsSerializer


class SiteSettingsAPIView(APIView):
    """
    Retrieve site settings and contact information for the detected organization.

    Returns:
        - settings: SiteSettingsSerializer data (branding, platform identity, support info)
        - contacts: List of ContactPersonSerializer data (active contacts only)
        - organization: The detected organization slug (or None for platform default)
    """

    permission_classes = [AllowAny]
    renderer_classes = [GenericJSONRenderer]
    object_label = "site_settings"

    def get(self, request: Request) -> Response:
        from apps.common.middleware import get_request_site_settings

        site = get_request_site_settings(request)
        org = getattr(request, "organization", None)
        contacts = ContactPerson.objects.filter(
            organization=org, is_active=True
        ).order_by("order", "name")

        data = {
            "settings": SiteSettingsSerializer(site, context={"request": request}).data,
            "contacts": ContactPersonSerializer(
                contacts, many=True, context={"request": request}
            ).data,
            "organization": org.slug if org else None,
        }

        return Response(data, status=status.HTTP_200_OK)


class SuperAdminOrgsAPIView(APIView):
    """SuperAdmin only: list all organizations with their settings."""

    permission_classes = [IsAdminUser]
    renderer_classes = [GenericJSONRenderer]
    object_label = "organizations"

    def get(self, request: Request) -> Response:
        if not request.user.is_superuser:
            return Response({"error": "Superuser only"}, status=status.HTTP_403_FORBIDDEN)

        from apps.organizations.models import Organization

        # PR-6: avoid N+1 by annotating active member count in one query
        # instead of calling ``org.memberships.filter(...).count()`` per row.
        orgs = (
            Organization.objects.all()
            .select_related("site_settings")
            .annotate(
                active_members=Count(
                    "memberships",
                    filter=Q(memberships__is_active=True),
                    distinct=True,
                )
            )
            .order_by("name")
        )
        data = []
        for org in orgs:
            settings = getattr(org, "site_settings", None)
            data.append(
                {
                    "id": str(org.id),
                    "name": org.name,
                    "slug": org.slug,
                    "type": org.type,
                    "is_active": org.is_active,
                    "platform_name": settings.platform_name if settings else None,
                    "primary_color": settings.primary_color if settings else None,
                    "support_email": settings.support_email if settings else None,
                    "members_count": org.active_members,
                }
            )
        return Response({"organizations": data, "total": len(data)}, status=status.HTTP_200_OK)
