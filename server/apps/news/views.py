from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.news.models import News, NewsCategory, NewsRead
from apps.news.serializers import (
    NewsAdminSerializer,
    NewsDetailSerializer,
    NewsListSerializer,
)


class NewsListAPIView(APIView):
    """Public: list published news, pinned first.

    Response includes ``unread_count`` — the number of articles the
    authenticated user has not yet opened.  The sidebar badge reads this
    field so it only shows truly new content, not the total article count.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        qs = News.objects.filter(is_published=True)
        # Filter by organization: user sees org news + global news (org=NULL)
        if request.user.is_authenticated and not request.user.is_superuser:
            from apps.organizations.utils import get_user_organizations
            user_orgs = get_user_organizations(request.user)
            qs = qs.filter(Q(organization__in=user_orgs) | Q(organization__isnull=True))
        qs = qs.order_by("-pinned", "-published_at", "-created_at")
        serializer = NewsListSerializer(qs, many=True, context={"request": request})

        # Compute unread count for the sidebar badge
        if request.user.is_authenticated:
            read_ids = NewsRead.objects.filter(
                user=request.user
            ).values_list("news_id", flat=True)
            unread_count = qs.exclude(pk__in=read_ids).count()
        else:
            unread_count = qs.count()

        return Response({"news": serializer.data, "unread_count": unread_count})


class NewsDetailAPIView(APIView):
    """Public: get published news by slug; increments views_count and marks as read."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug, *args, **kwargs):
        qs = News.objects.filter(slug=slug, is_published=True)
        # SECURITY: scope to user's organisations — prevents IDOR across orgs.
        if request.user.is_authenticated and not request.user.is_superuser:
            from apps.organizations.utils import get_user_organizations
            user_orgs = get_user_organizations(request.user)
            qs = qs.filter(Q(organization__in=user_orgs) | Q(organization__isnull=True))
        news = get_object_or_404(qs)
        News.objects.filter(pk=news.pk).update(views_count=F("views_count") + 1)
        news.refresh_from_db()
        # Mark as read for the sidebar unread counter
        if request.user.is_authenticated:
            NewsRead.objects.get_or_create(user=request.user, news=news)
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
        news = serializer.save(author=request.user)

        # Fire TG broadcast if admin checked «Notify subscribers» and article is published.
        if news.notify_subscribers and news.is_published:
            from apps.notifications.tasks import notify_subscribers_news
            notify_subscribers_news.delay(str(news.pk))

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
