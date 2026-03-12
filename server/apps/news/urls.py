from django.urls import path

from apps.news.views import (
    NewsAdminDetailAPIView,
    NewsAdminListCreateAPIView,
    NewsDetailAPIView,
    NewsListAPIView,
)

urlpatterns = [
    path("", NewsListAPIView.as_view(), name="news-list"),
    path("admin/", NewsAdminListCreateAPIView.as_view(), name="news-admin-list"),
    path("admin/<slug:slug>/", NewsAdminDetailAPIView.as_view(), name="news-admin-detail"),
    path("<slug:slug>/", NewsDetailAPIView.as_view(), name="news-detail"),
]
