"""Regression tests for /api/v1/reports/my-reports/.

Frontend → backend URL mismatch (PR-19): RTK Query was hitting
``/reports/me/`` but Django routed only ``/reports/my-reports/``.
The 404 was silently swallowed by the cache layer → list looked empty
even though the create succeeded.

These tests pin two invariants:
1. URL path ``/reports/my-reports/`` resolves to ``ReportListAPIView``.
2. After a successful POST to ``/reports/create/`` the same user gets
   the report back from ``GET /reports/my-reports/``.
"""
import pytest
from django.urls import resolve
from rest_framework.test import APIClient

from apps.reports.views import ReportListAPIView
from apps.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestMyReportsURLContract:
    """Lock-down — frontend `getMyReports` must hit a real backend route."""

    def test_my_reports_path_resolves_to_list_view(self):
        match = resolve("/api/v1/reports/my-reports/")
        assert match.func.view_class is ReportListAPIView

    def test_legacy_me_path_does_not_exist(self):
        # Defensive: the old ``/reports/me/`` URL must NOT silently
        # come back, otherwise the regression returns.
        from django.urls.exceptions import Resolver404

        with pytest.raises(Resolver404):
            resolve("/api/v1/reports/me/")


@pytest.mark.django_db
class TestMyReportsAfterCreate:
    """Regression — create then list must include the new report."""

    create_url = "/api/v1/reports/create/"
    list_url = "/api/v1/reports/my-reports/"

    def test_created_report_visible_in_my_reports_list(self, api_client):
        reporter = UserFactory(username="alice")
        target = UserFactory(username="bob")
        api_client.force_authenticate(user=reporter)

        create_resp = api_client.post(
            self.create_url,
            {
                "reported_user_username": target.username,
                "title": "Шумить уночі",
                "description": "Сусід грає на барабанах о 02:00.",
            },
            format="json",
        )
        assert create_resp.status_code == 201, create_resp.content

        list_resp = api_client.get(self.list_url)
        assert list_resp.status_code == 200, list_resp.content

        # Generic renderer wraps payload in ``{"report": ...}`` (object_label).
        # The list view returns a paginated/array body — peel both shapes.
        body = list_resp.json()
        if isinstance(body, dict):
            results = body.get("report") or body.get("reports") or body
        else:
            results = body

        if isinstance(results, dict) and "results" in results:
            results = results["results"]

        titles = [r.get("title") for r in results]
        assert "Шумить уночі" in titles, (
            f"Created report not surfaced in /my-reports/. Body: {body}"
        )
