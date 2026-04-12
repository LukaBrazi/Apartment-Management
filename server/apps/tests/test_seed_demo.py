"""Test that seed_demo management command runs and creates expected counts."""
import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_seed_demo_runs_and_creates_expected_data():
    from apps.apartments.models import Building, Entrance, Unit
    from apps.issues.models import Issue
    from apps.posts.models import Announcement
    from apps.news.models import News
    from django.contrib.auth import get_user_model

    User = get_user_model()

    call_command("seed_demo", verbosity=0)

    # 2 buildings (Будинок 1 + Будинок 2)
    assert Building.objects.count() == 2
    # 4 entrances (2 per building)
    assert Entrance.objects.count() == 4
    # 20 units (5 per entrance)
    assert Unit.objects.count() == 20
    # admin + dispatcher + guard + plumber + electrician + 1 tenant + 8 residents = 14
    assert User.objects.count() == 14
    # 15 service requests
    assert Issue.objects.count() == 15
    # 10 announcements
    assert Announcement.objects.count() == 10
    # 8 news articles
    assert News.objects.count() == 8


@pytest.mark.django_db
def test_seed_demo_idempotent():
    """Running seed_demo twice should not create duplicates."""
    from apps.apartments.models import Building
    from apps.issues.models import Issue

    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", verbosity=0)

    # Idempotent: second run uses get_or_create, no duplicates
    assert Building.objects.count() == 2
    assert Issue.objects.count() == 15
