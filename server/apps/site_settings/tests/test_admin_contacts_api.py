"""PR-15 — Admin Contacts CRUD endpoints.

Endpoints under test:
  POST   /api/v1/site-settings/contacts/admin/
  GET    /api/v1/site-settings/contacts/admin/
  PATCH  /api/v1/site-settings/contacts/admin/<id>/
  DELETE /api/v1/site-settings/contacts/admin/<id>/

Covers:
  * Org auto-pin on create (Bug 1 prevention from PR-14).
  * List queryset scoped to caller's orgs.
  * PATCH renaming.
  * DELETE 204.
  * Cross-org isolation: staff in org B cannot mutate org A contact (404).
  * Lock-down: ``AdminContactPersonSerializer.Meta.fields`` does NOT
    contain ``organization`` writable (file-level regex check).
"""
import re
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationType,
    OrgRole,
)
from apps.site_settings.models import ContactPerson

User = get_user_model()

ADMIN_LIST_URL = "/api/v1/site-settings/contacts/admin/"


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def org_a(db):
    owner = User.objects.create_user(
        email="contacts_owner_a@test.com",
        username="contacts_owner_a",
        first_name="Owner",
        last_name="A",
        password="testpass123",
    )
    organization = Organization.objects.create(
        name="Contacts Org A",
        type=OrganizationType.HOUSING_COMPLEX,
        owner=owner,
        address="Addr A",
        city="Kyiv",
        email="contacts_a@test.com",
        phone="+380101010101",
    )
    OrganizationMembership.objects.create(
        user=owner, organization=organization, role=OrgRole.DIRECTOR
    )
    return organization


@pytest.fixture
def org_b(db):
    owner = User.objects.create_user(
        email="contacts_owner_b@test.com",
        username="contacts_owner_b",
        first_name="Owner",
        last_name="B",
        password="testpass123",
    )
    organization = Organization.objects.create(
        name="Contacts Org B",
        type=OrganizationType.HOUSING_COMPLEX,
        owner=owner,
        address="Addr B",
        city="Lviv",
        email="contacts_b@test.com",
        phone="+380202020202",
    )
    OrganizationMembership.objects.create(
        user=owner, organization=organization, role=OrgRole.DIRECTOR
    )
    return organization


@pytest.fixture
def staff_a(db, org_a):
    user = User.objects.create_user(
        email="staff_a@test.com",
        username="staff_a",
        first_name="Staff",
        last_name="A",
        password="testpass123",
    )
    user.is_staff = True
    user.save()
    OrganizationMembership.objects.create(
        user=user, organization=org_a, role=OrgRole.STAFF
    )
    return user


@pytest.fixture
def staff_b(db, org_b):
    user = User.objects.create_user(
        email="staff_b@test.com",
        username="staff_b",
        first_name="Staff",
        last_name="B",
        password="testpass123",
    )
    user.is_staff = True
    user.save()
    OrganizationMembership.objects.create(
        user=user, organization=org_b, role=OrgRole.STAFF
    )
    return user


@pytest.fixture
def tenant(db, org_a):
    user = User.objects.create_user(
        email="contacts_tenant@test.com",
        username="contacts_tenant",
        first_name="Tenant",
        last_name="Plain",
        password="testpass123",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org_a, role=OrgRole.RESIDENT
    )
    return user


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminContactCreate:
    def _payload(self, **overrides):
        base = {
            "name": "Іван Петренко",
            "role": "manager",
            "position": "Управитель",
            "phone": "+380501112233",
            "email": "ivan@example.com",
            "telegram": "ivan_pm",
            "working_hours": "Пн-Пт 09:00-18:00",
            "is_emergency": False,
            "is_active": True,
        }
        base.update(overrides)
        return base

    def test_admin_contact_create_assigns_organization(self, staff_a, org_a):
        """Bug 1 prevention: created contact is auto-pinned to caller's org
        and immediately visible in the LIST response.
        """
        client = APIClient()
        client.force_authenticate(user=staff_a)

        response = client.post(ADMIN_LIST_URL, self._payload(), format="json")
        assert response.status_code in (200, 201), response.content

        contact = ContactPerson.objects.get(name="Іван Петренко")
        assert contact.organization_id == org_a.pkid, (
            "New contact must be auto-pinned to the caller's first active org"
        )

        list_response = client.get(ADMIN_LIST_URL)
        assert list_response.status_code == 200
        body = list_response.json()
        ids = self._extract_ids(body)
        assert str(contact.id) in ids or contact.id in ids

    def test_admin_contact_create_ignores_organization_in_payload(
        self, staff_a, org_a, org_b
    ):
        """Even if a malicious staff user passes ``organization=<other>``
        in the body, it must be ignored — pinning is server-side.
        """
        client = APIClient()
        client.force_authenticate(user=staff_a)

        payload = self._payload(name="Spoof Attempt")
        payload["organization"] = str(org_b.id)
        response = client.post(ADMIN_LIST_URL, payload, format="json")
        assert response.status_code in (200, 201)

        contact = ContactPerson.objects.get(name="Spoof Attempt")
        assert contact.organization_id == org_a.pkid, (
            "Server must override any client-supplied organization with the "
            "caller's own org (Bug 1 mitigation pattern)"
        )

    def _extract_ids(self, body):
        """Best-effort id extractor across {results: [...]} and {<label>: [...]}."""
        if isinstance(body, list):
            return [c.get("id") for c in body if isinstance(c, dict)]
        if isinstance(body, dict):
            for value in body.values():
                if isinstance(value, list):
                    return [c.get("id") for c in value if isinstance(c, dict)]
                if isinstance(value, dict) and "results" in value:
                    return [c.get("id") for c in value["results"] if isinstance(c, dict)]
        return []


@pytest.mark.django_db
class TestAdminContactListScopedByOrg:
    def test_list_scoped_to_caller_org(self, staff_a, staff_b, org_a, org_b):
        """Staff in org A creates a contact; staff in org B must not see it."""
        contact_a = ContactPerson.objects.create(
            organization=org_a, name="A Contact", role="manager"
        )
        ContactPerson.objects.create(
            organization=org_b, name="B Contact", role="manager"
        )

        client = APIClient()
        client.force_authenticate(user=staff_b)
        response = client.get(ADMIN_LIST_URL)
        assert response.status_code == 200
        body = response.json()
        names = []
        if isinstance(body, dict):
            for value in body.values():
                if isinstance(value, list):
                    names = [c.get("name") for c in value if isinstance(c, dict)]
                    break
                if isinstance(value, dict) and "results" in value:
                    names = [c.get("name") for c in value["results"]]
                    break
        assert "A Contact" not in names
        assert "B Contact" in names


@pytest.mark.django_db
class TestAdminContactUpdate:
    def test_admin_contact_update_rename(self, staff_a, org_a):
        contact = ContactPerson.objects.create(
            organization=org_a, name="Старе Імʼя", role="manager"
        )
        client = APIClient()
        client.force_authenticate(user=staff_a)
        response = client.patch(
            f"{ADMIN_LIST_URL}{contact.id}/",
            {"name": "Нове Імʼя"},
            format="json",
        )
        assert response.status_code == 200, response.content
        contact.refresh_from_db()
        assert contact.name == "Нове Імʼя"


@pytest.mark.django_db
class TestAdminContactDelete:
    def test_admin_contact_delete_succeeds(self, staff_a, org_a):
        contact = ContactPerson.objects.create(
            organization=org_a, name="Удалити", role="other"
        )
        client = APIClient()
        client.force_authenticate(user=staff_a)
        response = client.delete(f"{ADMIN_LIST_URL}{contact.id}/")
        assert response.status_code == 204
        assert not ContactPerson.objects.filter(id=contact.id).exists()


@pytest.mark.django_db
class TestAdminContactCrossOrgIsolation:
    def test_staff_a_cannot_modify_org_b_contact(self, staff_a, org_b):
        """Cross-org PATCH must 404 (paranoid: not 403, to avoid leak)."""
        contact = ContactPerson.objects.create(
            organization=org_b, name="Чужий", role="manager"
        )
        client = APIClient()
        client.force_authenticate(user=staff_a)
        response = client.patch(
            f"{ADMIN_LIST_URL}{contact.id}/",
            {"name": "Hijacked"},
            format="json",
        )
        assert response.status_code == 404
        contact.refresh_from_db()
        assert contact.name == "Чужий"

    def test_staff_a_cannot_delete_org_b_contact(self, staff_a, org_b):
        contact = ContactPerson.objects.create(
            organization=org_b, name="Чужий2", role="manager"
        )
        client = APIClient()
        client.force_authenticate(user=staff_a)
        response = client.delete(f"{ADMIN_LIST_URL}{contact.id}/")
        assert response.status_code == 404
        assert ContactPerson.objects.filter(id=contact.id).exists()

    def test_tenant_cannot_access_admin_endpoint(self, tenant):
        """Plain tenant (non-staff) must get 403 from IsAdminUser."""
        client = APIClient()
        client.force_authenticate(user=tenant)
        response = client.get(ADMIN_LIST_URL)
        assert response.status_code in (401, 403)


@pytest.mark.django_db
class TestAdminContactSerializerLockdown:
    """Lock-down: ``AdminContactPersonSerializer`` must NOT expose
    ``organization`` as a writable field — pinning is server-side via
    ``perform_create``.  Same pattern as ``BuildingSerializer`` after
    PR-14 Bug 1 fix.
    """

    def test_admin_serializer_meta_fields_does_not_contain_organization(self):
        serializers_path = (
            Path(__file__).resolve().parents[2] / "site_settings" / "serializers.py"
        )
        text = serializers_path.read_text(encoding="utf-8")

        # Find the AdminContactPersonSerializer class block
        match = re.search(
            r"class AdminContactPersonSerializer\b[^\n]*:\s*"
            r"(.*?)(?=\nclass\s|\Z)",
            text,
            re.DOTALL,
        )
        assert match, (
            "AdminContactPersonSerializer must exist in apps/site_settings/serializers.py"
        )
        body = match.group(1)

        fields_match = re.search(r"fields\s*=\s*\[(.*?)\]", body, re.DOTALL)
        assert fields_match, (
            "AdminContactPersonSerializer.Meta.fields list must be present"
        )
        fields_block = fields_match.group(1)

        # ``organization`` may appear ONLY in read_only_fields, never in
        # the writable ``fields`` list.  Heuristic: tokenise by quotes.
        listed_fields = re.findall(r'"([^"]+)"|\'([^\']+)\'', fields_block)
        flat = {a or b for a, b in listed_fields}
        assert "organization" not in flat, (
            "AdminContactPersonSerializer must not expose 'organization' as "
            "a writable field — pinning is server-side via perform_create. "
            "If you need to read the org, use a SerializerMethodField or add "
            "it to read_only_fields explicitly."
        )
