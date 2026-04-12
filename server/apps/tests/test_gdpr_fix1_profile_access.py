"""
GDPR Fix 1 — ProfileListAPIView access control.

Перевіряє:
- Tenant не може бачити список всіх мешканців (403)
- Staff/Admin може бачити список (200)
- Email більше не є search field (не знаходить за email)
- NonTenantProfileListAPIView теж захищений
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.profiles.models import Profile

User = get_user_model()


@pytest.fixture
def tenant_user(db):
    user = User.objects.create_user(
        username="gdpr_tenant",
        email="gdpr_tenant@test.com",
        password="Test1234!",
    )
    Profile.objects.filter(user=user).update(
        occupation=Profile.Occupation.TENANT
    )
    return user


@pytest.fixture
def staff_user(db):
    user = User.objects.create_user(
        username="gdpr_staff",
        email="gdpr_staff@test.com",
        password="Test1234!",
        is_staff=True,
    )
    Profile.objects.filter(user=user).update(
        occupation=Profile.Occupation.ELECTRICIAN
    )
    return user


@pytest.fixture
def other_tenant(db):
    user = User.objects.create_user(
        username="other_tenant",
        email="other_tenant@secret.com",
        password="Test1234!",
    )
    Profile.objects.filter(user=user).update(
        occupation=Profile.Occupation.TENANT
    )
    return user


# ── ProfileListAPIView ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProfileListGDPR:
    def test_tenant_cannot_list_profiles(self, tenant_user):
        """GDPR: мешканець не може бачити список всіх мешканців."""
        client = APIClient()
        client.force_authenticate(user=tenant_user)
        response = client.get("/api/v1/profiles/all/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_list_profiles(self):
        """Анонімний не може бачити список мешканців."""
        client = APIClient()
        response = client.get("/api/v1/profiles/all/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_staff_can_list_profiles(self, staff_user, other_tenant):
        """Staff може бачити список мешканців."""
        client = APIClient()
        client.force_authenticate(user=staff_user)
        response = client.get("/api/v1/profiles/all/")
        assert response.status_code == status.HTTP_200_OK

    def test_email_not_searchable(self, staff_user, other_tenant):
        """GDPR: email не є полем пошуку — user enumeration неможливий."""
        client = APIClient()
        client.force_authenticate(user=staff_user)
        response = client.get(
            "/api/v1/profiles/all/",
            {"search": "other_tenant@secret.com"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        profiles_data = data.get("profiles", {})
        # Unwrap pagination: profiles_data may be {"count": N, "results": [...]}
        profiles = profiles_data.get("results", []) if isinstance(profiles_data, dict) else profiles_data
        # Email пошук більше не повертає результати
        assert not any(
            p.get("username") == "other_tenant" for p in profiles
        ), "Email search should NOT find users (user enumeration prevented)"

    def test_username_search_still_works(self, staff_user, other_tenant):
        """Пошук за username залишається доступним для staff."""
        client = APIClient()
        client.force_authenticate(user=staff_user)
        response = client.get(
            "/api/v1/profiles/all/",
            {"search": "other_tenant"},
        )
        assert response.status_code == status.HTTP_200_OK


# ── NonTenantProfileListAPIView ───────────────────────────────────────────────

@pytest.mark.django_db
class TestNonTenantProfileListGDPR:
    def test_tenant_cannot_list_non_tenant_profiles(self, tenant_user, staff_user):
        """GDPR: мешканець не може бачити список персоналу."""
        client = APIClient()
        client.force_authenticate(user=tenant_user)
        response = client.get("/api/v1/profiles/non-tenant-profiles/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_can_list_non_tenant_profiles(self, staff_user):
        """Staff може бачити список персоналу."""
        client = APIClient()
        client.force_authenticate(user=staff_user)
        response = client.get("/api/v1/profiles/non-tenant-profiles/")
        assert response.status_code == status.HTTP_200_OK

    def test_email_not_searchable_non_tenant(self, staff_user):
        """GDPR: email не є полем пошуку в non-tenant profiles."""
        client = APIClient()
        client.force_authenticate(user=staff_user)
        response = client.get(
            "/api/v1/profiles/non-tenant-profiles/",
            {"search": "gdpr_staff@test.com"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        profiles_data = data.get("non_tenant_profiles", {})
        # Unwrap pagination: profiles_data may be {"count": N, "results": [...]}
        profiles = profiles_data.get("results", []) if isinstance(profiles_data, dict) else profiles_data
        assert not any(
            p.get("username") == "gdpr_staff" for p in profiles
        ), "Email search should NOT find users in non-tenant list"
