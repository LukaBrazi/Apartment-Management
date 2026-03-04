"""Smoke tests — project loads and basic User creation works."""
import pytest
from django.contrib.auth import get_user_model

from apps.tests.factories import UserFactory

User = get_user_model()


@pytest.mark.django_db
def test_project_loads():
    """Django can create the test DB and we can query User table."""
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_create_user_via_factory():
    user = UserFactory()
    assert user.pk is not None
    assert "@" in user.email


@pytest.mark.django_db
def test_create_admin_user():
    from apps.tests.factories import AdminUserFactory
    admin = AdminUserFactory()
    assert admin.is_staff
    assert admin.is_superuser


@pytest.mark.django_db
def test_user_full_name():
    user = UserFactory(first_name="Іван", last_name="Петренко")
    assert user.full_name == "Іван Петренко"
