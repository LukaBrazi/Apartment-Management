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
    client.user = tenant_user  # expose user for tests that reference client.user
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
        """Tenant→Tenant must be rejected with 403 (PermissionDenied in view)."""
        resp = self._create_rating(tenant_client, another_tenant_user)
        assert resp.status_code == 403, (
            f"Tenant rating another tenant must return 403 PermissionDenied. "
            f"Got {resp.status_code}: {resp.data}"
        )

    def test_duplicate_rating_rejected(self, tenant_client, worker_user):
        """
        Second rating on same worker must be rejected with 400
        (unique_together IntegrityError wrapped as ValidationError in the view).
        """
        resp1 = self._create_rating(tenant_client, worker_user, rating=5)
        assert resp1.status_code == 201

        resp2 = self._create_rating(tenant_client, worker_user, rating=4)
        assert resp2.status_code == 400, (
            f"Duplicate rating must return 400 ValidationError. "
            f"Got {resp2.status_code}: {resp2.data}"
        )

    def test_worker_cannot_rate_tenant(self, worker_user, tenant_user):
        """Worker→Tenant must be rejected with 403 (PermissionDenied in view)."""
        client = APIClient()
        client.force_authenticate(user=worker_user)

        resp = self._create_rating(client, tenant_user)
        assert resp.status_code == 403, (
            f"Worker rating a tenant must return 403 PermissionDenied. "
            f"Got {resp.status_code}: {resp.data}"
        )

    def test_worker_cannot_rate_self(self, worker_user):
        """Self-rating must be rejected with 403 at the `rating_user == rated_user` guard."""
        client = APIClient()
        client.force_authenticate(user=worker_user)

        resp = self._create_rating(client, worker_user)
        assert resp.status_code == 403, (
            f"Self-rating must return 403 PermissionDenied. "
            f"Got {resp.status_code}: {resp.data}"
        )

    def test_tenant_cannot_rate_self(self, tenant_client):
        """Self-rating must be rejected with 403 at the `rating_user == rated_user` guard."""
        resp = self._create_rating(tenant_client, tenant_client.user)
        assert resp.status_code == 403, (
            f"Tenant self-rating must return 403 PermissionDenied. "
            f"Got {resp.status_code}: {resp.data}"
        )

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
        Invalid rating values must be rejected with 400 ValidationError
        (raised by serializer choice/validator, not DB constraint).
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

            assert resp.status_code == 400, (
                f"Rating value {invalid_rating!r} must be rejected with 400, "
                f"got {resp.status_code}: {resp.data}"
            )

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
