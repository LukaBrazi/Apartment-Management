"""
GDPR Fix 4 — Right of Access / Data Portability (Art. 15 + 20).

GET /api/v1/auth/my-data/

Перевіряє:
- Неавтентифікований → 401
- Автентифікований → 200 з JSON payload
- Payload містить account, profile, issues, ratings_given, reports_made, vehicle_passes, posts, exported_at
- Дані належать ТІЛЬКИ поточному user (не витікає чужих даних)
- exported_at присутній і є ISO рядком
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.profiles.models import Profile
from apps.issues.models import Issue
from apps.ratings.models import Rating
from apps.passes.models import VehiclePass
from apps.apartments.models import Apartment

User = get_user_model()

DATA_URL = "/api/v1/auth/my-data/"


@pytest.fixture
def owner(db):
    user = User.objects.create_user(
        username="data_owner",
        email="data_owner@test.com",
        first_name="Власник",
        last_name="Даних",
        password="Test1234!",
    )
    Profile.objects.filter(user=user).update(
        bio="Моя особиста біографія",
        occupation=Profile.Occupation.TENANT,
    )
    return user


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="other_gdpr4",
        email="other_gdpr4@test.com",
        password="Test1234!",
    )


@pytest.fixture
def owner_apartment(db, owner):
    return Apartment.objects.create(
        apartment_number="202",
        floor=2,
        building_name="Тест Будинок",
        user=owner,
    )


class TestGDPRDataExport:
    def test_unauthenticated_cannot_export(self):
        """Анонімний не може отримати дані."""
        client = APIClient()
        response = client.get(DATA_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_gets_200(self, owner):
        """Автентифікований user отримує 200."""
        client = APIClient()
        client.force_authenticate(user=owner)
        response = client.get(DATA_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_payload_has_required_keys(self, owner):
        """Payload містить всі обов'язкові секції."""
        client = APIClient()
        client.force_authenticate(user=owner)
        response = client.get(DATA_URL)
        data = response.json()

        required_keys = [
            "account", "profile", "issues", "ratings_given",
            "reports_made", "vehicle_passes", "posts", "exported_at",
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"

    def test_account_data_correct(self, owner):
        """account секція містить правильні дані."""
        client = APIClient()
        client.force_authenticate(user=owner)
        response = client.get(DATA_URL)
        account = response.json()["account"]

        assert account["email"] == "data_owner@test.com"
        assert account["username"] == "data_owner"
        assert account["first_name"] == "Власник"
        assert account["last_name"] == "Даних"

    def test_only_own_issues_exported(self, owner, other_user, owner_apartment):
        """issues містять тільки заявки поточного user."""
        # Issue для owner
        Issue.objects.create(
            apartment=owner_apartment,
            reported_by=owner,
            title="Моя заявка",
            description="Опис",
            status=Issue.IssueStatus.REPORTED,
            priority=Issue.Priority.LOW,
        )
        # Issue для іншого user
        other_apt = Apartment.objects.create(
            apartment_number="303",
            floor=3,
            building_name="Тест",
            user=other_user,
        )
        Issue.objects.create(
            apartment=other_apt,
            reported_by=other_user,
            title="Чужа заявка",
            description="Не моя",
            status=Issue.IssueStatus.REPORTED,
            priority=Issue.Priority.LOW,
        )

        client = APIClient()
        client.force_authenticate(user=owner)
        response = client.get(DATA_URL)
        issues = response.json()["issues"]

        titles = [i["title"] for i in issues]
        assert "Моя заявка" in titles
        assert "Чужа заявка" not in titles

    def test_only_own_ratings_exported(self, owner, other_user):
        """ratings_given містять тільки рейтинги поточного user."""
        Rating.objects.create(
            rating_user=owner,
            rated_user=other_user,
            rating=Rating.RatingChoices.FIVE,
            comment="Добре",
        )
        client = APIClient()
        client.force_authenticate(user=owner)
        response = client.get(DATA_URL)
        ratings = response.json()["ratings_given"]

        assert len(ratings) == 1
        assert ratings[0]["rating"] == 5

    def test_exported_at_is_iso_string(self, owner):
        """exported_at є ISO datetime рядком."""
        client = APIClient()
        client.force_authenticate(user=owner)
        response = client.get(DATA_URL)
        exported_at = response.json()["exported_at"]

        assert isinstance(exported_at, str)
        assert "T" in exported_at  # ISO 8601 format

    def test_vehicle_passes_exported(self, owner):
        """vehicle_passes містять перепустки user."""
        VehiclePass.objects.create(
            tenant=owner,
            car_number="AA1111BB",
            visit_date=timezone.now().date(),
        )
        client = APIClient()
        client.force_authenticate(user=owner)
        response = client.get(DATA_URL)
        passes = response.json()["vehicle_passes"]

        assert len(passes) >= 1
        assert passes[0]["car_number"] == "AA1111BB"
