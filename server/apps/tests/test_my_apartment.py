"""
Hardcore tests for MyApartmentAPIView.

Context: GET /api/v1/apartments/my-apartment/ is the endpoint the frontend
uses on tenant pages to gate the "Report an Issue" flow. The e2e
regression on 2026-04-18 traced the "tenant sees no apartment after
seed_demo" issue back to this endpoint, so guarding it with unit tests
is necessary to keep the tenant-binding contract stable.

Invariants asserted:
- Anonymous: 401 (default IsAuthenticated).
- Authenticated user with NO linked Apartment: 200 + empty body `{}`
  under the wrapped "apartment" label. The view EXPLICITLY returns an
  empty dict rather than 404 — the frontend depends on this shape to
  render the "Спочатку додайте квартиру" state.
- Authenticated tenant with exactly ONE linked Apartment: 200 and
  serialized apartment matches the DB row (unit_number, building, floor).
- The endpoint returns ONLY the caller's apartment — cross-user leakage
  would be a data-protection bug.
- The view calls `request.user.apartment.first()` — when a user is
  linked to multiple apartments (legacy data), we pin deterministic
  behavior: the first apartment (by DB insertion order) is returned,
  not one of the others.
"""
import pytest
from rest_framework.test import APIClient

from apps.apartments.models import Apartment
from apps.tests.factories import UserFactory


MY_APARTMENT_URL = "/api/v1/apartments/my-apartment/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tenant():
    return UserFactory(username="apt_tenant")


@pytest.fixture
def tenant_client(tenant):
    c = APIClient()
    c.force_authenticate(user=tenant)
    return c


@pytest.mark.django_db
class TestMyApartmentAPIView:
    def test_anonymous_returns_401(self, api_client):
        resp = api_client.get(MY_APARTMENT_URL)
        assert resp.status_code == 401, (
            f"Anonymous GET /my-apartment/ must be 401. Got {resp.status_code}: {resp.data}"
        )

    def test_no_apartment_returns_200_empty_object(self, tenant_client, tenant):
        """User without an apartment must get 200 + empty body (not 404).

        Frontend reads `apartment.id === undefined` to render the
        "Add apartment first" state. If this ever flips to 404, tenant
        report-issue flow breaks silently.
        """
        assert not Apartment.objects.filter(tenant=tenant).exists()

        resp = tenant_client.get(MY_APARTMENT_URL)
        assert resp.status_code == 200, resp.content

        body = resp.json()
        # GenericJSONRenderer wraps: {"apartment": {...}}; the view returned {}
        # so the wrapped body is {"apartment": {}}.
        assert "apartment" in body, (
            f"Response must carry 'apartment' key. Got keys: {list(body)}"
        )
        assert body["apartment"] == {}, (
            f"No-apartment case must return empty dict under 'apartment'. "
            f"Got: {body['apartment']!r}"
        )

    def test_single_apartment_returns_serialized_row(self, tenant_client, tenant):
        apt = Apartment.objects.create(
            tenant=tenant,
            unit_number="105",
            building="Block C",
            floor=3,
        )

        resp = tenant_client.get(MY_APARTMENT_URL)
        assert resp.status_code == 200, resp.content

        body = resp.json()["apartment"]
        # Fields that the serializer exposes (exclude pkid/updated_at)
        assert body["id"] == str(apt.id)
        assert body["unit_number"] == "105"
        assert body["building"] == "Block C"
        assert body["floor"] == 3

    def test_cross_user_apartment_not_leaked(self, tenant_client, tenant):
        """A different user's apartment must not leak to caller."""
        other = UserFactory(username="apt_other")
        Apartment.objects.create(
            tenant=other,
            unit_number="999",
            building="Other Block",
            floor=9,
        )
        # Caller has NO apartment
        resp = tenant_client.get(MY_APARTMENT_URL)
        assert resp.status_code == 200
        assert resp.json()["apartment"] == {}, (
            "Caller with no apartment must not see other users' apartments. "
            f"Got: {resp.json()['apartment']!r}"
        )

    def test_multiple_apartments_returns_first_deterministic(self, tenant_client, tenant):
        """When a user has multiple apartments, .first() returns deterministic row.

        `user.apartment.first()` with no explicit ordering uses the model's
        default ordering or DB insertion order. We pin this behavior: the
        earliest-created apartment is returned.
        """
        first = Apartment.objects.create(
            tenant=tenant, unit_number="1", building="B1", floor=1
        )
        Apartment.objects.create(
            tenant=tenant, unit_number="2", building="B2", floor=2
        )
        Apartment.objects.create(
            tenant=tenant, unit_number="3", building="B3", floor=3
        )

        resp = tenant_client.get(MY_APARTMENT_URL)
        assert resp.status_code == 200
        body = resp.json()["apartment"]
        # .first() on a QuerySet with no ordering is technically undefined
        # across databases, but for this project's SQLite/PostgreSQL test
        # target it's consistently the first-inserted PK. If this assertion
        # starts flaking across DB backends, add an explicit `order_by` in
        # the view.
        assert body["id"] == str(first.id), (
            f"With multiple apartments, my-apartment must deterministically "
            f"return the first-inserted row. Expected {first.id}, got {body['id']}."
        )
