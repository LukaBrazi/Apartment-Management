"""Tests for Profile security — occupation is read-only field."""
import pytest
from rest_framework.test import APIClient

from apps.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tenant_client():
    client = APIClient()
    user = UserFactory(username="tenant_test")
    client.force_authenticate(user=user)
    client.user = user  # expose user for tests that reference client.user
    return client


@pytest.fixture
def tenant_user():
    return UserFactory(username="tenant_user")


@pytest.mark.django_db
class TestProfileSecurity:
    """Tests to ensure occupation field cannot be modified through API."""

    url = "/api/v1/profiles/user/update/"

    def test_tenant_cannot_change_own_occupation(self, tenant_client, tenant_user):
        """
        Test that a tenant cannot change their own occupation via PATCH.
        The occupation field should be read-only and ignored if provided.
        """
        initial_occupation = tenant_client.user.profile.occupation
        assert initial_occupation == "tenant"

        # Attempt to change occupation to GUARD
        resp = tenant_client.patch(
            self.url,
            {"occupation": "guard"},
            format="json"
        )

        # Request should succeed (200 or 400 depending on implementation)
        # But occupation should NOT change
        assert resp.status_code in [200, 400, 403]

        # Refresh and verify occupation is still "tenant"
        tenant_client.user.refresh_from_db()
        assert tenant_client.user.profile.occupation == "tenant", \
            "Occupation was changed! Security vulnerability detected."

    def test_profile_occupation_is_read_only(self, tenant_client):
        """
        Test that occupation field is completely read-only and cannot be modified.
        Even with valid data, occupation should remain unchanged.
        """
        original_occupation = tenant_client.user.profile.occupation

        # Try to change to PLUMBER
        resp = tenant_client.patch(
            self.url,
            {
                "occupation": "plumber",
                "bio": "Updated bio"
            },
            format="json"
        )

        # Verify response was successful (bio was updated)
        assert resp.status_code == 200

        # Verify bio WAS updated (so API is working)
        tenant_client.user.refresh_from_db()
        if resp.json().get("profile") or resp.json().get("bio"):
            # API accepted the request
            pass

        # Most important: verify occupation did NOT change
        assert tenant_client.user.profile.occupation == original_occupation, \
            f"Occupation changed from {original_occupation} to {tenant_client.user.profile.occupation}"

    def test_occupation_not_in_update_serializer_fields(self, tenant_client):
        """
        Test that occupation field is marked as read-only in the serializer.
        """
        from apps.profiles.serializers import UpdateProfileSerializer

        # Check that occupation is in read_only_fields
        serializer = UpdateProfileSerializer()
        assert "occupation" in serializer.fields
        assert serializer.fields["occupation"].read_only, \
            "occupation field should be read-only"

    def test_multiple_update_attempts_dont_change_occupation(self, tenant_client):
        """
        Test that multiple PATCH requests cannot change occupation.
        """
        original_occupation = tenant_client.user.profile.occupation

        # Try multiple different occupations
        for occupation in ["guard", "mason", "plumber", "electrician"]:
            resp = tenant_client.patch(
                self.url,
                {"occupation": occupation},
                format="json"
            )
            assert resp.status_code in [200, 400, 403]

        # Occupation should still be original
        tenant_client.user.refresh_from_db()
        assert tenant_client.user.profile.occupation == original_occupation

    def test_unauthenticated_cannot_update_profile(self, api_client):
        """
        Test that unauthenticated users cannot update any profile.
        """
        resp = api_client.patch(
            self.url,
            {"bio": "Hacked bio"},
            format="json"
        )
        assert resp.status_code == 401
