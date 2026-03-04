"""Announcement API views."""
from apps.apartments.models import Unit
from apps.posts.models import Announcement
from rest_framework import generics, permissions, serializers


class AnnouncementSerializer(serializers.ModelSerializer):
    building_name = serializers.ReadOnlyField(source="building.name")

    class Meta:
        model = Announcement
        fields = ["id", "building_name", "title", "body", "is_active", "created_at"]


class AnnouncementListAPIView(generics.ListAPIView):
    """Tenants see active announcements for their building only.
    Staff/admin see all active announcements across all buildings.
    """

    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Announcement.objects.filter(is_active=True)
        if user.is_staff or user.is_superuser:
            return qs
        # Tenant: filter to their building via Unit → Entrance → Building
        unit = Unit.objects.filter(apartment__tenant=user).select_related(
            "entrance__building"
        ).first()
        if unit:
            return qs.filter(building=unit.entrance.building)
        # Fallback: no unit linked → no announcements
        return qs.none()
