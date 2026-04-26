# Imports
from apps.users.views import (
    CustomTokenObtainPairAPIView,
    CustomTokenRefreshAPIView,
    GDPRDataExportAPIView,
    GDPREraseAccountAPIView,
    LogoutAPIView,
    ThrottledPasswordResetUserViewSet,
)
from django.urls import path

# Password reset endpoints (PR-7) — only these two Djoser actions are
# exposed, routed through ``ThrottledPasswordResetUserViewSet`` so the
# ``password_reset`` throttle scope (3/hour) actually fires. Mounting
# the full ``djoser.urls`` would also expose endpoints we don't want
# (registration, /me, etc.), so we map the two actions explicitly.
_password_reset_view = ThrottledPasswordResetUserViewSet.as_view(
    {"post": "reset_password"}
)
_password_reset_confirm_view = ThrottledPasswordResetUserViewSet.as_view(
    {"post": "reset_password_confirm"}
)

# Set the url patterns
urlpatterns = [
    path(
        "login/", CustomTokenObtainPairAPIView.as_view(), name="user-token-obtain-pair"
    ),
    path("refresh/", CustomTokenRefreshAPIView.as_view(), name="user-token-refresh"),
    path("logout/", LogoutAPIView.as_view(), name="user-logout"),
    # GDPR Art. 15 + 20 — Right of Access / Data Portability
    path("my-data/", GDPRDataExportAPIView.as_view(), name="user-gdpr-data-export"),
    # GDPR Art. 17 — Right to Erasure
    path("anonymize/", GDPREraseAccountAPIView.as_view(), name="user-gdpr-erase"),
    # Password reset (Djoser actions, throttled at 3/hour via password_reset scope).
    path(
        "users/reset_password/",
        _password_reset_view,
        name="user-password-reset",
    ),
    path(
        "users/reset_password_confirm/",
        _password_reset_confirm_view,
        name="user-password-reset-confirm",
    ),
]
