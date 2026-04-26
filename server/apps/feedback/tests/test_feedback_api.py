"""TDD tests for POST /api/v1/feedback/create/

Covers:
  - Authentication requirements (401 for anonymous)
  - Successful feedback creation (201 + DB record)
  - User is always taken from request, never from body
  - Message validation (min 10 chars, max 2000 chars, empty)
  - Celery task triggered on success
  - Rate limiting (429 after 3 requests)
  - Default is_reviewed=False
  - Response does not expose user field (security)
"""
from unittest.mock import patch, MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

User = get_user_model()

FEEDBACK_URL = "/api/v1/feedback/create/"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="feedback_user",
        email="feedback_user@test.com",
        password="testpass123",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="other_feedback_user",
        email="other_feedback_user@test.com",
        password="testpass123",
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Clear cache before each test to reset throttle counters."""
    cache.clear()
    yield
    cache.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestFeedbackCreate:

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self):
        """Anonymous user cannot submit feedback — must get 401."""
        client = APIClient()
        response = client.post(FEEDBACK_URL, {"message": "This is a valid message"}, format="json")
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_authenticated_creates_feedback(self, auth_client, user):
        """Authenticated user with valid message gets 201 and a DB record is created."""
        from apps.feedback.models import Feedback

        with patch("apps.feedback.views.send_feedback_notification_task") as mock_task:
            mock_task.delay = MagicMock()
            response = auth_client.post(
                FEEDBACK_URL,
                {"message": "This is a valid feedback message."},
                format="json",
            )

        assert response.status_code == 201
        assert Feedback.objects.filter(user=user).count() == 1

    @pytest.mark.django_db
    def test_user_set_from_request_not_body(self, auth_client, user, other_user):
        """Even if 'user' is passed in request body, it must be overridden by request.user."""
        from apps.feedback.models import Feedback

        with patch("apps.feedback.views.send_feedback_notification_task") as mock_task:
            mock_task.delay = MagicMock()
            response = auth_client.post(
                FEEDBACK_URL,
                {"message": "Trying to spoof user field here.", "user": other_user.pkid},
                format="json",
            )

        assert response.status_code == 201
        feedback = Feedback.objects.get(user=user)
        assert feedback.user == user
        assert feedback.user != other_user

    @pytest.mark.django_db
    def test_message_too_short_returns_400(self, auth_client):
        """Message shorter than 10 characters must return 400."""
        response = auth_client.post(
            FEEDBACK_URL,
            {"message": "Short"},
            format="json",
        )
        assert response.status_code == 400
        assert "message" in response.data

    @pytest.mark.django_db
    def test_empty_message_returns_400(self, auth_client):
        """Empty message must return 400."""
        response = auth_client.post(
            FEEDBACK_URL,
            {"message": ""},
            format="json",
        )
        assert response.status_code == 400
        assert "message" in response.data

    @pytest.mark.django_db
    def test_message_at_max_length_is_valid(self, auth_client):
        """Message with exactly 2000 characters must be accepted (201)."""
        with patch("apps.feedback.views.send_feedback_notification_task") as mock_task:
            mock_task.delay = MagicMock()
            response = auth_client.post(
                FEEDBACK_URL,
                {"message": "x" * 2000},
                format="json",
            )
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_message_over_max_length_returns_400(self, auth_client):
        """Message with 2001 characters must be rejected with 400."""
        response = auth_client.post(
            FEEDBACK_URL,
            {"message": "x" * 2001},
            format="json",
        )
        assert response.status_code == 400
        assert "message" in response.data

    @pytest.mark.django_db
    def test_celery_task_called_on_create(self, auth_client, user):
        """After successful feedback creation, send_feedback_notification_task.delay must be called
        with the correct feedback pkid."""
        from apps.feedback.models import Feedback

        with patch("apps.feedback.views.send_feedback_notification_task") as mock_task:
            mock_delay = MagicMock()
            mock_task.delay = mock_delay

            response = auth_client.post(
                FEEDBACK_URL,
                {"message": "Valid feedback message for celery test."},
                format="json",
            )

        assert response.status_code == 201
        feedback = Feedback.objects.get(user=user)
        mock_delay.assert_called_once_with(feedback.pkid)

    @pytest.mark.django_db
    def test_rate_limit_after_3_requests(self, auth_client):
        """4th request from the same user within the throttle window must return 429."""
        valid_payload = {"message": "Valid message for throttle test!"}

        with patch("apps.feedback.views.send_feedback_notification_task") as mock_task:
            mock_task.delay = MagicMock()

            # Перші 3 запити мають проходити
            for i in range(3):
                response = auth_client.post(FEEDBACK_URL, valid_payload, format="json")
                assert response.status_code == 201, f"Request {i+1} should succeed, got {response.status_code}"

            # 4-й запит має бути заблокований
            response = auth_client.post(FEEDBACK_URL, valid_payload, format="json")

        assert response.status_code == 429

    @pytest.mark.django_db
    def test_is_reviewed_default_false(self, auth_client, user):
        """Newly created feedback must have is_reviewed=False by default."""
        from apps.feedback.models import Feedback

        with patch("apps.feedback.views.send_feedback_notification_task") as mock_task:
            mock_task.delay = MagicMock()
            response = auth_client.post(
                FEEDBACK_URL,
                {"message": "Is this feedback reviewed yet?"},
                format="json",
            )

        assert response.status_code == 201
        feedback = Feedback.objects.get(user=user)
        assert feedback.is_reviewed is False

    @pytest.mark.django_db
    def test_response_does_not_contain_user_field(self, auth_client):
        """API response must NOT expose the 'user' field (security check)."""
        with patch("apps.feedback.views.send_feedback_notification_task") as mock_task:
            mock_task.delay = MagicMock()
            response = auth_client.post(
                FEEDBACK_URL,
                {"message": "Security check — no user in response."},
                format="json",
            )

        assert response.status_code == 201
        assert "user" not in response.data
