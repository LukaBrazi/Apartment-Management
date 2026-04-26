# Imports
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView

# Set the django urls
urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/profiles/", include("apps.profiles.urls")),
    path("api/v1/apartments/", include("apps.apartments.urls")),
    path("api/v1/issues/", include("apps.issues.urls")),
    path("api/v1/reports/", include("apps.reports.urls")),
    path("api/v1/ratings/", include("apps.ratings.urls")),
    path("api/v1/posts/", include("apps.posts.urls")),
    path("api/v1/passes/", include("apps.passes.urls")),
    path("api/v1/news/", include("apps.news.urls")),
    path("api/v1/site-settings/", include("apps.site_settings.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/orgs/", include("apps.organizations.urls")),
    path("api/v1/feedback/", include("apps.feedback.urls")),
]


# Swagger urls
urlpatterns += [
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="swagger-schema"),
    path(
        "api/v1/redoc/",
        SpectacularRedocView.as_view(url_name="swagger-schema"),
        name="swagger-redoc",
    ),
]


# Admin configuration — reads SITE_NAME from .env for white-label support
from django.conf import settings as _settings
_site_name = getattr(_settings, "SITE_NAME", "ApartmentOS")
admin.site.site_header = f"{_site_name} Admin"
admin.site.site_title = f"{_site_name} Admin"
admin.site.index_title = f"Панель управління {_site_name}"
