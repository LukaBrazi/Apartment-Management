from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.news.models import News, NewsCategory
from apps.news.serializers import (
    NewsAdminSerializer,
    NewsDetailSerializer,
    NewsListSerializer,
)


class NewsListAPIView(APIView):
    """Public: list published news, pinned first."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        qs = News.objects.filter(is_published=True).order_by("-pinned", "-published_at", "-created_at")
        serializer = NewsListSerializer(qs, many=True, context={"request": request})
        return Response({"news": serializer.data})


class NewsDetailAPIView(APIView):
    """Public: get published news by slug; increments views_count."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug, *args, **kwargs):
        news = get_object_or_404(News, slug=slug, is_published=True)
        News.objects.filter(pk=news.pk).update(views_count=F("views_count") + 1)
        news.refresh_from_db()
        serializer = NewsDetailSerializer(news, context={"request": request})
        return Response({"news_item": serializer.data})


class NewsAdminListCreateAPIView(APIView):
    """Admin: list all news (incl. drafts) and create new."""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        qs = News.objects.all().order_by("-created_at")
        serializer = NewsAdminSerializer(qs, many=True, context={"request": request})
        return Response({"news": serializer.data})

    def post(self, request, *args, **kwargs):
        serializer = NewsAdminSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)
        return Response({"news_item": serializer.data}, status=status.HTTP_201_CREATED)


class NewsAdminDetailAPIView(APIView):
    """Admin: retrieve, update or delete a news item by slug."""

    permission_classes = [permissions.IsAdminUser]

    def get_object(self, slug):
        return get_object_or_404(News, slug=slug)

    def get(self, request, slug, *args, **kwargs):
        news = self.get_object(slug)
        serializer = NewsAdminSerializer(news, context={"request": request})
        return Response({"news_item": serializer.data})

    def patch(self, request, slug, *args, **kwargs):
        news = self.get_object(slug)
        serializer = NewsAdminSerializer(news, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"news_item": serializer.data})

    def delete(self, request, slug, *args, **kwargs):
        news = self.get_object(slug)
        news.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
