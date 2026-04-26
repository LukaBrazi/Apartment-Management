"""TDD tests for GDPR consent endpoints (PR-5).

Covers ToS + Privacy MVP per DEV_PLAN.md phase 5.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
CONSENT_URL = "/api/v1/consent/"
CONSENT_ME_URL = "/api/v1/consent/me/"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="consent_user",
        email="consent@test.com",
        password="Test1234!",
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestConsentCreate:
    def test_post_consent_creates_log_with_user_version_ip_ua(self, auth_client, user, settings):
        settings.TOS_VERSION = "1.0"
        response = auth_client.post(
            CONSENT_URL,
            {"consent_type": "tos", "version": "1.0"},
            format="json",
            HTTP_USER_AGENT="MozillaTest/1.0",
            REMOTE_ADDR="10.0.0.1",
        )
        assert response.status_code == 201
        from apps.common.models import ConsentLog
        log = ConsentLog.objects.get()
        assert log.user == user
        assert log.consent_type == "tos"
        assert log.version == "1.0"
        assert log.user_agent == "MozillaTest/1.0"
        assert str(log.ip_address) in ("10.0.0.1", "127.0.0.1")  # APIClient may rewrite

    def test_post_consent_requires_authentication_returns_401(self, db):
        client = APIClient()
        response = client.post(
            CONSENT_URL,
            {"consent_type": "tos", "version": "1.0"},
            format="json",
        )
        assert response.status_code == 401

    def test_post_consent_invalid_type_returns_400(self, auth_client):
        response = auth_client.post(
            CONSENT_URL,
            {"consent_type": "marketing", "version": "1.0"},
            format="json",
        )
        assert response.status_code == 400

    def test_post_consent_log_immutable_no_put_endpoint(self, auth_client):
        response = auth_client.put(
            CONSENT_URL,
            {"consent_type": "tos", "version": "1.0"},
            format="json",
        )
        assert response.status_code in (404, 405)


@pytest.mark.django_db
class TestConsentMe:
    def test_get_consent_me_returns_null_when_no_consent(self, auth_client, settings):
        settings.TOS_VERSION = "1.0"
        settings.PRIVACY_VERSION = "1.0"
        response = auth_client.get(CONSENT_ME_URL)
        assert response.status_code == 200
        body = response.json()
        assert body["tos"] is None
        assert body["privacy"] is None

    def test_get_consent_me_returns_latest_per_type(self, auth_client, user, settings):
        settings.TOS_VERSION = "1.0"
        settings.PRIVACY_VERSION = "1.0"
        from apps.common.models import ConsentLog
        ConsentLog.objects.create(user=user, consent_type="tos", version="1.0")
        ConsentLog.objects.create(user=user, consent_type="privacy", version="1.0")
        response = auth_client.get(CONSENT_ME_URL)
        body = response.json()
        assert body["tos"]["version"] == "1.0"
        assert body["tos"]["current"] is True
        assert body["privacy"]["version"] == "1.0"
        assert body["privacy"]["current"] is True

    def test_consent_outdated_when_version_bumped(self, auth_client, user, settings):
        from apps.common.models import ConsentLog
        ConsentLog.objects.create(user=user, consent_type="tos", version="1.0")
        settings.TOS_VERSION = "2.0"
        settings.PRIVACY_VERSION = "1.0"
        response = auth_client.get(CONSENT_ME_URL)
        body = response.json()
        assert body["tos"]["version"] == "1.0"
        assert body["tos"]["current"] is False  # outdated
        assert body["privacy"] is None

    def test_get_consent_me_requires_auth(self, db):
        client = APIClient()
        response = client.get(CONSENT_ME_URL)
        assert response.status_code == 401

    def test_get_consent_me_returns_current_versions_for_frontend(
        self, auth_client, settings
    ):
        """Hotfix 2026-04-26: response must expose server-side current
        versions so frontend can POST the correct version literal.

        Without these fields, the frontend was sending version='current'
        as a sentinel, which the backend stored verbatim, causing
        current=False on next GET → modal never dismissed.
        """
        settings.TOS_VERSION = "1.0"
        settings.PRIVACY_VERSION = "2.0"
        response = auth_client.get(CONSENT_ME_URL)
        body = response.json()
        assert body["tos_current_version"] == "1.0"
        assert body["privacy_current_version"] == "2.0"

    def test_accept_with_correct_version_sets_current_true(
        self, auth_client, user, settings
    ):
        """Full round-trip: POST with correct version → GET shows current=True."""
        settings.TOS_VERSION = "1.0"
        settings.PRIVACY_VERSION = "1.0"

        # 1. First GET: nothing accepted yet
        body1 = auth_client.get(CONSENT_ME_URL).json()
        assert body1["tos"] is None
        assert body1["tos_current_version"] == "1.0"

        # 2. Accept ToS using version from server
        post = auth_client.post(
            CONSENT_URL,
            {"consent_type": "tos", "version": body1["tos_current_version"]},
            format="json",
        )
        assert post.status_code == 201

        # 3. GET again: ToS now current
        body2 = auth_client.get(CONSENT_ME_URL).json()
        assert body2["tos"] is not None
        assert body2["tos"]["version"] == "1.0"
        assert body2["tos"]["current"] is True
