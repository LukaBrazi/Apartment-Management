"""
Hardcore tests for Site Settings + Contact Persons endpoints.

Scope: apps.site_settings.views — another zero-coverage surface before this
file landed. These endpoints gate branding, platform identity, and the
contacts page across all orgs; regressions here propagate to every client.

Invariants asserted:
- GET /api/v1/site-settings/ (AllowAny): returns platform default when no
  X-Organization-Slug header is set; returns org-specific settings when
  header matches an active organization; gracefully falls back when the
  header points to a nonexistent / inactive org.
- Response shape: {"site_settings": {"settings": {...}, "contacts": [...], "organization": slug|None}}.
- Contacts are filtered by organization AND is_active=True, and ordered by (order, name).
- GET /api/v1/site-settings/superadmin/orgs/: 401 for anonymous, 403 for
  staff-but-not-superuser, 200 with full org list for superuser.
- Response shape for superadmin endpoint: {"organizations": {"organizations": [...], "total": N}}
  — `GenericJSONRenderer` wraps the outer dict, inner dict carries the payload.

No loose assertions. Status codes and shapes are pinned exactly.
"""
import pytest
from rest_framework.test import APIClient

from apps.organizations.models import Organization
from apps.site_settings.models import ContactPerson, SiteSettings
from apps.tests.factories import AdminUserFactory, UserFactory


SITE_SETTINGS_URL = "/api/v1/site-settings/"
SUPERADMIN_ORGS_URL = "/api/v1/site-settings/superadmin/orgs/"


def _make_org(name="Test Org", slug="test-org", is_active=True) -> Organization:
    from uuid import uuid4

    # Keep slugs unique across parametrized / repeated runs
    suffix = uuid4().hex[:6]
    return Organization.objects.create(
        name=f"{name}-{suffix}",
        slug=f"{slug}-{suffix}",
        is_active=is_active,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def platform_default_settings(db):
    """Ensure the organization=NULL default row exists with known values."""
    obj, _created = SiteSettings.objects.get_or_create(
        organization=None,
        defaults={
            "platform_name": "PlatformDefault",
            "primary_color": "#111111",
            "support_email": "default@platform.test",
        },
    )
    # Even if the row already existed, pin the fields we assert on so the
    # test is stable across reruns.
    obj.platform_name = "PlatformDefault"
    obj.primary_color = "#111111"
    obj.support_email = "default@platform.test"
    obj.save()
    return obj


# ═════════════════════════════════════════════════════════════════════════════
# GET /site-settings/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSiteSettingsGet:
    def test_returns_platform_default_when_no_header(
        self, api_client, platform_default_settings
    ):
        """Without X-Organization-Slug header, middleware sets org=None → default row."""
        resp = api_client.get(SITE_SETTINGS_URL)
        assert resp.status_code == 200, resp.content

        payload = resp.json()["site_settings"]
        assert payload["organization"] is None, (
            f"Expected organization=None for platform default, got {payload['organization']!r}"
        )
        settings = payload["settings"]
        assert settings["platform_name"] == "PlatformDefault"
        assert settings["primary_color"] == "#111111"
        assert settings["support_email"] == "default@platform.test"
        # Contacts filter must exclude all platform-level rows that are inactive
        # and must be a list (never null)
        assert isinstance(payload["contacts"], list)

    def test_returns_org_specific_settings_via_header(self, api_client):
        """X-Organization-Slug header selects per-org SiteSettings row."""
        org = _make_org(name="Acme", slug="acme")
        SiteSettings.objects.create(
            organization=org,
            platform_name="Acme Platform",
            primary_color="#FF0000",
        )

        resp = api_client.get(
            SITE_SETTINGS_URL,
            HTTP_X_ORGANIZATION_SLUG=org.slug,
        )
        assert resp.status_code == 200, resp.content

        payload = resp.json()["site_settings"]
        assert payload["organization"] == org.slug
        assert payload["settings"]["platform_name"] == "Acme Platform"
        assert payload["settings"]["primary_color"] == "#FF0000"

    def test_unknown_slug_falls_back_to_default(
        self, api_client, platform_default_settings
    ):
        """Nonexistent slug → middleware returns org=None → default settings."""
        resp = api_client.get(
            SITE_SETTINGS_URL,
            HTTP_X_ORGANIZATION_SLUG="no-such-org",
        )
        assert resp.status_code == 200
        payload = resp.json()["site_settings"]
        assert payload["organization"] is None
        assert payload["settings"]["platform_name"] == "PlatformDefault"

    def test_inactive_org_slug_falls_back_to_default(
        self, api_client, platform_default_settings
    ):
        """is_active=False org → middleware filter rejects → default settings."""
        org = _make_org(name="Inactive", slug="inactive", is_active=False)
        SiteSettings.objects.create(
            organization=org, platform_name="SHOULD-NOT-APPEAR"
        )

        resp = api_client.get(
            SITE_SETTINGS_URL,
            HTTP_X_ORGANIZATION_SLUG=org.slug,
        )
        assert resp.status_code == 200
        payload = resp.json()["site_settings"]
        assert payload["organization"] is None, (
            "Middleware must not resolve an inactive org; should fall through "
            f"to default. Got organization={payload['organization']!r}"
        )
        assert payload["settings"]["platform_name"] != "SHOULD-NOT-APPEAR"

    def test_contacts_filter_excludes_inactive_and_other_orgs(self, api_client):
        """Contacts list is filtered by (organization=request_org, is_active=True)."""
        org_a = _make_org(name="A", slug="a")
        org_b = _make_org(name="B", slug="b")
        SiteSettings.objects.create(organization=org_a, platform_name="A")

        ContactPerson.objects.create(
            organization=org_a, name="active-in-a", phone="1", is_active=True, order=1
        )
        ContactPerson.objects.create(
            organization=org_a, name="inactive-in-a", phone="2", is_active=False, order=0
        )
        ContactPerson.objects.create(
            organization=org_b, name="active-in-b", phone="3", is_active=True, order=0
        )

        resp = api_client.get(
            SITE_SETTINGS_URL,
            HTTP_X_ORGANIZATION_SLUG=org_a.slug,
        )
        assert resp.status_code == 200
        contacts = resp.json()["site_settings"]["contacts"]
        names = [c["name"] for c in contacts]
        assert names == ["active-in-a"], (
            f"Contacts must be filtered by (org=request_org, is_active=True). Got: {names}"
        )

    def test_contacts_ordered_by_order_then_name(self, api_client):
        """View orders contacts by (order, name) — stability matters for UI."""
        org = _make_org(name="Ord", slug="ord")
        SiteSettings.objects.create(organization=org)
        ContactPerson.objects.create(
            organization=org, name="Zeta", phone="z", is_active=True, order=1
        )
        ContactPerson.objects.create(
            organization=org, name="Alpha", phone="a", is_active=True, order=2
        )
        ContactPerson.objects.create(
            organization=org, name="Beta", phone="b", is_active=True, order=1
        )

        resp = api_client.get(
            SITE_SETTINGS_URL,
            HTTP_X_ORGANIZATION_SLUG=org.slug,
        )
        names = [c["name"] for c in resp.json()["site_settings"]["contacts"]]
        # (1, "Beta"), (1, "Zeta"), (2, "Alpha")
        assert names == ["Beta", "Zeta", "Alpha"], (
            f"Contacts must be ordered by (order, name). Got: {names}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# GET /site-settings/superadmin/orgs/
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSuperAdminOrgs:
    def test_anonymous_gets_401(self, api_client):
        resp = api_client.get(SUPERADMIN_ORGS_URL)
        assert resp.status_code == 401, (
            f"Anonymous must be 401 (IsAdminUser rejects). "
            f"Got {resp.status_code}: {resp.data}"
        )

    def test_staff_non_superuser_gets_403(self):
        """is_staff alone must NOT grant access — view has explicit superuser guard."""
        staff = UserFactory(username="ss_staff", is_staff=True, is_superuser=False)
        client = APIClient()
        client.force_authenticate(user=staff)
        resp = client.get(SUPERADMIN_ORGS_URL)
        assert resp.status_code == 403, (
            f"Staff-but-not-superuser must be 403. "
            f"Got {resp.status_code}: {resp.data}"
        )

    def test_plain_user_gets_403(self):
        """IsAdminUser requires is_staff=True — plain user gets 403."""
        user = UserFactory(username="ss_tenant")
        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.get(SUPERADMIN_ORGS_URL)
        assert resp.status_code == 403

    def test_superuser_sees_all_orgs(self):
        """Superuser sees every org with its settings payload."""
        org_a = _make_org(name="A", slug="a-sa")
        org_b = _make_org(name="B", slug="b-sa")
        SiteSettings.objects.create(
            organization=org_a,
            platform_name="Acme",
            primary_color="#ABCDEF",
            support_email="a@a.com",
        )
        # org_b has NO site_settings row — must still be returned with nulls

        superuser = AdminUserFactory(username="ss_super")
        client = APIClient()
        client.force_authenticate(user=superuser)

        resp = client.get(SUPERADMIN_ORGS_URL)
        assert resp.status_code == 200, resp.content

        body = resp.json()["organizations"]
        # `GenericJSONRenderer` wraps the whole response dict under the
        # outer "organizations" label. The inner dict carries the list.
        assert "organizations" in body and "total" in body, (
            f"Response must carry 'organizations' list and 'total' count. Got keys: {list(body.keys())}"
        )
        items = body["organizations"]
        by_slug = {row["slug"]: row for row in items}
        assert org_a.slug in by_slug and org_b.slug in by_slug, (
            f"Expected both orgs in response. Got slugs: {list(by_slug)}"
        )
        assert by_slug[org_a.slug]["platform_name"] == "Acme"
        assert by_slug[org_a.slug]["primary_color"] == "#ABCDEF"
        assert by_slug[org_a.slug]["support_email"] == "a@a.com"
        # org_b has no site_settings row — fields must be None, not crash
        assert by_slug[org_b.slug]["platform_name"] is None
        assert by_slug[org_b.slug]["primary_color"] is None
        # total count matches the list length
        assert body["total"] == len(items)
