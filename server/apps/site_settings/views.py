from apps.common.renderers import GenericJSONRenderer
from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ContactPerson, SiteSettings
from .serializers import (
    AdminContactPersonSerializer,
    ContactPersonSerializer,
    SiteSettingsSerializer,
)


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

        # Resolve the org context for the contacts list:
        #   * middleware-detected org (subdomain / X-Organization-Slug
        #     header) — wins when present
        #   * authenticated user's primary org — fallback so authenticated
        #     tenants on the bare apex domain (e.g. apartmentos.org)
        #     still see THEIR ОСББ's contacts.  Without this fallback,
        #     admin-created contacts (organization=org_A) were invisible
        #     because the middleware returned None for apex requests and
        #     the filter then matched only legacy org=None rows.
        #   * unauthenticated apex visitor — still org=None (platform).
        contacts_qs = ContactPerson.objects.filter(is_active=True)
        if org is not None:
            contacts_qs = contacts_qs.filter(organization=org)
        elif request.user.is_authenticated:
            from apps.organizations.utils import get_user_organizations

            user_orgs = get_user_organizations(request.user)
            if user_orgs.exists():
                contacts_qs = contacts_qs.filter(organization__in=user_orgs)
            else:
                # Authenticated but no membership — show only platform
                # contacts (legacy organization=None).
                contacts_qs = contacts_qs.filter(organization__isnull=True)
        else:
            # Anonymous on apex — only platform contacts.
            contacts_qs = contacts_qs.filter(organization__isnull=True)

        contacts = contacts_qs.order_by("order", "name")

        data = {
            "settings": SiteSettingsSerializer(site, context={"request": request}).data,
            "contacts": ContactPersonSerializer(
                contacts, many=True, context={"request": request}
            ).data,
            "organization": org.slug if org else None,
        }

        return Response(data, status=status.HTTP_200_OK)


def _scope_admin_contacts(user):
    """Contacts visible to a staff caller — scoped to their orgs.

    Same pattern as ``_scope_admin_buildings`` in apartments/views.py:
    superusers see everything, regular staff see only contacts whose
    ``organization`` is one of their active memberships.  Contacts
    with ``organization=None`` (platform-level legacy) are excluded
    for non-superusers — there is no safe tenant claim on them.
    """
    from apps.organizations.utils import get_user_organizations

    base = ContactPerson.objects.select_related("organization")
    if user.is_superuser:
        return base
    return base.filter(organization__in=get_user_organizations(user))


class AdminContactListCreateAPIView(generics.ListCreateAPIView):
    """Admin list/create contacts — scoped to the caller's orgs.

    URL: ``/api/v1/site-settings/contacts/admin/``.  Body for POST is
    the writable field set defined on ``AdminContactPersonSerializer``
    (no ``organization`` — pinned server-side).

    Bug 1 prevention (PR-14 pattern): without ``perform_create``
    pinning, the new row would be saved with ``organization=None`` and
    immediately disappear from this same view's GET response (the
    queryset filters by org membership).
    """

    serializer_class = AdminContactPersonSerializer
    permission_classes = [IsAdminUser]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "admin_contacts"
    pagination_class = None

    def get_queryset(self):
        return _scope_admin_contacts(self.request.user).order_by(
            "order", "name"
        )

    def perform_create(self, serializer):
        # Local import — avoid an import cycle at module load (apartments
        # imports from site_settings via the SiteSettings FK in some
        # paths) and keep the helper as the single source of truth.
        from apps.apartments.views import _resolve_caller_organization

        org = _resolve_caller_organization(self.request.user)
        serializer.save(organization=org)


class AdminContactUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Admin retrieve/update/destroy for a single contact.

    URL: ``/api/v1/site-settings/contacts/admin/<int:id>/``.  Cross-org
    access returns 404 because the queryset filters out contacts that
    do not belong to the caller's orgs (paranoid: not 403, to avoid
    leaking the existence of the contact ID).
    """

    serializer_class = AdminContactPersonSerializer
    permission_classes = [IsAdminUser]
    renderer_classes = (GenericJSONRenderer,)
    object_label = "admin_contact"
    lookup_field = "id"

    def get_queryset(self):
        return _scope_admin_contacts(self.request.user)


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
