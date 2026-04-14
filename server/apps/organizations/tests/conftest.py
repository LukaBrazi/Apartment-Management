# Imports
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model

from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrgRole,
    OrganizationType,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def mock_celery_notifications():
    """
    Мокаємо Celery-таск нотифікацій щоб уникнути підключення до RabbitMQ в тестах.
    Патчимо з tasks (де оголошено), бо в signals імпорт всередині функції.
    Застосовується до всіх тестів в organizations/tests/ автоматично.
    """
    with patch("apps.notifications.tasks.notify_dispatchers_new_issue.delay"):
        yield


# ── User Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def superadmin(db):
    """Fixture for superadmin user.

    Args:
        db: Django DB fixture.

    Returns:
        User: Superadmin user.
    """
    return User.objects.create_superuser(
        email="superadmin@test.com",
        username="superadmin",
        first_name="Super",
        last_name="Admin",
        password="testpass123",
    )


@pytest.fixture
def director_user(db):
    """Fixture for director user.

    Args:
        db: Django DB fixture.

    Returns:
        User: Director user.
    """
    return User.objects.create_user(
        email="director@test.com",
        username="director",
        first_name="John",
        last_name="Director",
        password="testpass123",
    )


@pytest.fixture
def admin_user(db):
    """Fixture for admin user.

    Args:
        db: Django DB fixture.

    Returns:
        User: Admin user.
    """
    return User.objects.create_user(
        email="admin@test.com",
        username="admin",
        first_name="Jane",
        last_name="Admin",
        password="testpass123",
    )


@pytest.fixture
def staff_user(db):
    """Fixture for staff user.

    Args:
        db: Django DB fixture.

    Returns:
        User: Staff user.
    """
    return User.objects.create_user(
        email="staff@test.com",
        username="staff",
        first_name="Bob",
        last_name="Staff",
        password="testpass123",
    )


@pytest.fixture
def resident_user(db):
    """Fixture for resident user.

    Args:
        db: Django DB fixture.

    Returns:
        User: Resident user.
    """
    return User.objects.create_user(
        email="resident@test.com",
        username="resident",
        first_name="Alice",
        last_name="Resident",
        password="testpass123",
    )


# ── Organization Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def org(db, director_user):
    """Fixture for organization with director membership.

    Args:
        db: Django DB fixture.
        director_user: Director user.

    Returns:
        Organization: Organization with director membership.
    """
    organization = Organization.objects.create(
        name="Test Complex",
        type=OrganizationType.HOUSING_COMPLEX,
        owner=director_user,
        address="123 Main St",
        city="Kyiv",
        description="Test residential complex",
        email="test@complex.com",
        phone="+380123456789",
    )

    # Create director membership
    OrganizationMembership.objects.create(
        user=director_user,
        organization=organization,
        role=OrgRole.DIRECTOR,
    )

    return organization


@pytest.fixture
def org_membership(db, org, resident_user):
    """Fixture for organization membership.

    Args:
        db: Django DB fixture.
        org: Organization.
        resident_user: Resident user.

    Returns:
        OrganizationMembership: Organization membership.
    """
    return OrganizationMembership.objects.create(
        user=resident_user,
        organization=org,
        role=OrgRole.RESIDENT,
    )


@pytest.fixture
def org_with_members(db, org, admin_user, staff_user, resident_user):
    """Fixture for organization with multiple members.

    Args:
        db: Django DB fixture.
        org: Organization.
        admin_user: Admin user.
        staff_user: Staff user.
        resident_user: Resident user.

    Returns:
        Organization: Organization with members.
    """
    OrganizationMembership.objects.create(
        user=admin_user,
        organization=org,
        role=OrgRole.ADMIN,
    )

    OrganizationMembership.objects.create(
        user=staff_user,
        organization=org,
        role=OrgRole.STAFF,
        staff_type="electrician",
    )

    OrganizationMembership.objects.create(
        user=resident_user,
        organization=org,
        role=OrgRole.RESIDENT,
    )

    return org


# ── Apartment Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def building(db, org):
    """Fixture for building.

    Args:
        db: Django DB fixture.
        org: Organization.

    Returns:
        Building: Building instance.
    """
    from apps.apartments.models import Building

    return Building.objects.create(
        name="Building A",
        address="123 Main St",
        city="Kyiv",
        organization=org,
    )


@pytest.fixture
def entrance(db, building):
    """Fixture for entrance.

    Args:
        db: Django DB fixture.
        building: Building instance.

    Returns:
        Entrance: Entrance instance.
    """
    from apps.apartments.models import Entrance

    return Entrance.objects.create(
        building=building,
        name="Entrance 1",
    )


@pytest.fixture
def unit(db, entrance):
    """Fixture for unit.

    Args:
        db: Django DB fixture.
        entrance: Entrance instance.

    Returns:
        Unit: Unit instance.
    """
    from apps.apartments.models import Unit

    return Unit.objects.create(
        entrance=entrance,
        number="101",
        floor=1,
    )
