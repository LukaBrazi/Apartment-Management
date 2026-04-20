"""Tests for the ``OrganizationBot`` model — PR-14 phase 1.

Focus: encryption round-trip via the model, constraint enforcement,
and the webhook-URL helper. Delivery-path / task-routing tests live
in phase-3 test files.
"""
from __future__ import annotations

import pytest
from django.db import IntegrityError

from apps.notifications.models import OrganizationBot
from apps.organizations.models import Organization, OrganizationType


# Fixtures use explicit ASCII slugs because this branch's Organization.save()
# still calls django.utils.text.slugify, which strips Cyrillic to "" — and
# migration 0004 already occupies the empty-slug row. The Cyrillic-aware
# python-slugify swap lives on feat/seed-news; until it merges we pass
# slugs in by hand so the tests are branch-independent.
@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="ОСББ Тестовий",
        slug="osbb-testovyi",
        type=OrganizationType.HOUSING_COMPLEX,
    )


@pytest.fixture
def org_other(db):
    return Organization.objects.create(
        name="ОСББ Сусідній",
        slug="osbb-susidnii",
        type=OrganizationType.HOUSING_COMPLEX,
    )


@pytest.mark.django_db
class TestOrganizationBotEncryption:
    def test_save_round_trips_bot_token(self, org):
        """Plaintext goes in via property, ciphertext lands in DB, read
        reverses it. This is the single most important invariant."""
        bot = OrganizationBot(organization=org, bot_username="ZelenyiBot")
        bot.bot_token = "123456789:AAE-abc"
        bot.save()

        fresh = OrganizationBot.objects.get(pk=bot.pk)
        assert fresh.bot_token == "123456789:AAE-abc"
        # The raw ciphertext field is NOT the plaintext.
        assert fresh.encrypted_token != "123456789:AAE-abc"
        assert fresh.encrypted_token  # but it's set

    def test_empty_token_yields_empty_ciphertext(self, org):
        bot = OrganizationBot(organization=org, bot_username="Empty")
        bot.bot_token = ""
        bot.save()
        assert bot.encrypted_token == ""

    def test_token_masked_hides_secret(self, org):
        bot = OrganizationBot(organization=org, bot_username="Masked")
        bot.bot_token = "99999:AAE-topSecretABCD"
        bot.save()
        masked = bot.bot_token_masked
        assert "topSecret" not in masked
        assert masked.startswith("99999:")
        assert masked.endswith("ABCD")

    def test_is_configured_requires_all_three(self, org):
        """Active + token + username — all three needed."""
        bot = OrganizationBot(organization=org, bot_username="")
        assert bot.is_configured is False  # no username, no token, but active

        bot.bot_username = "HasUsername"
        assert bot.is_configured is False  # still no token

        bot.bot_token = "123:xyz"
        assert bot.is_configured is True

        bot.is_active = False
        assert bot.is_configured is False  # inactive kills it


@pytest.mark.django_db
class TestOrganizationBotDefaults:
    def test_auto_generated_webhook_secret(self, org):
        a = OrganizationBot.objects.create(organization=org, bot_username="AutoA")
        b = OrganizationBot.objects.create(
            organization=org, bot_username="AutoB", is_primary=False,
        )
        assert a.webhook_secret and b.webhook_secret
        assert a.webhook_secret != b.webhook_secret  # random per row
        # Telegram requires 1–256 chars from [A-Za-z0-9_-].
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert set(a.webhook_secret) <= allowed
        assert 1 <= len(a.webhook_secret) <= 256

    def test_auto_generated_internal_secret_is_independent(self, org):
        bot = OrganizationBot.objects.create(
            organization=org, bot_username="Internals",
        )
        assert bot.internal_secret
        assert bot.internal_secret != bot.webhook_secret


@pytest.mark.django_db
class TestOrganizationBotConstraints:
    def test_only_one_primary_per_org(self, org):
        """Partial unique constraint: two primaries in the same org fail."""
        OrganizationBot.objects.create(
            organization=org, bot_username="PrimaryA", is_primary=True,
        )
        with pytest.raises(IntegrityError):
            OrganizationBot.objects.create(
                organization=org, bot_username="PrimaryB", is_primary=True,
            )

    def test_non_primary_rows_allowed_to_coexist(self, org):
        """Backups can multiply freely — only `is_primary=True` collides."""
        OrganizationBot.objects.create(
            organization=org, bot_username="Primary", is_primary=True,
        )
        OrganizationBot.objects.create(
            organization=org, bot_username="Backup1", is_primary=False,
        )
        OrganizationBot.objects.create(
            organization=org, bot_username="Backup2", is_primary=False,
        )
        assert OrganizationBot.objects.filter(organization=org).count() == 3

    def test_primary_allowed_in_different_org(self, org, org_other):
        """Primary uniqueness is per-org, not platform-wide."""
        OrganizationBot.objects.create(
            organization=org, bot_username="OrgOneBot", is_primary=True,
        )
        OrganizationBot.objects.create(
            organization=org_other, bot_username="OrgTwoBot", is_primary=True,
        )
        assert OrganizationBot.objects.filter(is_primary=True).count() == 2

    def test_bot_username_is_globally_unique(self, org, org_other):
        """Telegram enforces @username uniqueness. So do we — two orgs
        can't both claim the same bot."""
        OrganizationBot.objects.create(
            organization=org, bot_username="OnlyOne", is_primary=True,
        )
        with pytest.raises(IntegrityError):
            OrganizationBot.objects.create(
                organization=org_other, bot_username="OnlyOne", is_primary=True,
            )


@pytest.mark.django_db
class TestOrganizationBotWebhook:
    def test_webhook_url_contains_org_slug(self, org):
        bot = OrganizationBot.objects.create(
            organization=org, bot_username="SlugTest",
        )
        url = bot.get_webhook_url("https://apartmentos.org")
        assert url == (
            f"https://apartmentos.org/api/v1/notifications/telegram/webhook/"
            f"{org.slug}/"
        )

    def test_webhook_url_strips_trailing_slash(self, org):
        bot = OrganizationBot.objects.create(
            organization=org, bot_username="TrailingSlash",
        )
        assert "///" not in bot.get_webhook_url("https://apartmentos.org/")


@pytest.mark.django_db
class TestOrganizationBotStr:
    def test_active_bot_str(self, org):
        bot = OrganizationBot.objects.create(
            organization=org, bot_username="Lovely", is_active=True,
        )
        rendered = str(bot)
        assert "@Lovely" in rendered
        assert org.name in rendered
        assert "active" in rendered

    def test_inactive_bot_str(self, org):
        bot = OrganizationBot.objects.create(
            organization=org, bot_username="Sleepy", is_active=False,
        )
        assert "inactive" in str(bot)
