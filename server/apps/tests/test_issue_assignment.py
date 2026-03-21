"""Tests for issue assignment validation:
- Tenant cannot be assigned as issue executor
- Non-tenant profiles endpoint excludes tenants
- Worker can be assigned to an issue
"""
import pytest
from rest_framework.test import APIClient

from apps.profiles.models import Profile
from apps.tests.factories import (
    AdminUserFactory,
    IssueFactory,
    UserFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_client():
    client = APIClient()
    admin = AdminUserFactory()
    client.force_authenticate(user=admin)
    return client


def make_user_with_occupation(occupation: str):
    user = UserFactory()
    user.profile.occupation = occupation
    user.profile.save()
    return user


# ─── Issue Assignment ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestIssueAssignment:
    def _url(self, issue_id):
        return f"/api/v1/issues/admin/update/{issue_id}/"

    def test_worker_can_be_assigned_to_issue(self, admin_client):
        """Admin can assign a worker (non-tenant) to an issue."""
        issue = IssueFactory()
        worker = make_user_with_occupation("plumber")
        resp = admin_client.patch(
            self._url(issue.id),
            {"assigned_to_username": worker.username},
            format="json",
        )
        assert resp.status_code == 200
        issue.refresh_from_db()
        assert issue.assigned_to == worker

    def test_guard_can_be_assigned_to_issue(self, admin_client):
        """Admin can assign a guard to an issue."""
        issue = IssueFactory()
        guard = make_user_with_occupation("guard")
        resp = admin_client.patch(
            self._url(issue.id),
            {"assigned_to_username": guard.username},
            format="json",
        )
        assert resp.status_code == 200
        issue.refresh_from_db()
        assert issue.assigned_to == guard

    def test_tenant_cannot_be_assigned_to_issue(self, admin_client):
        """Tenant cannot be assigned as issue executor — returns 400 with Ukrainian message."""
        issue = IssueFactory()
        tenant = make_user_with_occupation("tenant")
        resp = admin_client.patch(
            self._url(issue.id),
            {"assigned_to_username": tenant.username},
            format="json",
        )
        assert resp.status_code == 400
        error_text = str(resp.json())
        assert "Мешканця" in error_text or "мешканця" in error_text

    def test_error_message_is_in_ukrainian(self, admin_client):
        """The error message for assigning a tenant must be in Ukrainian."""
        issue = IssueFactory()
        tenant = make_user_with_occupation("tenant")
        resp = admin_client.patch(
            self._url(issue.id),
            {"assigned_to_username": tenant.username},
            format="json",
        )
        assert resp.status_code == 400
        # Verify Ukrainian characters present in response
        import re
        error_text = str(resp.json())
        assert re.search(r"[а-яА-ЯіІїЇєЄґҐ]", error_text), (
            f"Error message not in Ukrainian: {error_text}"
        )

    def test_assigned_to_can_be_cleared(self, admin_client):
        """Admin can clear the assigned_to field (set to null)."""
        worker = make_user_with_occupation("electrician")
        issue = IssueFactory(assigned_to=worker)
        resp = admin_client.patch(
            self._url(issue.id),
            {"assigned_to_username": None},
            format="json",
        )
        assert resp.status_code == 200
        issue.refresh_from_db()
        assert issue.assigned_to is None

    def test_non_admin_cannot_assign_issue(self):
        """Non-admin cannot use the admin update endpoint."""
        issue = IssueFactory()
        worker = make_user_with_occupation("plumber")
        client = APIClient()
        tenant_user = make_user_with_occupation("tenant")
        client.force_authenticate(user=tenant_user)
        resp = client.patch(
            self._url(issue.id),
            {"assigned_to_username": worker.username},
            format="json",
        )
        assert resp.status_code == 403


# ─── Non-Tenant Profiles Endpoint ────────────────────────────────────────────


@pytest.mark.django_db
class TestNonTenantProfilesEndpoint:
    url = "/api/v1/profiles/non-tenant-profiles/"

    def test_endpoint_excludes_tenants(self, admin_client):
        """Non-tenant profiles endpoint must not return users with occupation=tenant."""
        tenant = make_user_with_occupation("tenant")
        worker = make_user_with_occupation("plumber")
        resp = admin_client.get(self.url)
        assert resp.status_code == 200
        data = resp.json()
        profiles = data.get("non_tenant_profiles", {}).get("results", [])
        usernames = [p["username"] for p in profiles]
        assert tenant.username not in usernames
        assert worker.username in usernames

    def test_endpoint_includes_workers(self, admin_client):
        """Non-tenant profiles endpoint returns workers of all non-tenant occupations."""
        occupations = ["plumber", "electrician", "mason", "guard"]
        workers = [make_user_with_occupation(occ) for occ in occupations]
        resp = admin_client.get(self.url)
        assert resp.status_code == 200
        data = resp.json()
        profiles = data.get("non_tenant_profiles", {}).get("results", [])
        usernames = {p["username"] for p in profiles}
        for w in workers:
            assert w.username in usernames

    def test_unauthenticated_cannot_access(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == 401
