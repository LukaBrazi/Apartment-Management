"""Tests for rating permissions — tenants rating workers, duplicate prevention."""
import pytest
from rest_framework.test import APIClient

from apps.ratings.models import Rating
from apps.profiles.models import Profile
from apps.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tenant_user():
    """Create a tenant user."""
    return UserFactory(username="tenant_rating")


@pytest.fixture
def tenant_client(tenant_user):
    """Create authenticated client for a tenant."""
    client = APIClient()
    client.force_authenticate(user=tenant_user)
    return client


@pytest.fixture
def worker_user():
    """Create a worker user (plumber)."""
    worker = UserFactory(username="plumber_worker")
    worker.profile.occupation = Profile.Occupation.PLUMBER
    worker.profile.save()
    return worker


@pytest.fixture
def another_tenant_user():
    """Create another tenant user."""
    return UserFactory(username="another_tenant")


@pytest.mark.django_db
class TestRatingsPermissions:
    """Tests for rating permissions and constraints."""

    url = "/api/v1/ratings/create/"

    def _create_rating(self, client, rated_user, rating=5, comment="Good work"):
        """Helper method to create a rating."""
        resp = client.post(
            self.url,
            {
                "rated_user_username": rated_user.username,
                "rating": rating,
                "comment": comment,
            },
            format="json"
        )
        return resp

    def test_tenant_can_rate_worker(self, tenant_client, worker_user):
        """
        Test that a tenant can rate a worker (e.g., plumber).
        Should return 201 Created.
        """
        resp = self._create_rating(tenant_client, worker_user, rating=5)
        assert resp.status_code == 201, \
            f"Tenant should be able to rate a worker. Response: {resp.data}"

        # Verify rating was created
        assert Rating.objects.filter(
            rating_user=tenant_client.user,
            rated_user=worker_user,
            rating=5
        ).exists()

    def test_tenant_cannot_rate_tenant(self, tenant_client, another_tenant_user):
        """
        Test that a tenant cannot rate another tenant.
        Should return 403 Forbidden or permission denied error.
        """
        resp = self._create_rating(tenant_client, another_tenant_user)

        # Should be rejected
        assert resp.status_code in [403, 400], \
            f"Tenant should NOT be able to rate another tenant. Got {resp.status_code}: {resp.data}"

    def test_duplicate_rating_rejected(self, tenant_client, worker_user):
        """
        Test that a tenant cannot rate the same worker twice.
        The second rating should be rejected (unique_together constraint).
        """
        # Create first rating
        resp1 = self._create_rating(tenant_client, worker_user, rating=5)
        assert resp1.status_code == 201

        # Attempt duplicate rating
        resp2 = self._create_rating(tenant_client, worker_user, rating=4)

        # Should be rejected due to unique_together constraint
        assert resp2.status_code in [400, 409], \
            f"Duplicate rating should be rejected. Got {resp2.status_code}: {resp2.data}"

    def test_worker_cannot_rate_tenant(self, worker_user, tenant_user):
        """
        Test that a worker cannot rate a tenant.
        Workers can only be rated by tenants, not the other way around.
        """
        client = APIClient()
        client.force_authenticate(user=worker_user)

        resp = self._create_rating(client, tenant_user)

        # Should be rejected
        assert resp.status_code in [403, 400], \
            f"Worker should NOT be able to rate a tenant. Got {resp.status_code}"

    def test_worker_cannot_rate_self(self, worker_user):
        """
        Test that a worker cannot rate themselves.
        """
        client = APIClient()
        client.force_authenticate(user=worker_user)

        resp = self._create_rating(client, worker_user)

        # Should be rejected
        assert resp.status_code in [403, 400], \
            f"User should NOT be able to rate themselves. Got {resp.status_code}"

    def test_tenant_cannot_rate_self(self, tenant_client):
        """
        Test that a tenant cannot rate themselves.
        """
        resp = self._create_rating(tenant_client, tenant_client.user)

        # Should be rejected
        assert resp.status_code in [403, 400], \
            f"Tenant should NOT be able to rate themselves. Got {resp.status_code}"

    def test_rating_with_invalid_user(self, tenant_client):
        """
        Test that rating a non-existent user is rejected.
        """
        resp = tenant_client.post(
            self.url,
            {
                "rated_user_username": "nonexistent_user_12345",
                "rating": 5,
                "comment": "Test",
            },
            format="json"
        )

        assert resp.status_code == 404, \
            "Rating non-existent user should return 404"

    def test_rating_with_valid_comment(self, tenant_client, worker_user):
        """
        Test that a rating can include a comment.
        """
        comment = "Great work on the plumbing repairs"
        resp = self._create_rating(
            tenant_client, worker_user,
            rating=5, comment=comment
        )

        assert resp.status_code == 201
        rating = Rating.objects.get(
            rating_user=tenant_client.user,
            rated_user=worker_user
        )
        assert rating.comment == comment

    def test_rating_with_all_star_values(self, tenant_client, worker_user):
        """
        Test that all valid rating values (1-5) are accepted.
        """
        for rating_value in [1, 2, 3, 4, 5]:
            # Create new worker for each rating to avoid duplicate constraint
            worker = UserFactory(username=f"worker_{rating_value}")
            worker.profile.occupation = Profile.Occupation.ELECTRICIAN
            worker.profile.save()

            resp = self._create_rating(
                tenant_client, worker,
                rating=rating_value
            )

            assert resp.status_code == 201, \
                f"Rating value {rating_value} should be accepted"

    def test_invalid_rating_value_rejected(self, tenant_client, worker_user):
        """
        Test that invalid rating values are rejected.
        Valid values are 1-5 only.
        """
        for invalid_rating in [0, 6, 10, -1, 2.5]:
            resp = tenant_client.post(
                self.url,
                {
                    "rated_user_username": worker_user.username,
                    "rating": invalid_rating,
                    "comment": "Invalid",
                },
                format="json"
            )

            assert resp.status_code in [400, 409], \
                f"Rating value {invalid_rating} should be rejected"

    def test_unauthenticated_cannot_rate(self, api_client, worker_user):
        """
        Test that unauthenticated users cannot create ratings.
        """
        resp = api_client.post(
            self.url,
            {
                "rated_user_username": worker_user.username,
                "rating": 5,
                "comment": "Test",
            },
            format="json"
        )

        assert resp.status_code == 401, \
            "Unauthenticated user should not be able to rate"

    def test_average_rating_updates_after_rating(self, tenant_client, worker_user):
        """
        Test that the worker's average rating is correctly calculated after receiving ratings.
        """
        # Create multiple ratings
        ratings_list = [5, 4, 3, 5]

        for i, rating_val in enumerate(ratings_list):
            # Create new tenant for each rating
            tenant = UserFactory(username=f"tenant_rate_{i}")
            client = APIClient()
            client.force_authenticate(user=tenant)

            resp = self._create_rating(client, worker_user, rating=rating_val)
            assert resp.status_code == 201

        # Verify average rating
        worker_user.refresh_from_db()
        avg_rating = worker_user.profile.get_average_rating()

        # Expected average: (5 + 4 + 3 + 5) / 4 = 4.25
        expected_avg = sum(ratings_list) / len(ratings_list)
        assert abs(avg_rating - expected_avg) < 0.01, \
            f"Average rating should be {expected_avg}, got {avg_rating}"
