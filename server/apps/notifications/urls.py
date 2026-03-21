from django.urls import path
from .views import (
    GenerateTokenView,
    VerifyTokenView,
    TelegramStatusView,
    TelegramDisconnectView,
    TelegramSettingsView,
)

app_name = "notifications"

urlpatterns = [
    path("telegram/generate-token/", GenerateTokenView.as_view(), name="generate-token"),
    path("telegram/verify/", VerifyTokenView.as_view(), name="verify"),
    path("telegram/status/", TelegramStatusView.as_view(), name="status"),
    path("telegram/disconnect/", TelegramDisconnectView.as_view(), name="disconnect"),
    path("telegram/settings/", TelegramSettingsView.as_view(), name="settings"),
]
