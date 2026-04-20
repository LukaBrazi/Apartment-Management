from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    GenerateTokenView,
    OrganizationBotViewSet,
    TelegramDisconnectView,
    TelegramSettingsView,
    TelegramStatusView,
    TelegramWebhookView,
    VerifyTokenView,
)

app_name = "notifications"


# PR-14 phase 6: super_admin-only REST API for OrganizationBot rows.
# Mounted under ``/telegram-bots/`` via a DRF router so we get the
# standard list/detail/action URL shapes without hand-wiring each one.
router = DefaultRouter()
router.register(
    r"telegram-bots", OrganizationBotViewSet, basename="telegram-bots",
)


urlpatterns = [
    path(
        "telegram/generate-token/",
        GenerateTokenView.as_view(),
        name="generate-token",
    ),
    path("telegram/verify/", VerifyTokenView.as_view(), name="verify"),
    path("telegram/status/", TelegramStatusView.as_view(), name="status"),
    path(
        "telegram/disconnect/",
        TelegramDisconnectView.as_view(),
        name="disconnect",
    ),
    path(
        "telegram/settings/",
        TelegramSettingsView.as_view(),
        name="settings",
    ),
    # PR-14 phase 5: per-org webhook endpoint Telegram POSTs updates to.
    # The slug is the ``Organization.slug`` — the primary active bot of
    # that org handles the update. Secret goes in the header, not the URL.
    path(
        "telegram/webhook/<slug:org_slug>/",
        TelegramWebhookView.as_view(),
        name="webhook",
    ),
    # Super-admin CRUD / health API.
    path("", include(router.urls)),
]
