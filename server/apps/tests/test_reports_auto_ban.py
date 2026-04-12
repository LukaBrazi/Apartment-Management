"""Tests for automatic user banning after 5 reports."""
import pytest
from rest_framework.test import APIClient

from apps.reports.models import Report
from apps.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client():
    client = APIClient()
    user = UserFactory(username="reporter_user")
    client.force_authenticate(user=user)
    client.user = user  # expose user for tests that reference client.user
    return client


@pytest.fixture
def reported_user():
    return UserFactory(username="target_user")


@pytest.mark.django_db
class TestReportsAutoBan:
    """Tests for automatic user banning after receiving 5 reports."""

    url = "/api/v1/reports/create/"

    def _create_report(self, client, reported_user, title=None, description=None):
        """Helper method to create a report."""
        title = title or "Test Report"
        description = description or "Test Description"

        resp = client.post(
            self.url,
            {
                "title": title,
                "description": description,
                "reported_user_username": reported_user.username,
            },
            format="json"
        )
        return resp

    def test_fifth_report_bans_user(self, authenticated_client, reported_user):
        """
        Test that a user is banned (is_active=False) after receiving 5 reports.
        """
        # Verify user starts active
        assert reported_user.is_active is True

        # Create 4 reports (no ban yet)
        for i in range(4):
            client = APIClient()
            reporter = UserFactory(username=f"reporter_{i}")
            client.force_authenticate(user=reporter)

            resp = self._create_report(client, reported_user, f"Report {i+1}")
            assert resp.status_code == 201

        # Verify user still active after 4 reports
        reported_user.refresh_from_db()
        assert reported_user.is_active is True
        assert reported_user.profile.report_count == 4

        # Create 5th report - should trigger ban
        client = APIClient()
        reporter_5 = UserFactory(username="reporter_final")
        client.force_authenticate(user=reporter_5)

        resp = self._create_report(client, reported_user, "Final Report")
        assert resp.status_code == 201

        # Verify user is NOW banned
        reported_user.refresh_from_db()
        assert reported_user.is_active is False, \
            "User should be banned (is_active=False) after 5 reports"
        assert reported_user.profile.report_count == 5

    def test_fourth_report_does_not_ban(self, reported_user):
        """
        Test that a user is NOT banned after receiving only 4 reports.
        """
        assert reported_user.is_active is True

        # Create 4 reports
        for i in range(4):
            client = APIClient()
            reporter = UserFactory(username=f"reporter_4_{i}")
            client.force_authenticate(user=reporter)

            resp = self._create_report(client, reported_user, f"Report {i+1}")
            assert resp.status_code == 201

        # Verify user is still active
        reported_user.refresh_from_db()
        assert reported_user.is_active is True, \
            "User should still be active after 4 reports"
        assert reported_user.profile.report_count == 4

    def test_self_report_rejected(self, authenticated_client):
        """
        Test that a user cannot report themselves.
        """
        reporter = authenticated_client.user

        resp = authenticated_client.post(
            self.url,
            {
                "title": "Self Report",
                "description": "Trying to report myself",
                "reported_user_username": reporter.username,
            },
            format="json"
        )

        # Should be rejected
        assert resp.status_code == 400, \
            "Self-report should be rejected with 400"

    def test_report_count_increments_correctly(self, reported_user):
        """
        Test that report_count in profile increments with each report.
        """
        assert reported_user.profile.report_count == 0

        for i in range(5):
            client = APIClient()
            reporter = UserFactory(username=f"reporter_count_{i}")
            client.force_authenticate(user=reporter)

            resp = self._create_report(client, reported_user, f"Report {i+1}")
            assert resp.status_code == 201

            reported_user.refresh_from_db()
            assert reported_user.profile.report_count == i + 1, \
                f"Report count should be {i+1} after {i+1} reports"

    def test_reputation_decreases_with_reports(self, reported_user):
        """
        Test that reputation decreases as reports accumulate.
        Reputation formula: max(0, 100 - report_count * 20)
        """
        initial_reputation = reported_user.profile.reputation
        assert initial_reputation == 100  # Default reputation

        # Create one report
        client = APIClient()
        reporter = UserFactory(username="rep_reporter")
        client.force_authenticate(user=reporter)
        resp = self._create_report(client, reported_user)
        assert resp.status_code == 201

        reported_user.refresh_from_db()
        # After 1 report: 100 - (1 * 20) = 80
        assert reported_user.profile.reputation == 80, \
            "Reputation should decrease by 20 per report"

    def test_multiple_reports_from_same_reporter_allowed(self, reported_user):
        """
        Test that the same reporter can create multiple reports against a user.
        (No duplicate constraint at API level)
        """
        client = APIClient()
        reporter = UserFactory(username="multi_reporter")
        client.force_authenticate(user=reporter)

        # Create multiple reports from same reporter
        for i in range(3):
            resp = self._create_report(
                client, reported_user,
                f"Report {i+1} from same reporter"
            )
            assert resp.status_code == 201

        reported_user.refresh_from_db()
        assert reported_user.profile.report_count == 3

    def test_unauthenticated_cannot_create_report(self, api_client, reported_user):
        """
        Test that unauthenticated users cannot create reports.
        """
        resp = api_client.post(
            self.url,
            {
                "title": "Anon Report",
                "description": "Anonymous report",
                "reported_user_username": reported_user.username,
            },
            format="json"
        )
        assert resp.status_code == 401
