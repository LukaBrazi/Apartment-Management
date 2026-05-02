"""Regression: admin-created contact must surface in public /contacts.

Bug — symptom: admin posts to /api/v1/site-settings/contacts/admin/
which pins ``organization=org_A`` via perform_create.  Then the
public /contacts page hits /api/v1/site-settings/ — that view used
to filter ``organization=request.organization``, but
``OrganizationMiddleware`` detects the org only from subdomain
(*.apartmentos.org) or ``X-Organization-Slug`` header.  An
authenticated tenant on the apex ``apartmentos.org`` got
``request.organization=None`` → filter ``organization=None`` →
admin's contact (organization=org_A) was invisible.

Fix: when the middleware returns no org but the caller is
authenticated, fall back to the user's primary org membership.
"""
import pytest
from rest_framework.test import APIClient

from apps.organizations.models import Organization, OrganizationMembership
from apps.site_settings.models import ContactPerson
from apps.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


def _membership(user, org, *, is_active=True, role="resident"):
    return OrganizationMembership.objects.create(
        user=user, organization=org, is_active=is_active, role=role
    )


@pytest.mark.django_db
class TestContactsVisibilityForAuthenticatedUser:
    list_url = "/api/v1/site-settings/"

    def test_member_sees_contacts_of_own_org_on_apex(self, api_client):
        """Authenticated tenant on apex (no subdomain) sees ОСББ's contacts."""
        org = Organization.objects.create(name="ЖК Сонце", slug="zhk-sun")
        contact = ContactPerson.objects.create(
            organization=org,
            name="Аварійна служба",
            role="emergency",
            is_emergency=True,
            is_active=True,
        )
        tenant = UserFactory(username="tenant_a")
        _membership(tenant, org)
        api_client.force_authenticate(user=tenant)

        resp = api_client.get(self.list_url)
        assert resp.status_code == 200, resp.content
        body = resp.json()["site_settings"]
        names = [c["name"] for c in body["contacts"]]
        assert contact.name in names

    def test_non_member_does_not_see_other_orgs_contacts(self, api_client):
        org_a = Organization.objects.create(name="ЖК Місяць", slug="zhk-moon")
        org_b = Organization.objects.create(name="ЖК Зорі", slug="zhk-star")
        ContactPerson.objects.create(
            organization=org_a,
            name="Тільки для A",
            role="emergency",
            is_active=True,
        )
        outsider = UserFactory(username="outsider")
        _membership(outsider, org_b)  # member of B, not A
        api_client.force_authenticate(user=outsider)

        resp = api_client.get(self.list_url)
        body = resp.json()["site_settings"]
        names = [c["name"] for c in body["contacts"]]
        assert "Тільки для A" not in names

    def test_inactive_contact_filtered_out(self, api_client):
        org = Organization.objects.create(name="ЖК Тест", slug="zhk-test")
        ContactPerson.objects.create(
            organization=org,
            name="Деактивований",
            role="emergency",
            is_active=False,
        )
        tenant = UserFactory(username="tenant_test")
        _membership(tenant, org)
        api_client.force_authenticate(user=tenant)

        resp = api_client.get(self.list_url)
        body = resp.json()["site_settings"]
        names = [c["name"] for c in body["contacts"]]
        assert "Деактивований" not in names

    def test_anonymous_apex_visitor_sees_only_platform_contacts(self, api_client):
        """Unauthenticated visitor on bare apex — only org=None contacts."""
        platform = ContactPerson.objects.create(
            organization=None,
            name="Платформенна підтримка",
            role="other",
            is_active=True,
        )
        org = Organization.objects.create(name="ЖК Невидимий", slug="hidden")
        ContactPerson.objects.create(
            organization=org,
            name="Не для анонімів",
            role="emergency",
            is_active=True,
        )

        resp = api_client.get(self.list_url)
        body = resp.json()["site_settings"]
        names = [c["name"] for c in body["contacts"]]
        assert platform.name in names
        assert "Не для анонімів" not in names

    def test_authenticated_without_membership_sees_only_platform(self, api_client):
        """Edge case: super-tenant with no active org → platform-only."""
        ContactPerson.objects.create(
            organization=None, name="Глобальний", role="other", is_active=True
        )
        org = Organization.objects.create(name="ЖК Без зв'язку", slug="no-link")
        ContactPerson.objects.create(
            organization=org, name="Org-only", role="emergency", is_active=True
        )
        floater = UserFactory(username="floater")
        # No membership at all.
        api_client.force_authenticate(user=floater)

        resp = api_client.get(self.list_url)
        body = resp.json()["site_settings"]
        names = [c["name"] for c in body["contacts"]]
        assert "Глобальний" in names
        assert "Org-only" not in names
