"""TDD tests for the organization report email feature (PR-11).

Coverage map:

* TestAdminAction       — permission gates + dispatch fan-out.
* TestGatherReportData  — single-source aggregation correctness.
* TestSendReportTask    — Celery task end-to-end (locmem mailbox).
* TestEmailTemplate     — template renders without external refs.

Fixtures import the existing ``conftest.py`` users and ``org`` fixture
from ``apps/organizations/tests/conftest.py``. We add one composite
fixture, ``org_with_residents``, that wires up 2 buildings, 4 units,
3 residents, and 2 occupied units — the canonical numeric test setup.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.template.loader import render_to_string
from django.test import RequestFactory

from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrgRole,
)


User = get_user_model()


# ── Composite fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def superuser_with_email(db):
    """Superuser with a real email for the admin action happy path."""
    return User.objects.create_superuser(
        username="pr11_super",
        email="pr11_super@apartmentos.org",
        password="testpass123",
        first_name="Super",
        last_name="Eleven",
    )


@pytest.fixture
def superuser_no_email(db):
    """Superuser whose ``email`` field is empty (admin without profile email)."""
    user = User.objects.create_superuser(
        username="pr11_super_noemail",
        email="placeholder@x.com",
        password="testpass123",
        first_name="No",
        last_name="Email",
    )
    User.objects.filter(pk=user.pk).update(email="")
    user.refresh_from_db()
    return user


@pytest.fixture
def regular_user_pr11(db):
    """Non-superuser invoking the action — must be blocked."""
    return User.objects.create_user(
        username="pr11_regular",
        email="pr11_regular@apartmentos.org",
        password="testpass123",
        first_name="Just",
        last_name="Resident",
    )


@pytest.fixture
def org_with_residents(db, director_user):
    """Realistic org: 2 buildings, 4 units, 3 residents, 2 occupied.

    Numbers chosen to make division non-degenerate (50% occupancy)
    and to expose distinct-count bugs (one resident has memberships
    in both an active and inactive role to test ``is_active`` filter).
    """
    from apps.apartments.models import Building, Entrance, Residency, Unit

    org = Organization.objects.create(
        name="Зелений Квартал — PR11",
        type="housing_complex",
        owner=director_user,
        email="pr11@org.test",
    )

    # 2 buildings
    b1 = Building.objects.create(name="B-1", address="Addr 1", organization=org)
    b2 = Building.objects.create(name="B-2", address="Addr 2", organization=org)

    # 1 entrance per building, 2 units per entrance → 4 units total
    e1 = Entrance.objects.create(building=b1, name="E1")
    e2 = Entrance.objects.create(building=b2, name="E2")
    u1 = Unit.objects.create(entrance=e1, number="101")
    u2 = Unit.objects.create(entrance=e1, number="102")
    u3 = Unit.objects.create(entrance=e2, number="201")
    u4 = Unit.objects.create(entrance=e2, number="202")  # noqa: F841

    # 3 residents
    r1 = User.objects.create_user(
        username="pr11_res1", email="r1@pr11.test", password="x",
        first_name="R", last_name="One",
    )
    r2 = User.objects.create_user(
        username="pr11_res2", email="r2@pr11.test", password="x",
        first_name="R", last_name="Two",
    )
    r3 = User.objects.create_user(
        username="pr11_res3", email="r3@pr11.test", password="x",
        first_name="R", last_name="Three",
    )

    OrganizationMembership.objects.create(
        user=r1, organization=org, role=OrgRole.RESIDENT, is_active=True,
    )
    OrganizationMembership.objects.create(
        user=r2, organization=org, role=OrgRole.RESIDENT, is_active=True,
    )
    OrganizationMembership.objects.create(
        user=r3, organization=org, role=OrgRole.RESIDENT, is_active=True,
    )
    # Inactive duplicate membership — must NOT be double counted.
    OrganizationMembership.objects.create(
        user=r1, organization=Organization.objects.create(
            name="Other org PR11", slug="other-pr11", owner=director_user,
        ),
        role=OrgRole.RESIDENT, is_active=False,
    )

    # 2 occupied units (u1, u3) via Residency rows.
    Residency.objects.create(user=r1, unit=u1, is_primary=True)
    Residency.objects.create(user=r2, unit=u3, is_primary=True)
    # u2 and u4 stay vacant.

    return org


@pytest.fixture
def empty_org(db, director_user):
    """An org with no buildings — exercises divide-by-zero defenses."""
    return Organization.objects.create(
        name="Empty Org PR11",
        type="housing_complex",
        owner=director_user,
    )


def _make_request_with_messages(user):
    """Build a RequestFactory POST with messages middleware wired up.

    Django admin actions call ``self.message_user(...)`` which goes
    through the messages framework; without a session + storage that
    blows up. This helper produces a request that works for unit tests.
    """
    rf = RequestFactory()
    req = rf.post("/admin/organizations/organization/")
    req.user = user
    # messages framework needs a session-ish storage; FallbackStorage
    # is the simplest in-memory option available in core.
    req.session = {}
    req._messages = FallbackStorage(req)
    return req


# ── Admin action: permissions + dispatch ─────────────────────────────────────


@pytest.mark.django_db
class TestAdminAction:
    def test_action_registered_on_org_admin(self):
        from apps.organizations.admin import OrganizationAdmin

        admin_instance = OrganizationAdmin(Organization, AdminSite())
        action_names = list(admin_instance.actions or [])
        assert "generate_org_report_email" in action_names

    def test_action_blocks_non_superuser(self, regular_user_pr11, org_with_residents):
        from apps.organizations.admin import OrganizationAdmin

        request = _make_request_with_messages(regular_user_pr11)
        admin_instance = OrganizationAdmin(Organization, AdminSite())
        qs = Organization.objects.filter(pk=org_with_residents.pk)

        with patch(
            "apps.organizations.tasks.send_organization_report_task.delay"
        ) as mock_delay:
            admin_instance.generate_org_report_email(request, qs)

        # Must NOT dispatch any tasks.
        mock_delay.assert_not_called()

    def test_action_blocks_when_superuser_has_no_email(
        self, superuser_no_email, org_with_residents,
    ):
        from apps.organizations.admin import OrganizationAdmin

        request = _make_request_with_messages(superuser_no_email)
        admin_instance = OrganizationAdmin(Organization, AdminSite())
        qs = Organization.objects.filter(pk=org_with_residents.pk)

        with patch(
            "apps.organizations.tasks.send_organization_report_task.delay"
        ) as mock_delay:
            admin_instance.generate_org_report_email(request, qs)

        mock_delay.assert_not_called()

    def test_action_dispatches_one_task_per_selected_org(
        self, superuser_with_email, org_with_residents, empty_org,
    ):
        from apps.organizations.admin import OrganizationAdmin

        request = _make_request_with_messages(superuser_with_email)
        admin_instance = OrganizationAdmin(Organization, AdminSite())
        qs = Organization.objects.filter(
            pk__in=[org_with_residents.pk, empty_org.pk]
        )

        with patch(
            "apps.organizations.tasks.send_organization_report_task.delay"
        ) as mock_delay:
            admin_instance.generate_org_report_email(request, qs)

        assert mock_delay.call_count == 2
        # Each call passes (org_id, recipient_email)
        called_emails = {c.args[1] for c in mock_delay.call_args_list}
        assert called_emails == {superuser_with_email.email}


# ── Data gathering ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestGatherReportData:
    def test_returns_required_keys(self, org_with_residents):
        from apps.organizations.tasks import _gather_org_report_data

        data = _gather_org_report_data(org_with_residents.id)
        required = {
            "org_name", "org_slug", "org_is_active",
            "n_buildings", "n_units",
            "n_residents", "n_occupied",
            "occupancy_pct", "occupancy_pct_px", "occupancy_ascii",
            "active_features",
            "subscription_plan_text", "trial_status_text",
            "generated_at",
        }
        assert required <= set(data.keys())

    def test_n_buildings_count(self, org_with_residents):
        from apps.organizations.tasks import _gather_org_report_data

        data = _gather_org_report_data(org_with_residents.id)
        assert data["n_buildings"] == 2

    def test_n_units_count(self, org_with_residents):
        from apps.organizations.tasks import _gather_org_report_data

        data = _gather_org_report_data(org_with_residents.id)
        assert data["n_units"] == 4

    def test_n_residents_distinct_active_only(self, org_with_residents):
        from apps.organizations.tasks import _gather_org_report_data

        data = _gather_org_report_data(org_with_residents.id)
        # Three active residents; r1's inactive membership in another
        # org must not contribute to this org's count.
        assert data["n_residents"] == 3

    def test_occupancy_metrics(self, org_with_residents):
        from apps.organizations.tasks import _gather_org_report_data

        data = _gather_org_report_data(org_with_residents.id)
        assert data["n_occupied"] == 2
        assert data["occupancy_pct"] == 50.0
        # 50% × 5 = 250 px out of 500
        assert data["occupancy_pct_px"] == 250
        # 20-char ASCII bar — half filled, half empty
        assert data["occupancy_ascii"].count("█") == 10
        assert data["occupancy_ascii"].count("░") == 10

    def test_zero_units_is_safe(self, empty_org):
        from apps.organizations.tasks import _gather_org_report_data

        data = _gather_org_report_data(empty_org.id)
        assert data["n_units"] == 0
        assert data["n_buildings"] == 0
        assert data["n_occupied"] == 0
        assert data["occupancy_pct"] == 0.0  # no division by zero
        assert data["occupancy_pct_px"] == 0
        assert data["occupancy_ascii"] == "░" * 20

    def test_active_features_lists_known_flags(self, org_with_residents):
        from apps.organizations.tasks import _gather_org_report_data

        data = _gather_org_report_data(org_with_residents.id)
        feats = data["active_features"]
        # _default_features() seeds posts/issues/passes/ratings/announcements
        names = {f["name"] for f in feats}
        assert {"posts", "issues", "passes", "ratings", "announcements"} <= names
        # All five are True by default
        assert all(f["active"] for f in feats if f["name"] in {
            "posts", "issues", "passes", "ratings", "announcements",
        })

    def test_active_features_empty_when_no_features(
        self, db, director_user,
    ):
        """Empty features dict → empty list (template shows fallback).

        Note: ``set_default_features`` post_save signal repopulates an
        empty dict on create, so we have to bypass it via ``QuerySet.update``.
        """
        from apps.organizations.tasks import _gather_org_report_data

        org = Organization.objects.create(
            name="No-features org PR11",
            type="housing_complex",
            owner=director_user,
        )
        # Bypass the post_save signal that would refill defaults.
        Organization.objects.filter(pk=org.pk).update(features={})

        data = _gather_org_report_data(org.id)
        assert data["active_features"] == []

    def test_raises_for_missing_org(self, db):
        """Bogus UUID → ValueError, never silent."""
        import uuid
        from apps.organizations.tasks import _gather_org_report_data

        with pytest.raises(ValueError):
            _gather_org_report_data(uuid.uuid4())


# ── Celery task end-to-end ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestSendReportTask:
    def test_sends_email_with_html_alternative(self, org_with_residents, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        mail.outbox = []

        from apps.organizations.tasks import send_organization_report_task
        send_organization_report_task(org_with_residents.id, "to@x.com")

        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert "to@x.com" in msg.to
        assert "Звіт організації" in msg.subject
        # Exactly one HTML alternative — no plaintext attachment, no .html file.
        html_alts = [a for a in msg.alternatives if a[1] == "text/html"]
        assert len(html_alts) == 1
        assert msg.attachments == []

    def test_subject_includes_org_name(self, org_with_residents, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        mail.outbox = []

        from apps.organizations.tasks import send_organization_report_task
        send_organization_report_task(org_with_residents.id, "to@x.com")

        assert org_with_residents.name in mail.outbox[0].subject

    def test_html_contains_org_name_and_kpis(self, org_with_residents, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        mail.outbox = []

        from apps.organizations.tasks import send_organization_report_task
        send_organization_report_task(org_with_residents.id, "to@x.com")

        html = mail.outbox[0].alternatives[0][0]
        assert org_with_residents.name in html
        # KPI labels must appear so the user knows what each number means.
        assert "Будинки" in html
        assert "Квартири" in html
        assert "Мешканці" in html
        assert "Заселеність" in html
        # Occupancy percentage rendered as a string token.
        # Django L10N for ``uk`` locale formats 50.0 as ``50,0`` — accept either.
        assert "50.0%" in html or "50,0%" in html
        # Subscription / trial placeholder visible
        assert "TODO PR-12" in html
        assert "TODO PR-13" in html

    def test_missing_org_logs_warning_no_email(self, db, settings, caplog):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        mail.outbox = []

        import uuid
        from apps.organizations.tasks import send_organization_report_task
        with caplog.at_level("WARNING"):
            send_organization_report_task(uuid.uuid4(), "to@x.com")

        assert mail.outbox == []
        assert any(
            "missing" in r.message.lower() or "missing" in r.getMessage().lower()
            for r in caplog.records
        )


# ── Template render guarantees ───────────────────────────────────────────────


@pytest.mark.django_db
class TestEmailTemplate:
    def test_renders_without_error_with_full_data(self, org_with_residents):
        from apps.organizations.tasks import _gather_org_report_data

        ctx = _gather_org_report_data(org_with_residents.id)
        ctx["recipient_email"] = "x@x.com"
        html = render_to_string("organizations/email/org_report.html", ctx)
        assert html
        assert "ApartmentOS" in html
        assert org_with_residents.name in html

    def test_renders_with_zero_features(self, org_with_residents):
        """Empty active_features → fallback copy is shown."""
        from apps.organizations.tasks import _gather_org_report_data

        ctx = _gather_org_report_data(org_with_residents.id)
        ctx["active_features"] = []
        ctx["recipient_email"] = "x@x.com"
        html = render_to_string("organizations/email/org_report.html", ctx)
        assert "Лише базові функції" in html

    def test_renders_with_zero_units(self, empty_org):
        """No units → no division by zero, page still renders."""
        from apps.organizations.tasks import _gather_org_report_data

        ctx = _gather_org_report_data(empty_org.id)
        ctx["recipient_email"] = "x@x.com"
        html = render_to_string("organizations/email/org_report.html", ctx)
        assert html
        # ``uk`` locale renders 0.0 as ``0,0`` — accept either form.
        assert "0%" in html or "0,0%" in html or "0.0%" in html

    def test_html_is_self_contained(self, org_with_residents):
        """No external CSS/JS/images — email clients block them anyway."""
        from apps.organizations.tasks import _gather_org_report_data

        ctx = _gather_org_report_data(org_with_residents.id)
        ctx["recipient_email"] = "x@x.com"
        html = render_to_string("organizations/email/org_report.html", ctx)

        assert "<link rel=\"stylesheet\"" not in html
        assert "<script" not in html
        # No external image references — we use text + emoji + inline SVG only.
        assert "src=\"http" not in html
        assert "src='http" not in html
        # Inline SVG present (progress bar)
        assert "<svg" in html

    def test_html_uses_table_based_layout(self, org_with_residents):
        """Email-safe layout — must not lean on flexbox or CSS grid."""
        from apps.organizations.tasks import _gather_org_report_data

        ctx = _gather_org_report_data(org_with_residents.id)
        ctx["recipient_email"] = "x@x.com"
        html = render_to_string("organizations/email/org_report.html", ctx)

        # Plenty of <table> elements — main structural mechanism.
        assert html.lower().count("<table") >= 6
        # No flexbox / grid CSS — old Outlook would silently break.
        assert "display:flex" not in html.lower()
        assert "display: flex" not in html.lower()
        assert "display:grid" not in html.lower()
        assert "display: grid" not in html.lower()
