"""Tests for the per-(user, organization) TelegramProfile shape — PR-14 phase 2.

These lock down the invariants the rescope migration set up:

* one profile per (user, org) — same user can still hold profiles in
  multiple orgs, but only one per org;
* chat_id uniqueness is per-org, not global;
* verification tokens carry an organization and cascade with it.

Delivery-path tests (who actually sends what when a bot is configured)
live in PR-14 phase 3 test files.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.notifications.models import TelegramProfile, TelegramVerificationToken
from apps.organizations.models import Organization, OrganizationType

User = get_user_model()


# ── Fixtures ───────────────────────────────────────────────────────────────
# ASCII slugs, same reason as test_organization_bot.py: until python-slugify
# lands on this branch, Cyrillic slugify() returns empty and would collide
# with the demo org created by migration 0004.


@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="ОСББ Сонячний",
        slug="osbb-soniachnyi",
        type=OrganizationType.HOUSING_COMPLEX,
    )


@pytest.fixture
def org_other(db):
    return Organization.objects.create(
        name="ОСББ Місячний",
        slug="osbb-misiachnyi",
        type=OrganizationType.HOUSING_COMPLEX,
    )


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="olenka",
        email="resident@demo.com",
        password="Demo1234!",
        first_name="Олена",
        last_name="Коваль",
    )


@pytest.fixture
def user_other(db):
    return User.objects.create_user(
        username="petryk",
        email="resident2@demo.com",
        password="Demo1234!",
        first_name="Петро",
        last_name="Коваленко",
    )


# ── Profile: per-(user, org) uniqueness ────────────────────────────────────


@pytest.mark.django_db
class TestTelegramProfilePerOrg:
    def test_same_user_can_hold_profiles_in_two_orgs(self, user, org, org_other):
        """The whole point of the rescope. One human, two ЖК memberships,
        two separate Telegram bindings — each under its own bot."""
        TelegramProfile.objects.create(user=user, organization=org, chat_id=1001)
        TelegramProfile.objects.create(
            user=user, organization=org_other, chat_id=1002,
        )
        assert TelegramProfile.objects.filter(user=user).count() == 2

    def test_duplicate_user_and_org_rejected(self, user, org):
        """(user, organization) is unique — second create raises."""
        TelegramProfile.objects.create(user=user, organization=org, chat_id=111)
        with pytest.raises(IntegrityError):
            TelegramProfile.objects.create(user=user, organization=org, chat_id=222)

    def test_two_users_in_same_org_are_fine(self, user, user_other, org):
        """Different users in the same org each get their own profile —
        only user×org is unique, not org alone."""
        TelegramProfile.objects.create(user=user, organization=org, chat_id=501)
        TelegramProfile.objects.create(
            user=user_other, organization=org, chat_id=502,
        )
        assert TelegramProfile.objects.filter(organization=org).count() == 2


# ── Profile: chat_id uniqueness is per-org, not global ─────────────────────


@pytest.mark.django_db
class TestTelegramProfileChatIdScoping:
    def test_same_chat_id_allowed_across_orgs(self, user, user_other, org, org_other):
        """Telegram assigns a different chat_id per bot for the same human,
        but at the DB layer we only enforce (org, chat_id) uniqueness —
        the same numeric chat_id appearing under two different orgs is
        not a conflict. Proves the ``unique=True`` on chat_id is gone."""
        TelegramProfile.objects.create(user=user, organization=org, chat_id=42)
        # Same chat_id, different org — must succeed.
        TelegramProfile.objects.create(
            user=user_other, organization=org_other, chat_id=42,
        )
        assert TelegramProfile.objects.filter(chat_id=42).count() == 2

    def test_same_chat_id_in_same_org_rejected(self, user, user_other, org):
        """Within one org, one chat_id → one user. Second write blows up."""
        TelegramProfile.objects.create(user=user, organization=org, chat_id=999)
        with pytest.raises(IntegrityError):
            TelegramProfile.objects.create(
                user=user_other, organization=org, chat_id=999,
            )


# ── Profile: cascade behaviour ─────────────────────────────────────────────


@pytest.mark.django_db
class TestTelegramProfileCascade:
    def test_deleting_org_cascades_profiles(self, user, org):
        TelegramProfile.objects.create(user=user, organization=org, chat_id=77)
        assert TelegramProfile.objects.count() == 1
        org.delete()
        assert TelegramProfile.objects.count() == 0

    def test_deleting_user_cascades_profiles(self, user, org):
        TelegramProfile.objects.create(user=user, organization=org, chat_id=88)
        user.delete()
        assert TelegramProfile.objects.count() == 0


# ── Verification token: now org-scoped ─────────────────────────────────────


@pytest.mark.django_db
class TestTelegramVerificationToken:
    def test_token_requires_organization(self, user):
        """Legacy shape had no org FK; new shape requires it. Attempting
        to skip the FK blows up at DB level."""
        with pytest.raises(IntegrityError):
            TelegramVerificationToken.objects.create(user=user)

    def test_token_with_org_is_valid(self, user, org):
        token = TelegramVerificationToken.objects.create(
            user=user, organization=org,
        )
        assert token.is_valid is True
        assert str(org.slug) in str(token)

    def test_token_cascade_on_org_delete(self, user, org):
        TelegramVerificationToken.objects.create(user=user, organization=org)
        assert TelegramVerificationToken.objects.count() == 1
        org.delete()
        assert TelegramVerificationToken.objects.count() == 0

    def test_two_tokens_for_different_orgs_coexist(self, user, org, org_other):
        """A user can have simultaneous pending links in two orgs — no
        uniqueness constraint blocks that, and the /verify/ flow will
        match them by the org the bot lives under."""
        TelegramVerificationToken.objects.create(user=user, organization=org)
        TelegramVerificationToken.objects.create(
            user=user, organization=org_other,
        )
        assert TelegramVerificationToken.objects.filter(user=user).count() == 2
