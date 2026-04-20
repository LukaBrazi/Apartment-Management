"""
Hardcore tests for auth endpoints — login, refresh, logout.

Scope: apps.users.views {CustomTokenObtainPairAPIView, CustomTokenRefreshAPIView,
LogoutAPIView}. Zero unit-test coverage before this file. These endpoints
set/delete the HttpOnly cookies that gate every authenticated route, and
blacklist refresh tokens on logout — any regression here is a session-security
regression.

Invariants asserted:
- Login with valid creds → 200, "Login successful." message, `access` and
  `refresh` HttpOnly cookies set, plus a non-HttpOnly `logged_in=true` cookie
  that the frontend reads to gate ProtectedRoute.
- Login response body must NOT echo the raw access/refresh tokens (they
  live in cookies only).
- Wrong password → 401, no auth cookies set.
- Nonexistent email → 401.
- Inactive user → 401.
- Refresh with no cookie and no body → 400 (SimpleJWT's missing-token error).
- Refresh with valid refresh cookie → 200 + rotated `access` cookie.
- Refresh with tampered cookie → 401 (InvalidToken).
- Logout → 204, cookies deleted (Set-Cookie with max-age=0 or empty value).
- Logout blacklists the refresh token so a subsequent refresh using the
  same token is rejected (requires `token_blacklist` app enabled).
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils.http import http_date
from rest_framework.test import APIClient

User = get_user_model()


LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/refresh/"
LOGOUT_URL = "/api/v1/auth/logout/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def password():
    return "TestPass12345!"


@pytest.fixture
def user(db, password):
    return User.objects.create_user(
        username="auth_user",
        email="auth@test.com",
        password=password,
        is_active=True,
    )


def _cookie_is_cleared(cookie) -> bool:
    """A Set-Cookie used to clear is marked by max-age=0 / empty value.

    Django's `HttpResponse.delete_cookie` sets max-age=0 AND expires to epoch.
    """
    # cookie.value is empty; cookie["max-age"] is 0.
    return cookie.value == "" or str(cookie.get("max-age")) == "0"


# ═════════════════════════════════════════════════════════════════════════════
# Login — CustomTokenObtainPairAPIView
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestLogin:
    def test_valid_credentials_return_200_and_cookies(self, api_client, user, password):
        resp = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": password},
            format="json",
        )
        assert resp.status_code == 200, resp.data
        assert resp.data.get("message") == "Login successful."

        # Tokens must be in cookies, NOT in body
        assert "access" not in resp.data, (
            "access token must be in HttpOnly cookie, not response body"
        )
        assert "refresh" not in resp.data, (
            "refresh token must be in HttpOnly cookie, not response body"
        )

        # Three cookies present
        cookies = resp.cookies
        assert "access" in cookies, f"Missing 'access' cookie. Got: {list(cookies)}"
        assert "refresh" in cookies, f"Missing 'refresh' cookie. Got: {list(cookies)}"
        assert "logged_in" in cookies, (
            f"Missing 'logged_in' cookie (frontend needs this to gate ProtectedRoute). "
            f"Got: {list(cookies)}"
        )

        # access + refresh must be HttpOnly
        assert cookies["access"]["httponly"], "access cookie must be HttpOnly"
        assert cookies["refresh"]["httponly"], "refresh cookie must be HttpOnly"
        # logged_in must NOT be HttpOnly (frontend JS reads it)
        assert not cookies["logged_in"]["httponly"], (
            "logged_in cookie must be readable by JS (not HttpOnly)"
        )
        assert cookies["logged_in"].value == "true"

        # Tokens are non-empty strings
        assert cookies["access"].value, "access token cookie value empty"
        assert cookies["refresh"].value, "refresh token cookie value empty"

    def test_wrong_password_returns_401_and_no_cookies(self, api_client, user):
        resp = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "WRONG_password_999"},
            format="json",
        )
        assert resp.status_code == 401, resp.data

        # No auth cookies issued
        for name in ("access", "refresh", "logged_in"):
            cookie = resp.cookies.get(name)
            assert cookie is None or cookie.value == "", (
                f"Wrong-password response must not set {name!r} cookie, "
                f"got value={cookie.value if cookie else None!r}"
            )

    def test_unknown_email_returns_401(self, api_client):
        resp = api_client.post(
            LOGIN_URL,
            {"email": "nobody@nowhere.test", "password": "anything12345"},
            format="json",
        )
        assert resp.status_code == 401

    def test_inactive_user_returns_401(self, api_client, password):
        u = User.objects.create_user(
            username="inactive_auth",
            email="inactive@test.com",
            password=password,
        )
        u.is_active = False
        u.save(update_fields=["is_active"])

        resp = api_client.post(
            LOGIN_URL,
            {"email": u.email, "password": password},
            format="json",
        )
        assert resp.status_code == 401, (
            "Inactive user must not be able to log in (SimpleJWT rejects). "
            f"Got {resp.status_code}: {resp.data}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Refresh — CustomTokenRefreshAPIView
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestRefresh:
    def _login(self, api_client, user, password):
        resp = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": password},
            format="json",
        )
        assert resp.status_code == 200
        # Copy cookies onto the client so subsequent requests carry them
        for name, morsel in resp.cookies.items():
            api_client.cookies[name] = morsel.value
        return resp

    def test_refresh_without_cookie_returns_400(self, api_client):
        resp = api_client.post(REFRESH_URL, {}, format="json")
        # SimpleJWT's TokenRefreshSerializer marks `refresh` as required →
        # missing field is a 400 validation error.
        assert resp.status_code == 400, (
            f"Missing refresh token must be 400 (validation error). "
            f"Got {resp.status_code}: {resp.data}"
        )

    def test_refresh_with_valid_cookie_rotates_access(self, api_client, user, password):
        self._login(api_client, user, password)
        old_access = api_client.cookies["access"].value

        resp = api_client.post(REFRESH_URL, {}, format="json")
        assert resp.status_code == 200, resp.data
        assert resp.data.get("message") == "Access token refreshed successfully."

        assert "access" in resp.cookies, "Refresh must set a new access cookie"
        new_access = resp.cookies["access"].value
        assert new_access, "New access token must not be empty"
        # Tokens can in theory be identical if iat resolution is coarse, but in
        # practice SimpleJWT embeds a fresh jti / iat so they MUST differ.
        assert new_access != old_access, (
            "Refresh must rotate access token (iat/jti changes). Got identical value."
        )

        # Response body must not echo raw tokens
        assert "access" not in resp.data
        assert "refresh" not in resp.data

    def test_refresh_with_tampered_cookie_returns_401(self, api_client):
        api_client.cookies["refresh"] = "totally.not.a.valid.jwt"
        resp = api_client.post(REFRESH_URL, {}, format="json")
        assert resp.status_code == 401, (
            f"Tampered refresh token must be 401 (InvalidToken). "
            f"Got {resp.status_code}: {resp.data}"
        )

    def test_refresh_for_deleted_user_returns_401_and_clears_cookies(
        self, api_client, user, password
    ):
        """Ghost-session regression — see CustomTokenRefreshAPIView.

        Scenario: a user is deleted (demo reseed, GDPR erasure) while
        their refresh-token cookie is still live in the browser. Before
        this fix, /auth/refresh/ happily issued new access tokens for the
        non-existent user, the next API call returned 401 'User not
        found', and the SPA went into an infinite refresh loop that
        prevented the user from ever reaching /login.

        Required behavior: refresh detects the missing user, blacklists
        the refresh token, returns 401 with code='user_not_found', and
        emits Set-Cookie clearing access/refresh/logged_in.
        """
        self._login(api_client, user, password)
        # Simulate deletion: drop the user row that the refresh token
        # claims as `user_id`. Hard-delete (not anonymize) is the most
        # adversarial case.
        user.delete()

        resp = api_client.post(REFRESH_URL, {}, format="json")

        assert resp.status_code == 401, (
            f"Refresh for deleted user must be 401 (ghost-session guard). "
            f"Got {resp.status_code}: {resp.data}"
        )
        assert resp.data.get("code") == "user_not_found", resp.data

        # All three auth cookies must be cleared so the SPA falls back
        # to /login on next render.
        for name in ("access", "refresh", "logged_in"):
            cookie = resp.cookies.get(name)
            assert cookie is not None, (
                f"Refresh-for-deleted-user must emit Set-Cookie clearing {name!r}"
            )
            assert _cookie_is_cleared(cookie), (
                f"Cookie {name!r} must be cleared (empty value or max-age=0). "
                f"Got value={cookie.value!r} max-age={cookie.get('max-age')!r}"
            )

    def test_refresh_for_inactive_user_returns_401_and_clears_cookies(
        self, api_client, user, password
    ):
        """Same guard as deleted-user but for is_active=False.

        Anonymize / soft-deactivate flows set is_active=False rather than
        deleting the row. The refresh endpoint must treat both cases the
        same: end the session, clear cookies, force re-login.
        """
        self._login(api_client, user, password)
        user.is_active = False
        user.save(update_fields=["is_active"])

        resp = api_client.post(REFRESH_URL, {}, format="json")

        assert resp.status_code == 401, (
            f"Refresh for inactive user must be 401. "
            f"Got {resp.status_code}: {resp.data}"
        )
        assert resp.data.get("code") == "user_not_found", resp.data

        for name in ("access", "refresh", "logged_in"):
            cookie = resp.cookies.get(name)
            assert cookie is not None and _cookie_is_cleared(cookie), (
                f"Cookie {name!r} must be cleared after refresh-for-inactive."
            )


# ═════════════════════════════════════════════════════════════════════════════
# Logout — LogoutAPIView
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestLogout:
    def _login(self, api_client, user, password):
        resp = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": password},
            format="json",
        )
        assert resp.status_code == 200
        for name, morsel in resp.cookies.items():
            api_client.cookies[name] = morsel.value

    def test_logout_returns_204_and_clears_cookies(self, api_client, user, password):
        self._login(api_client, user, password)

        resp = api_client.post(LOGOUT_URL)
        assert resp.status_code == 204, resp.data

        # Each of the three cookies must have been issued with a clearing Set-Cookie
        for name in ("access", "refresh", "logged_in"):
            cookie = resp.cookies.get(name)
            assert cookie is not None, (
                f"Logout must emit Set-Cookie to clear {name!r}"
            )
            assert _cookie_is_cleared(cookie), (
                f"Cookie {name!r} must be cleared (empty value or max-age=0). "
                f"Got value={cookie.value!r} max-age={cookie.get('max-age')!r}"
            )

    def test_logout_blacklists_refresh_token(self, api_client, user, password):
        """After logout, the old refresh token must be blacklisted → refresh fails 401."""
        self._login(api_client, user, password)
        old_refresh_value = api_client.cookies["refresh"].value

        # Logout clears cookies AND blacklists the refresh token
        resp = api_client.post(LOGOUT_URL)
        assert resp.status_code == 204

        # Put the old refresh token back on the client and try to refresh
        api_client.cookies["refresh"] = old_refresh_value

        resp2 = api_client.post(REFRESH_URL, {}, format="json")
        assert resp2.status_code == 401, (
            f"Refresh with blacklisted token must be 401. "
            f"Got {resp2.status_code}: {resp2.data}"
        )

    def test_logout_anonymous_returns_401(self, api_client):
        """
        LogoutAPIView inherits the project default IsAuthenticated permission,
        so an unauthenticated POST gets 401 before the view body runs.

        This pins the current behavior: a client that already lost its cookies
        cannot re-trigger blacklist logic anonymously. If this ever flips to
        AllowAny, clients could be used to try-blacklist arbitrary refresh
        tokens — this test must fail loudly in that case.
        """
        resp = api_client.post(LOGOUT_URL)
        assert resp.status_code == 401, (
            f"Anonymous logout must be 401 under default IsAuthenticated. "
            f"Got {resp.status_code}: {resp.data}"
        )
