"""Tests for ``apps.notifications.bot_resolver`` — PR-14 phase 3.

The resolver is the choke point every send path runs through. These
tests pin down its behaviour so a future refactor can't silently
widen the delivery envelope.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.notifications.bot_resolver import (
    TELEGRAM_FEATURE_FLAG,
    get_bot_for_org,
    resolve_org_from_user_and_context,
)
from apps.notifications.models import OrganizationBot
from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationType,
    OrgRole,
)

User = get_user_model()


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def org_on(db):
    """Org with the Telegram feature enabled."""
    return Organization.objects.create(
        name="ОСББ Alpha",
        slug="osbb-alpha",
        type=OrganizationType.HOUSING_COMPLEX,
        features={TELEGRAM_FEATURE_FLAG: True},
    )


@pytest.fixture
def org_off(db):
    """Org with the Telegram feature flag explicitly off."""
    return Organization.objects.create(
        name="ОСББ Beta",
        slug="osbb-beta",
        type=OrganizationType.HOUSING_COMPLEX,
        features={TELEGRAM_FEATURE_FLAG: False},
    )


@pytest.fixture
def org_flag_missing(db):
    """Org with no feature map at all — should behave like "off"."""
    return Organization.objects.create(
        name="ОСББ Gamma",
        slug="osbb-gamma",
        type=OrganizationType.HOUSING_COMPLEX,
        features={},
    )


@pytest.fixture
def configured_bot_factory(db):
    """Make an OrganizationBot that ``is_configured`` evaluates true for."""
    def _make(organization, **overrides):
        bot = OrganizationBot(
            organization=organization,
            bot_username=overrides.pop("bot_username", "AlphaOSBBBot"),
            is_active=overrides.pop("is_active", True),
            is_primary=overrides.pop("is_primary", True),
        )
        bot.bot_token = overrides.pop("bot_token", "123456789:AAE-configured")
        for k, v in overrides.items():
            setattr(bot, k, v)
        bot.save()
        return bot

    return _make


# ── get_bot_for_org ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestGetBotForOrg:
    def test_returns_none_when_org_is_none(self):
        assert get_bot_for_org(None) is None

    def test_returns_none_when_feature_flag_off(self, org_off, configured_bot_factory):
        """Bot exists and is configured, but the customer turned the
        feature off. Nothing should be returned — that's the kill switch."""
        configured_bot_factory(org_off)
        assert get_bot_for_org(org_off) is None

    def test_returns_none_when_feature_flag_missing(
        self, org_flag_missing, configured_bot_factory,
    ):
        """A missing flag is treated the same as False."""
        configured_bot_factory(org_flag_missing)
        assert get_bot_for_org(org_flag_missing) is None

    def test_returns_none_when_no_bot_exists(self, org_on):
        """Feature enabled, but nobody's configured the bot yet. Silent fallback."""
        assert get_bot_for_org(org_on) is None

    def test_returns_none_when_bot_is_inactive(
        self, org_on, configured_bot_factory,
    ):
        configured_bot_factory(org_on, is_active=False)
        assert get_bot_for_org(org_on) is None

    def test_returns_none_when_bot_token_empty(self, org_on, configured_bot_factory):
        """An active primary bot without a token shouldn't be sent to."""
        bot = configured_bot_factory(org_on)
        bot.bot_token = ""
        bot.save(update_fields=["encrypted_token"])
        assert get_bot_for_org(org_on) is None

    def test_returns_configured_primary_bot(self, org_on, configured_bot_factory):
        bot = configured_bot_factory(org_on)
        resolved = get_bot_for_org(org_on)
        assert resolved is not None
        assert resolved.pk == bot.pk

    def test_ignores_non_primary_bot_even_when_active(
        self, org_on, configured_bot_factory,
    ):
        """Backup bots aren't used for routing in phase 3 — only primary."""
        configured_bot_factory(org_on, bot_username="Primary", is_primary=True)
        configured_bot_factory(org_on, bot_username="Backup", is_primary=False)
        resolved = get_bot_for_org(org_on)
        assert resolved.bot_username == "Primary"


# ── resolve_org_from_user_and_context ──────────────────────────────────────


@pytest.fixture
def user_with_membership(db, org_on):
    user = User.objects.create_user(
        username="resident",
        email="resident@demo.com",
        password="Demo1234!",
        first_name="Олена",
        last_name="Коваль",
    )
    OrganizationMembership.objects.create(
        user=user,
        organization=org_on,
        role=OrgRole.RESIDENT,
        is_active=True,
    )
    return user


@pytest.fixture
def user_no_membership(db):
    return User.objects.create_user(
        username="dangling",
        email="dangling@demo.com",
        password="Demo1234!",
        first_name="Іван",
        last_name="Нічий",
    )


@pytest.mark.django_db
class TestResolveOrgFromUser:
    def test_returns_fallback_when_given(self, user_with_membership, org_off):
        """Explicit fallback wins — the caller knows best."""
        assert (
            resolve_org_from_user_and_context(
                user_with_membership, fallback_org=org_off,
            )
            == org_off
        )

    def test_uses_primary_membership_when_no_fallback(
        self, user_with_membership, org_on,
    ):
        assert (
            resolve_org_from_user_and_context(user_with_membership)
            == org_on
        )

    def test_returns_none_for_user_with_no_membership(self, user_no_membership):
        assert resolve_org_from_user_and_context(user_no_membership) is None


# ── Fixtures для нових тестів ──────────────────────────────────────────────


@pytest.fixture
def org_a(db):
    """Орг з увімкненим feature flag."""
    return Organization.objects.create(
        name="ОСББ A",
        slug="osbb-a",
        type=OrganizationType.HOUSING_COMPLEX,
        features={TELEGRAM_FEATURE_FLAG: True},
    )


@pytest.fixture
def org_flag_off(db):
    """Орг з вимкненим feature flag."""
    return Organization.objects.create(
        name="ОСББ Off",
        slug="osbb-flag-off",
        type=OrganizationType.HOUSING_COMPLEX,
        features={TELEGRAM_FEATURE_FLAG: False},
    )


@pytest.fixture
def bot_factory(db):
    """Створює ``OrganizationBot``.

    Підтримує ``organization=None`` для платформового дефолтного бота
    (``is_default=True``).
    """
    def _make(organization, **overrides):
        bot = OrganizationBot(
            organization=organization,
            bot_username=overrides.pop("bot_username", "AlphaOSBBBot"),
            is_active=overrides.pop("is_active", True),
            is_primary=overrides.pop("is_primary", True),
        )
        bot.bot_token = overrides.pop("bot_token", "123456789:AAE-configured-token-xyz")
        for k, v in overrides.items():
            setattr(bot, k, v)
        bot.save()
        return bot

    return _make


# ── TestGetDefaultBot ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestGetDefaultBot:
    """Перевірка логіки ``_get_default_bot()``."""

    def test_returns_bot_when_default_active_configured(self, bot_factory):
        """Дефолтний бот з is_default=True, is_active=True і токеном → повертається."""
        from apps.notifications.bot_resolver import _get_default_bot

        default_bot = bot_factory(
            None,
            is_default=True,
            is_primary=False,
            bot_username="ApartmentOSBot",
        )
        result = _get_default_bot()
        assert result is not None
        assert result.pk == default_bot.pk

    def test_returns_none_when_no_default_bot(self):
        """Жодного дефолтного бота в БД → None."""
        from apps.notifications.bot_resolver import _get_default_bot

        assert _get_default_bot() is None

    def test_returns_none_when_default_bot_inactive(self, bot_factory):
        """Дефолтний бот є, але is_active=False → None."""
        from apps.notifications.bot_resolver import _get_default_bot

        bot_factory(
            None,
            is_default=True,
            is_active=False,
            is_primary=False,
            bot_username="ApartmentOSBot",
        )
        assert _get_default_bot() is None

    def test_returns_none_when_default_bot_has_no_token(self, bot_factory):
        """Дефолтний бот є і активний, але без токена → не налаштований → None."""
        from apps.notifications.bot_resolver import _get_default_bot

        bot = bot_factory(
            None,
            is_default=True,
            is_primary=False,
            bot_username="ApartmentOSBot",
        )
        # Витерти токен після збереження
        bot.bot_token = ""
        bot.save(update_fields=["encrypted_token"])

        assert _get_default_bot() is None


# ── TestGetBotForOrgFallback ───────────────────────────────────────────────


@pytest.mark.django_db
class TestGetBotForOrgFallback:
    """Перевірка fallback-логіки ``get_bot_for_org()`` → дефолтний бот."""

    def test_org_without_own_bot_gets_default(self, org_a, bot_factory):
        """Орг без власного бота → отримує дефолтний бот."""
        default_bot = bot_factory(
            None,
            is_default=True,
            is_primary=False,
            bot_username="ApartmentOSBot",
        )
        result = get_bot_for_org(org_a)
        assert result is not None
        assert result.pk == default_bot.pk

    def test_org_with_own_bot_gets_own_bot_not_default(
        self, org_a, configured_bot_factory, bot_factory
    ):
        """Орг з власним ботом → отримує свій бот, НЕ дефолтний."""
        own_bot = configured_bot_factory(org_a, bot_username="OrgOwnBot")
        # Дефолтний бот теж існує
        bot_factory(
            None,
            is_default=True,
            is_primary=False,
            bot_username="ApartmentOSBot",
        )
        result = get_bot_for_org(org_a)
        assert result is not None
        assert result.pk == own_bot.pk

    def test_org_with_flag_off_gets_none_even_with_default(
        self, org_flag_off, bot_factory
    ):
        """Вимкнений feature flag → None, навіть якщо є дефолтний бот."""
        bot_factory(
            None,
            is_default=True,
            is_primary=False,
            bot_username="ApartmentOSBot",
        )
        assert get_bot_for_org(org_flag_off) is None

    def test_none_org_returns_none(self):
        """organization=None → None (без змін)."""
        assert get_bot_for_org(None) is None

    def test_own_bot_not_configured_falls_back_to_default(
        self, org_a, configured_bot_factory, bot_factory
    ):
        """Власний бот є, але без токена → fallback на дефолтний бот."""
        # Створити власний бот, потім витерти токен
        own_bot = configured_bot_factory(org_a, bot_username="OrgOwnBot")
        own_bot.bot_token = ""
        own_bot.save(update_fields=["encrypted_token"])

        # Дефолтний бот налаштований
        default_bot = bot_factory(
            None,
            is_default=True,
            is_primary=False,
            bot_username="ApartmentOSBot",
        )

        result = get_bot_for_org(org_a)
        assert result is not None
        assert result.pk == default_bot.pk
