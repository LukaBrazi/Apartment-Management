"""Tests for ``apps.notifications.admin`` — OrganizationBotAdmin.

PR-14 directive from the CEO: *"тілтки super_admin"* — only super_admin
may see or mutate ``OrganizationBot``.  Everything else in this module
is a regression test against that rule, plus coverage for the two
action bodies (``_test_one`` and ``_set_webhook_one``) that have side
effects on the row (``last_test_*`` fields) and fire off HTTP calls.

Testing strategy
----------------
* **Permissions** — exercise each ``has_*_permission`` hook with a
  super_admin, a director, an admin-role user, a resident, and an
  anonymous request.  A miss on any hook is a real security hole
  because Django's URL-based admin routes reach those hooks, not any
  middleware in front.
* **Form** — prove that saving without entering a token preserves the
  existing encrypted value (never zero it out), and saving *with* a
  token replaces the ciphertext (via the property setter → Fernet).
* **Actions** — drive ``_test_one`` / ``_set_webhook_one`` directly
  with ``telegram_api`` mocked.  This keeps the tests fast and
  decoupled from the real Telegram response shape.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib import messages
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, override_settings

from apps.notifications.admin import (
    OrganizationBotAdmin,
    OrganizationBotAdminForm,
)
from apps.notifications.models import OrganizationBot
from apps.notifications.telegram_api import TelegramAPIResult
from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationType,
    OrgRole,
)

User = get_user_model()


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def site():
    return AdminSite()


@pytest.fixture
def model_admin(site):
    return OrganizationBotAdmin(OrganizationBot, site)


@pytest.fixture
def factory():
    return RequestFactory()


@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="ОСББ Test", slug="osbb-test",
        type=OrganizationType.HOUSING_COMPLEX,
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_user(
        username="super", email="super@demo.com", password="Demo1234!",
        is_staff=True, is_superuser=True,
        first_name="S", last_name="U",
    )


@pytest.fixture
def director(db, org):
    user = User.objects.create_user(
        username="director", email="director@demo.com", password="Demo1234!",
        is_staff=True, is_superuser=False,
        first_name="D", last_name="I",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.DIRECTOR, is_active=True,
    )
    return user


@pytest.fixture
def org_admin(db, org):
    user = User.objects.create_user(
        username="orgadmin", email="orgadmin@demo.com", password="Demo1234!",
        is_staff=True, is_superuser=False,
        first_name="A", last_name="D",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.ADMIN, is_active=True,
    )
    return user


@pytest.fixture
def resident(db, org):
    user = User.objects.create_user(
        username="res", email="res@demo.com", password="Demo1234!",
        is_staff=False, is_superuser=False,
        first_name="R", last_name="E",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.RESIDENT, is_active=True,
    )
    return user


@pytest.fixture
def bot(db, org):
    bot = OrganizationBot(
        organization=org,
        bot_username="AlphaBot",
        is_active=True,
        is_primary=True,
    )
    bot.bot_token = "123456789:AAE-original-secret"
    bot.save()
    return bot


def _make_request(factory, user):
    request = factory.get("/admin/")
    request.user = user
    # messages framework needs _messages set up — simplest mock.
    request._messages = MagicMock()
    return request


# ── Permissions: super_admin only ─────────────────────────────────────────


@pytest.mark.django_db
class TestPermissions:
    """Every permission hook must lock on ``is_superuser``.

    Hiding the sidebar link only covers one of the four entry points.
    A director who manually GETs ``/admin/notifications/organizationbot/``
    still has to hit ``has_view_permission`` and be refused.
    """

    def test_superuser_has_every_permission(
        self, factory, model_admin, superuser, bot,
    ):
        request = _make_request(factory, superuser)
        assert model_admin.has_module_permission(request) is True
        assert model_admin.has_view_permission(request, bot) is True
        assert model_admin.has_add_permission(request) is True
        assert model_admin.has_change_permission(request, bot) is True
        assert model_admin.has_delete_permission(request, bot) is True

    @pytest.mark.parametrize(
        "role_fixture", ["director", "org_admin", "resident"],
    )
    def test_non_superuser_roles_have_no_access(
        self, factory, model_admin, request, role_fixture, bot,
    ):
        """Director, admin, resident — none of them may touch this model."""
        user = request.getfixturevalue(role_fixture)
        req = _make_request(factory, user)
        assert model_admin.has_module_permission(req) is False
        assert model_admin.has_view_permission(req, bot) is False
        assert model_admin.has_add_permission(req) is False
        assert model_admin.has_change_permission(req, bot) is False
        assert model_admin.has_delete_permission(req, bot) is False

    def test_anonymous_has_no_access(self, factory, model_admin, bot):
        from django.contrib.auth.models import AnonymousUser

        req = _make_request(factory, AnonymousUser())
        assert model_admin.has_module_permission(req) is False
        assert model_admin.has_view_permission(req, bot) is False
        assert model_admin.has_add_permission(req) is False
        assert model_admin.has_change_permission(req, bot) is False
        assert model_admin.has_delete_permission(req, bot) is False


# ── Form: write-only bot_token ────────────────────────────────────────────


@pytest.mark.django_db
class TestForm:
    """The token is never round-tripped to the browser.

    ``OrganizationBotAdminForm`` must:
    * render the field as a password input (``render_value=False``),
    * leave the stored ciphertext alone when the field is submitted blank,
    * re-encrypt via the property setter when a new value is entered.
    """

    def test_token_widget_is_password_and_not_rendered(self):
        form = OrganizationBotAdminForm()
        widget = form.fields["bot_token"].widget
        from django.forms.widgets import PasswordInput

        assert isinstance(widget, PasswordInput)
        assert widget.render_value is False

    def test_empty_submit_preserves_existing_token(self, org):
        bot = OrganizationBot(
            organization=org, bot_username="AlphaBot",
            is_active=True, is_primary=True,
        )
        bot.bot_token = "original:secret"
        bot.save()
        original_ciphertext = bot.encrypted_token

        form = OrganizationBotAdminForm(
            data={
                "organization": org.pk,
                "bot_username": "AlphaBot",
                "bot_token": "",
                "is_active": "on",
                "is_primary": "on",
            },
            instance=bot,
        )
        assert form.is_valid(), form.errors
        saved = form.save()
        saved.refresh_from_db()
        # Ciphertext stays put; plaintext still decrypts.
        assert saved.encrypted_token == original_ciphertext
        assert saved.bot_token == "original:secret"

    def test_new_token_is_encrypted(self, org):
        bot = OrganizationBot(
            organization=org, bot_username="AlphaBot",
            is_active=True, is_primary=True,
        )
        bot.bot_token = "original:secret"
        bot.save()

        form = OrganizationBotAdminForm(
            data={
                "organization": org.pk,
                "bot_username": "AlphaBot",
                "bot_token": "999:NEW-secret",
                "is_active": "on",
                "is_primary": "on",
            },
            instance=bot,
        )
        assert form.is_valid(), form.errors
        saved = form.save()
        saved.refresh_from_db()
        # Ciphertext changed, and the property decrypts back to the new value.
        assert saved.bot_token == "999:NEW-secret"
        # And "999:NEW-secret" must NOT appear verbatim in the stored
        # ciphertext — otherwise encryption isn't doing its job.
        assert "NEW-secret" not in saved.encrypted_token


# ── Actions: _test_one ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestActionTestBot:
    def test_success_records_ok_and_flashes_success(
        self, factory, model_admin, superuser, bot,
    ):
        req = _make_request(factory, superuser)
        with patch(
            "apps.notifications.admin.tg_get_me",
            return_value=TelegramAPIResult(
                ok=True, data={"username": "AlphaBot"},
            ),
        ):
            model_admin._test_one(req, bot)
        bot.refresh_from_db()
        assert bot.last_test_ok is True
        assert bot.last_test_error == ""
        assert bot.last_tested_at is not None

    def test_username_mismatch_records_warning(
        self, factory, model_admin, superuser, bot,
    ):
        """A common super_admin mistake: paste a token from a different
        bot.  ``getMe`` returns the *actual* bot's username — we detect
        the mismatch and refuse to call the test 'ok', so the UI
        surfaces the problem before any user tries to /start."""
        req = _make_request(factory, superuser)
        with patch(
            "apps.notifications.admin.tg_get_me",
            return_value=TelegramAPIResult(
                ok=True, data={"username": "SomeoneElseBot"},
            ),
        ):
            model_admin._test_one(req, bot)
        bot.refresh_from_db()
        assert bot.last_test_ok is False
        assert "SomeoneElseBot" in bot.last_test_error
        assert "AlphaBot" in bot.last_test_error

    def test_telegram_error_records_failure(
        self, factory, model_admin, superuser, bot,
    ):
        req = _make_request(factory, superuser)
        with patch(
            "apps.notifications.admin.tg_get_me",
            return_value=TelegramAPIResult(
                ok=False, error="Unauthorized",
            ),
        ):
            model_admin._test_one(req, bot)
        bot.refresh_from_db()
        assert bot.last_test_ok is False
        assert bot.last_test_error == "Unauthorized"

    def test_unreadable_token_records_failure_without_calling_tg(
        self, factory, model_admin, superuser, org,
    ):
        """Corrupt ciphertext (e.g. key rotation gap) must not 500 the
        admin or call Telegram with empty/garbage tokens."""
        broken = OrganizationBot(
            organization=org, bot_username="BrokenBot",
            encrypted_token="definitely-not-fernet",
            is_active=True, is_primary=True,
        )
        broken.save()
        req = _make_request(factory, superuser)
        with patch("apps.notifications.admin.tg_get_me") as tg_call:
            model_admin._test_one(req, broken)
        tg_call.assert_not_called()
        broken.refresh_from_db()
        assert broken.last_test_ok is False
        assert broken.last_test_error != ""


# ── Actions: _set_webhook_one + _delete_webhook_one ───────────────────────


@pytest.mark.django_db
class TestActionSetWebhook:
    def test_success_passes_url_and_secret(
        self, factory, model_admin, superuser, bot,
    ):
        req = _make_request(factory, superuser)
        with patch(
            "apps.notifications.admin.tg_set_webhook",
            return_value=TelegramAPIResult(ok=True),
        ) as set_webhook_call:
            model_admin._set_webhook_one(
                req, bot, base_url="https://apartmentos.org",
            )

        set_webhook_call.assert_called_once()
        kwargs = set_webhook_call.call_args.kwargs
        # Token comes from the bot (not from the queue).
        assert set_webhook_call.call_args.args[0] == bot.bot_token
        assert kwargs["url"].endswith(f"/webhook/{bot.organization.slug}/")
        assert kwargs["secret_token"] == bot.webhook_secret

    def test_action_refuses_when_platform_public_url_blank(
        self, factory, model_admin, superuser, bot,
    ):
        req = _make_request(factory, superuser)
        with override_settings(PLATFORM_PUBLIC_URL=""):
            with patch(
                "apps.notifications.admin.tg_set_webhook",
            ) as set_webhook_call:
                model_admin.action_set_webhook(
                    req, OrganizationBot.objects.filter(pk=bot.pk),
                )
        set_webhook_call.assert_not_called()


@pytest.mark.django_db
class TestActionDeleteWebhook:
    def test_success_calls_api(
        self, factory, model_admin, superuser, bot,
    ):
        req = _make_request(factory, superuser)
        with patch(
            "apps.notifications.admin.tg_delete_webhook",
            return_value=TelegramAPIResult(ok=True),
        ) as delete_webhook_call:
            model_admin._delete_webhook_one(req, bot)
        delete_webhook_call.assert_called_once_with(bot.bot_token)


# ── save_model records created_by ─────────────────────────────────────────


@pytest.mark.django_db
class TestSaveModel:
    def test_created_by_is_set_on_create(
        self, factory, model_admin, superuser, org,
    ):
        req = _make_request(factory, superuser)
        new_bot = OrganizationBot(
            organization=org, bot_username="FreshBot",
            is_active=True, is_primary=False,
        )
        new_bot.bot_token = "1:AAE-fresh"
        model_admin.save_model(req, new_bot, form=None, change=False)
        new_bot.refresh_from_db()
        assert new_bot.created_by_id == superuser.pk

    def test_created_by_unchanged_on_update(
        self, factory, model_admin, superuser, bot,
    ):
        """``change=True`` must not overwrite the original creator."""
        original = bot.created_by_id
        req = _make_request(factory, superuser)
        bot.bot_username = "AlphaBotRenamed"
        model_admin.save_model(req, bot, form=None, change=True)
        bot.refresh_from_db()
        assert bot.created_by_id == original


# ── masked_token + webhook_url helpers ────────────────────────────────────


@pytest.mark.django_db
class TestDisplayHelpers:
    def test_masked_token_hides_middle(self, model_admin, bot):
        masked = model_admin.masked_token(bot)
        # The bot ID (before ':') is kept; the middle is hidden; last 4
        # of the secret are kept for human verification.
        assert masked.startswith("123456789:")
        assert "original" not in masked  # secret body not leaked
        assert masked.endswith("cret")  # tail kept

    def test_masked_token_on_empty_bot(self, model_admin, org):
        empty = OrganizationBot(
            organization=org, bot_username="EmptyBot",
            is_active=True, is_primary=False,
        )
        assert model_admin.masked_token(empty) == "—"

    def test_webhook_url_with_public_url(self, model_admin, bot):
        with override_settings(PLATFORM_PUBLIC_URL="https://apartmentos.org"):
            url = model_admin.webhook_url(bot)
        assert url == (
            "https://apartmentos.org/api/v1/notifications/"
            f"telegram/webhook/{bot.organization.slug}/"
        )

    def test_webhook_url_without_public_url_explains(self, model_admin, bot):
        with override_settings(PLATFORM_PUBLIC_URL=""):
            url = model_admin.webhook_url(bot)
        assert "PLATFORM_PUBLIC_URL" in str(url)
