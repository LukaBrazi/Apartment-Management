"""Announcement API views."""
from apps.apartments.models import Building
from apps.posts.models import Announcement
from rest_framework import generics, permissions, serializers


class AnnouncementSerializer(serializers.ModelSerializer):
    building_name = serializers.ReadOnlyField(source="building.name")

    class Meta:
        model = Announcement
        fields = ["id", "building_name", "title", "body", "is_active", "created_at"]


class AnnouncementListAPIView(generics.ListAPIView):
    """Tenants see active announcements for their building only.
    Staff/admin and guards see all active announcements for their organization.
    """

    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Announcement.objects.filter(is_active=True)
        if user.is_staff or user.is_superuser:
            return qs

        # Every authenticated user has a Profile (signal-created at user
        # creation).  Guards and workers see all announcements for their
        # org's buildings; tenants see only their own building via the
        # primary Residency.
        occupation = user.profile.occupation

        if occupation != "tenant":
            from apps.organizations.utils import get_user_organizations

            user_orgs = get_user_organizations(user)
            return qs.filter(building__organization__in=user_orgs)

        # Tenant: filter to their building via ``Profile.primary_unit``
        # → Entrance → Building.  ``Residency`` is the canonical source.
        unit = user.profile.primary_unit
        if unit is not None and unit.entrance_id:
            return qs.filter(building=unit.entrance.building)
        # No residency linked → no announcements.
        return qs.none()


class AnnouncementAdminSerializer(serializers.ModelSerializer):
    """Admin serializer for announcements — building is a writable FK."""

    building = serializers.SlugRelatedField(
        slug_field='id',
        queryset=Building.objects.all()
    )
    building_name = serializers.ReadOnlyField(source="building.name")

    class Meta:
        model = Announcement
        fields = ["id", "building", "building_name", "title", "body", "is_active", "created_at"]


class AnnouncementAdminListCreateAPIView(generics.ListCreateAPIView):
    """Admin view: list all announcements (including inactive) and create new ones."""

    serializer_class = AnnouncementAdminSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Announcement.objects.all().order_by("-created_at")


class AnnouncementAdminDetailAPIView(generics.RetrieveAPIView):
    """Admin view: retrieve a single announcement by UUID id."""

    queryset = Announcement.objects.all()
    serializer_class = AnnouncementAdminSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = "id"


class AnnouncementAdminUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Admin view: PATCH or DELETE an announcement by UUID id."""

    queryset = Announcement.objects.all()
    serializer_class = AnnouncementAdminSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = "id"
    http_method_names = ["get", "patch", "delete"]
