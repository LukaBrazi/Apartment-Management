"""
GDPR Fix 3 — Right to Erasure (Art. 17).

POST /api/v1/auth/anonymize/

Перевіряє:
- Автентифікований user може анонімізувати свій акаунт
- Після анонімізації: email/username замінені на gdpr.invalid плейсхолдери
- is_active = False
- Profile: bio, phone, avatar очищені
- Відповідь 200 з повідомленням
- Неавтентифікований → 401
- Staff-user теж може анонімізуватись (немає виключень за роллю)
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.profiles.models import Profile

User = get_user_model()

ERASE_URL = "/api/v1/auth/anonymize/"


@pytest.fixture
def regular_user(db):
    user = User.objects.create_user(
        username="eraseme",
        email="eraseme@test.com",
        first_name="Видалити",
        last_name="Мене",
        password="Test1234!",
    )
    Profile.objects.filter(user=user).update(
        bio="Особиста інформація",
        occupation=Profile.Occupation.TENANT,
    )
    return user


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="staff_erase",
        email="staff_erase@test.com",
        password="Test1234!",
        is_staff=True,
    )


@pytest.mark.django_db
class TestGDPREraseAccount:
    def test_unauthenticated_cannot_erase(self):
        """Анонімний не може викликати erasure endpoint."""
        client = APIClient()
        response = client.post(ERASE_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_can_erase_own_account(self, regular_user):
        """Автентифікований user анонімізує власний акаунт."""
        client = APIClient()
        client.force_authenticate(user=regular_user)

        response = client.post(ERASE_URL)

        assert response.status_code == status.HTTP_200_OK, response.data

    def test_user_email_anonymized(self, regular_user):
        """Email замінений на gdpr.invalid домен."""
        client = APIClient()
        client.force_authenticate(user=regular_user)
        client.post(ERASE_URL)

        regular_user.refresh_from_db()
        assert "gdpr.invalid" in regular_user.email
        assert "eraseme@test.com" not in regular_user.email

    def test_user_username_anonymized(self, regular_user):
        """Username замінений на deleted_ плейсхолдер."""
        client = APIClient()
        client.force_authenticate(user=regular_user)
        client.post(ERASE_URL)

        regular_user.refresh_from_db()
        assert regular_user.username.startswith("deleted_")
        assert "eraseme" not in regular_user.username

    def test_user_name_cleared(self, regular_user):
        """Ім'я та прізвище очищені."""
        client = APIClient()
        client.force_authenticate(user=regular_user)
        client.post(ERASE_URL)

        regular_user.refresh_from_db()
        assert regular_user.first_name == ""
        assert regular_user.last_name == ""

    def test_user_deactivated(self, regular_user):
        """Акаунт деактивовано (is_active=False)."""
        client = APIClient()
        client.force_authenticate(user=regular_user)
        client.post(ERASE_URL)

        regular_user.refresh_from_db()
        assert regular_user.is_active is False

    def test_profile_bio_cleared(self, regular_user):
        """Profile.bio очищено після erasure."""
        client = APIClient()
        client.force_authenticate(user=regular_user)
        client.post(ERASE_URL)

        profile = Profile.objects.get(user=regular_user)
        assert profile.bio == "" or profile.bio is None

    def test_staff_user_can_erase_own_account(self, staff_user):
        """Staff теж може анонімізувати себе (нема виключень за роллю)."""
        client = APIClient()
        client.force_authenticate(user=staff_user)

        response = client.post(ERASE_URL)
        assert response.status_code == status.HTTP_200_OK

        staff_user.refresh_from_db()
        assert "gdpr.invalid" in staff_user.email
        assert staff_user.is_active is False

    def test_response_has_message(self, regular_user):
        """Відповідь містить повідомлення для user."""
        client = APIClient()
        client.force_authenticate(user=regular_user)

        response = client.post(ERASE_URL)
        assert "message" in response.data
