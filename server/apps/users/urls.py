# Imports
from apps.users.views import (
    CustomProviderAuthAPIView,
    CustomTokenObtainPairAPIView,
    CustomTokenRefreshAPIView,
    GDPRDataExportAPIView,
    GDPREraseAccountAPIView,
    LogoutAPIView,
)
from django.urls import path, re_path

# Set the url patterns
urlpatterns = [
    re_path(
        r"^o/(?P<provider>\S+)/$",
        CustomProviderAuthAPIView.as_view(),
        name="user-provider-auth",
    ),
    path(
        "login/", CustomTokenObtainPairAPIView.as_view(), name="user-token-obtain-pair"
    ),
    path("refresh/", CustomTokenRefreshAPIView.as_view(), name="user-token-refresh"),
    path("logout/", LogoutAPIView.as_view(), name="user-logout"),
    # GDPR Art. 15 + 20 — Right of Access / Data Portability
    path("my-data/", GDPRDataExportAPIView.as_view(), name="user-gdpr-data-export"),
    # GDPR Art. 17 — Right to Erasure
    path("anonymize/", GDPREraseAccountAPIView.as_view(), name="user-gdpr-erase"),
]
