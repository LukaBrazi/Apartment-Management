from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TelegramProfile, TelegramVerificationToken
from .permissions import IsTelegramBot
from .serializers import (
    GenerateTokenSerializer,
    TelegramSettingsSerializer,
    TelegramStatusSerializer,
    VerifyTokenSerializer,
)


class GenerateTokenView(APIView):
    """Generate a one-time verification token for connecting Telegram."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Invalidate any existing unused tokens
        TelegramVerificationToken.objects.filter(user=request.user, is_used=False).delete()

        token_obj = TelegramVerificationToken.objects.create(user=request.user)
        bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "SkandiApartmentsBot")
        deep_link = f"https://t.me/{bot_username}?start={token_obj.token}"

        data = {
            "token": token_obj.token,
            "expires_at": token_obj.expires_at,
            "bot_username": bot_username,
            "deep_link": deep_link,
        }
        serializer = GenerateTokenSerializer(data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VerifyTokenView(APIView):
    """Called by the Telegram bot to verify a token and link chat_id to user."""
    permission_classes = [IsTelegramBot]

    def post(self, request):
        serializer = VerifyTokenSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        token_obj = serializer.context["token_obj"]
        chat_id = serializer.validated_data["chat_id"]

        # Mark token as used
        token_obj.is_used = True
        token_obj.save(update_fields=["is_used"])

        # Create or reactivate TelegramProfile
        profile, created = TelegramProfile.objects.get_or_create(
            user=token_obj.user,
            defaults={"chat_id": chat_id, "is_active": True},
        )
        if not created:
            profile.chat_id = chat_id
            profile.is_active = True
            profile.save(update_fields=["chat_id", "is_active"])

        return Response(
            {"detail": "Telegram connected successfully.", "created": created},
            status=status.HTTP_200_OK,
        )


class TelegramStatusView(generics.RetrieveAPIView):
    """Return current Telegram connection status for the authenticated user."""
    permission_classes = [IsAuthenticated]
    serializer_class = TelegramStatusSerializer

    def get_object(self):
        try:
            return self.request.user.telegram_profile
        except TelegramProfile.DoesNotExist:
            return None

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response({"connected": False}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(instance)
        return Response({"connected": True, **serializer.data})


class TelegramDisconnectView(APIView):
    """Disconnect Telegram from the user's account."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        try:
            profile = request.user.telegram_profile
            profile.is_active = False
            profile.save(update_fields=["is_active"])
            return Response({"detail": "Telegram disconnected."}, status=status.HTTP_200_OK)
        except TelegramProfile.DoesNotExist:
            return Response({"detail": "No Telegram profile found."}, status=status.HTTP_404_NOT_FOUND)


class TelegramSettingsView(generics.UpdateAPIView):
    """Update notification preferences."""
    permission_classes = [IsAuthenticated]
    serializer_class = TelegramSettingsSerializer
    http_method_names = ["patch"]

    def get_object(self):
        try:
            return self.request.user.telegram_profile
        except TelegramProfile.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Telegram not connected.")
