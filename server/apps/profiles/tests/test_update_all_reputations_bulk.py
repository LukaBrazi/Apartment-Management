"""Regression test: ``update_all_reputations`` must use bulk_update.

Before PR-6 the task issued one UPDATE per profile (``profile.save()`` per
loop iteration).  With N profiles that meant 1 SELECT + N UPDATE round
trips.  After PR-6 the task uses ``Profile.objects.bulk_update`` so the
total stays at a small constant regardless of N.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.profiles.models import Profile
from apps.profiles.tasks import update_all_reputations

User = get_user_model()


@pytest.fixture
def ten_profiles_with_reports(db):
    """Create 10 users (auto-creates Profile via signal) and bump report_count."""
    profiles = []
    for i in range(10):
        u = User.objects.create_user(
            username=f"rep_perf_{i}",
            email=f"rep_perf_{i}@t.com",
            password="Test1234!",
            first_name=f"Rep{i}",
            last_name="Perf",
        )
        # Profile auto-created by signal — bump report_count so reputation
        # actually changes when update_reputation runs (otherwise nothing
        # to update and the assertion is trivially satisfied).
        Profile.objects.filter(user=u).update(report_count=i + 1, reputation=100)
        profiles.append(u.profile)
    return profiles


@pytest.mark.django_db
class TestUpdateAllReputationsBulk:
    def test_uses_bulk_update_constant_query_count(
        self, ten_profiles_with_reports, django_assert_max_num_queries
    ):
        """One SELECT + a small number of bulk UPDATEs — never N UPDATEs."""
        # Tight upper bound: 1 SELECT + 1 bulk UPDATE + savepoint frame.
        # If someone reverts to ``profile.save()`` per row the count grows
        # by N (10 here), blowing right past 5.
        with django_assert_max_num_queries(5):
            update_all_reputations()

        # Sanity: reputations were actually written.
        for profile in ten_profiles_with_reports:
            profile.refresh_from_db()
            expected = max(0, 100 - profile.report_count * 20)
            assert profile.reputation == expected
