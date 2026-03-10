from apps.common.renderers import GenericJSONRenderer
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SiteSettings
from .serializers import SiteSettingsSerializer


class SiteSettingsAPIView(APIView):
    permission_classes = [AllowAny]
    renderer_classes = [GenericJSONRenderer]
    object_label = "site_settings"

    def get(self, request: Request) -> Response:
        obj = SiteSettings.get()
        serializer = SiteSettingsSerializer(obj, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
