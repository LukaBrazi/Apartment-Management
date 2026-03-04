"""Test that seed_demo management command runs and creates expected counts."""
import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_seed_demo_runs_and_creates_expected_data():
    from apps.apartments.models import Building, Entrance, Unit
    from apps.issues.models import Issue
    from apps.posts.models import Announcement
    from django.contrib.auth import get_user_model

    User = get_user_model()

    call_command("seed_demo", verbosity=0)

    # 1 building
    assert Building.objects.count() == 1
    # 2 entrances
    assert Entrance.objects.count() == 2
    # 20 units (10 per entrance)
    assert Unit.objects.count() == 20
    # 1 dispatcher + 3 residents = 4
    assert User.objects.count() == 4
    # 10 issues
    assert Issue.objects.count() == 10
    # 5 announcements
    assert Announcement.objects.count() == 5


@pytest.mark.django_db
def test_seed_demo_idempotent():
    """Running seed_demo twice should not create duplicates."""
    from apps.apartments.models import Building

    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", verbosity=0)

    assert Building.objects.count() == 1
