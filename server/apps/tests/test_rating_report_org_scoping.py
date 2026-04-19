"""Regression tests for Rating + Report ``organization`` auto-population.

Both models gained an ``organization`` ForeignKey in the
``sec-fix-org-scoping`` branch (April 2026).  The FK is auto-populated
in ``Model.save()`` from the rater's / reporter's primary
``OrganizationMembership`` so admin queries can filter rows by org
without forcing every API call site to set the FK explicitly.

These tests lock down that contract:

* a row created by a user with a primary membership inherits that org;
* a row created by a user with no membership is left null — those
  rows are invisible to the multi-tenant admin views;
* a row created with an explicit ``organization=`` is **not** overridden
  by the auto-populate hook.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from apps.organizations.models import Organization, OrganizationMembership, OrgRole
from apps.ratings.models import Rating
from apps.reports.models import Report
from apps.tests.factories import UserFactory


pytestmark = pytest.mark.django_db


def _org(slug: str = "org") -> Organization:
    suffix = uuid4().hex[:6]
    return Organization.objects.create(
        name=f"Org-{suffix}",
        slug=f"{slug}-{suffix}",
        is_active=True,
    )


def _add_membership(user, org, role: str = OrgRole.RESIDENT) -> OrganizationMembership:
    return OrganizationMembership.objects.create(
        user=user,
        organization=org,
        role=role,
        is_active=True,
    )


# ── Rating ──────────────────────────────────────────────────────────────────


class TestRatingOrgAutoPopulate:
    def test_rating_inherits_rating_users_primary_org(self):
        org = _org("rate")
        rater = UserFactory(username=f"rater-{uuid4().hex[:4]}")
        rated = UserFactory(username=f"rated-{uuid4().hex[:4]}")
        _add_membership(rater, org)

        rating = Rating.objects.create(rating_user=rater, rated_user=rated, rating=5)

        assert rating.organization_id == org.pk

    def test_rating_without_membership_is_left_null(self):
        rater = UserFactory(username=f"orphan-rater-{uuid4().hex[:4]}")
        rated = UserFactory(username=f"orphan-rated-{uuid4().hex[:4]}")

        rating = Rating.objects.create(rating_user=rater, rated_user=rated, rating=4)

        assert rating.organization_id is None

    def test_explicit_organization_is_not_overridden(self):
        rater_org = _org("rater-home")
        explicit_org = _org("explicit")
        rater = UserFactory(username=f"rater2-{uuid4().hex[:4]}")
        rated = UserFactory(username=f"rated2-{uuid4().hex[:4]}")
        _add_membership(rater, rater_org)

        rating = Rating.objects.create(
            rating_user=rater,
            rated_user=rated,
            rating=3,
            organization=explicit_org,
        )

        assert rating.organization_id == explicit_org.pk


# ── Report ──────────────────────────────────────────────────────────────────


class TestReportOrgAutoPopulate:
    def test_report_inherits_reporters_primary_org(self):
        org = _org("rep")
        reporter = UserFactory(username=f"reporter-{uuid4().hex[:4]}")
        target = UserFactory(username=f"target-{uuid4().hex[:4]}")
        _add_membership(reporter, org)

        report = Report.objects.create(
            title="Noise complaint",
            reported_by=reporter,
            reported_user=target,
            description="Loud music after 22:00",
        )

        assert report.organization_id == org.pk

    def test_report_without_membership_is_left_null(self):
        reporter = UserFactory(username=f"orphan-reporter-{uuid4().hex[:4]}")
        target = UserFactory(username=f"orphan-target-{uuid4().hex[:4]}")

        report = Report.objects.create(
            title="No-org report",
            reported_by=reporter,
            reported_user=target,
            description="Reporter has no membership — org left null.",
        )

        assert report.organization_id is None

    def test_explicit_organization_is_not_overridden(self):
        reporter_org = _org("reporter-home")
        explicit_org = _org("forced")
        reporter = UserFactory(username=f"reporter2-{uuid4().hex[:4]}")
        target = UserFactory(username=f"target2-{uuid4().hex[:4]}")
        _add_membership(reporter, reporter_org)

        report = Report.objects.create(
            title="Forced-org report",
            reported_by=reporter,
            reported_user=target,
            description="Explicit org wins",
            organization=explicit_org,
        )

        assert report.organization_id == explicit_org.pk
