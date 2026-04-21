"""
Тести захисту від IDOR (Insecure Direct Object Reference) у views заявок.

Перевіряємо, що IssueDetailAPIView, IssueUpdateAPIView та IssueDeleteAPIView
повертають 404 для заявок з чужої організації.
"""
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrgRole,
    OrganizationType,
)
from apps.issues.models import Issue

User = get_user_model()


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_celery_notifications():
    """Мокаємо Celery-таск, щоб уникнути підключення до RabbitMQ."""
    with patch("apps.notifications.tasks.notify_dispatchers_new_issue.delay"):
        yield


@pytest.fixture
def org1(db):
    owner = User.objects.create_user(
        email="owner1@test.com",
        username="owner1",
        first_name="Owner",
        last_name="One",
        password="testpass123",
    )
    org = Organization.objects.create(
        name="Org One",
        type=OrganizationType.HOUSING_COMPLEX,
        owner=owner,
        address="1 Main St",
        city="Kyiv",
        email="org1@test.com",
        phone="+380111111111",
    )
    OrganizationMembership.objects.create(user=owner, organization=org, role=OrgRole.DIRECTOR)
    return org


@pytest.fixture
def org2(db):
    owner = User.objects.create_user(
        email="owner2@test.com",
        username="owner2",
        first_name="Owner",
        last_name="Two",
        password="testpass123",
    )
    org = Organization.objects.create(
        name="Org Two",
        type=OrganizationType.HOUSING_COMPLEX,
        owner=owner,
        address="2 Oak Ave",
        city="Lviv",
        email="org2@test.com",
        phone="+380222222222",
    )
    OrganizationMembership.objects.create(user=owner, organization=org, role=OrgRole.DIRECTOR)
    return org


@pytest.fixture
def user_in_org1(db, org1):
    """Резидент org1."""
    user = User.objects.create_user(
        email="resident1@test.com",
        username="resident1",
        first_name="Alice",
        last_name="Resident",
        password="testpass123",
    )
    OrganizationMembership.objects.create(user=user, organization=org1, role=OrgRole.RESIDENT)
    return user


@pytest.fixture
def user_in_org2(db, org2):
    """Резидент org2."""
    user = User.objects.create_user(
        email="resident2@test.com",
        username="resident2",
        first_name="Bob",
        last_name="Resident",
        password="testpass123",
    )
    OrganizationMembership.objects.create(user=user, organization=org2, role=OrgRole.RESIDENT)
    return user


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="super@test.com",
        username="superuser",
        first_name="Super",
        last_name="User",
        password="testpass123",
    )


@pytest.fixture
def issue_in_org2(db, org2, user_in_org2):
    """Заявка, що належить org2."""
    return Issue.objects.create(
        title="Org2 Private Issue",
        description="Should not be visible to org1 users",
        organization=org2,
        reported_by=user_in_org2,
    )


# ── IDOR Tests ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestIssueIDORProtection:
    """Тести захисту від IDOR у IssueDetailAPIView, IssueUpdateAPIView, IssueDeleteAPIView."""

    def test_detail_cross_org_returns_404(self, user_in_org1, issue_in_org2):
        """GET /issues/<id>/ для заявки чужої орг → 404."""
        client = APIClient()
        client.force_authenticate(user=user_in_org1)
        response = client.get(f"/api/v1/issues/{issue_in_org2.id}/")
        assert response.status_code == 404, (
            f"Очікували 404, отримали {response.status_code}. "
            "IDOR: користувач бачить заявку з іншої організації!"
        )

    def test_update_cross_org_returns_404(self, user_in_org1, issue_in_org2):
        """PATCH /issues/update/<id>/ для заявки чужої орг → 404."""
        client = APIClient()
        client.force_authenticate(user=user_in_org1)
        response = client.patch(
            f"/api/v1/issues/update/{issue_in_org2.id}/",
            {"status": "accepted"},
            format="json",
        )
        assert response.status_code == 404, (
            f"Очікували 404, отримали {response.status_code}. "
            "IDOR: користувач може оновити заявку з іншої організації!"
        )

    def test_delete_cross_org_returns_404(self, user_in_org1, issue_in_org2):
        """DELETE /issues/delete/<id>/ для заявки чужої орг → 404."""
        client = APIClient()
        client.force_authenticate(user=user_in_org1)
        response = client.delete(f"/api/v1/issues/delete/{issue_in_org2.id}/")
        assert response.status_code == 404, (
            f"Очікували 404, отримали {response.status_code}. "
            "IDOR: користувач може видалити заявку з іншої організації!"
        )

    def test_detail_own_org_issue_accessible(self, user_in_org1, org1):
        """GET /issues/<id>/ для власної заявки → не 404 (403 або 200 залежно від ролі)."""
        own_issue = Issue.objects.create(
            title="Own Org Issue",
            description="This belongs to org1",
            organization=org1,
            reported_by=user_in_org1,
        )
        client = APIClient()
        client.force_authenticate(user=user_in_org1)
        response = client.get(f"/api/v1/issues/{own_issue.id}/")
        # Заявка з власної орг — не має повертати 404
        assert response.status_code != 404, (
            "Власна заявка не повинна повертати 404!"
        )

    def test_superuser_can_access_any_org_issue(self, superuser, issue_in_org2):
        """Суперюзер має доступ до заявок будь-якої організації."""
        client = APIClient()
        client.force_authenticate(user=superuser)
        response = client.get(f"/api/v1/issues/{issue_in_org2.id}/")
        # Суперюзер може бачити заявку (200 або 403 якщо немає доступу через get_object логіку)
        assert response.status_code != 404, (
            "Суперюзер не повинен отримувати 404 на заявках з будь-якої орг!"
        )

    def test_user_without_org_cannot_access_any_issue(self, db, issue_in_org2):
        """Користувач без членства в жодній організації отримує 404."""
        no_org_user = User.objects.create_user(
            email="noorg@test.com",
            username="noorguser",
            first_name="No",
            last_name="Org",
            password="testpass123",
        )
        client = APIClient()
        client.force_authenticate(user=no_org_user)
        response = client.get(f"/api/v1/issues/{issue_in_org2.id}/")
        assert response.status_code == 404
