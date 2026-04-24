from autoslug import AutoSlugField
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from slugify import slugify as unicode_slugify
from taggit.managers import TaggableManager

from apps.common.models import TimeStampedModel

User = get_user_model()


def _slugify(value: str) -> str:
    return unicode_slugify(value)


class NewsCategory(TimeStampedModel):
    name = models.CharField(_("Name"), max_length=100)
    slug = AutoSlugField(
        populate_from="name", unique=True, always_update=False, slugify=_slugify
    )
    color = models.CharField(_("Color"), max_length=7, default="#2F6FED")

    class Meta:
        verbose_name = _("News Category")
        verbose_name_plural = _("News Categories")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class News(TimeStampedModel):
    title = models.CharField(_("Title"), max_length=255)
    slug = AutoSlugField(
        populate_from="title",
        unique=True,
        always_update=False,
        slugify=_slugify,
        verbose_name=_("Slug"),
    )
    excerpt = models.TextField(_("Excerpt"))
    body = models.TextField(_("Body"))
    cover_image = models.ImageField(
        _("Cover Image"), upload_to="news/covers/", blank=True, null=True
    )
    category = models.ForeignKey(
        NewsCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news",
        verbose_name=_("Category"),
    )
    tags = TaggableManager(verbose_name=_("Tags"), blank=True)
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_articles",
        verbose_name=_("Author"),
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        related_name="news_articles",
        null=True,
        blank=True,
        help_text=_("Організація (NULL = глобальна новина для всіх)"),
    )
    published_at = models.DateTimeField(_("Published At"), null=True, blank=True)
    is_published = models.BooleanField(_("Published"), default=False)
    pinned = models.BooleanField(_("Pinned"), default=False)
    notify_subscribers = models.BooleanField(
        _("Notify Subscribers"),
        default=False,
        help_text=_("Send Telegram notification to org subscribers when published"),
    )
    views_count = models.PositiveIntegerField(_("Views"), default=0)
    external_url = models.URLField(_("External URL"), blank=True)

    class Meta:
        verbose_name = _("News")
        verbose_name_plural = _("News")
        ordering = ["-pinned", "-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "is_published"], name="news_org_published_idx"),
            models.Index(fields=["-published_at"], name="news_published_date_idx"),
        ]


class NewsRead(models.Model):
    """Tracks which News articles a user has already read.

    Created (get_or_create) when a user fetches a news detail view.
    Used to compute the per-user unread count for the sidebar badge.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="news_reads",
        verbose_name=_("User"),
    )
    news = models.ForeignKey(
        News,
        on_delete=models.CASCADE,
        related_name="reads",
        verbose_name=_("News"),
    )
    read_at = models.DateTimeField(_("Read at"), auto_now_add=True)

    class Meta:
        unique_together = [("user", "news")]
        verbose_name = _("News read")
        verbose_name_plural = _("News reads")

    def __str__(self) -> str:
        return self.title
