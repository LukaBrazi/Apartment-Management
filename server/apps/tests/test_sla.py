"""Tests for Issue status flow + SLA."""
import pytest
from datetime import timedelta

from django.utils import timezone

from apps.issues.models import Issue, ALLOWED_TRANSITIONS
from apps.tests.factories import ApartmentFactory, CategoryFactory, IssueFactory, UserFactory


@pytest.mark.django_db
def test_due_at_computed_on_create():
    """due_at = created_at + sla_hours when category is set."""
    category = CategoryFactory(sla_hours=48)
    apt = ApartmentFactory()
    user = UserFactory()
    before = timezone.now()
    issue = IssueFactory(apartment=apt, reported_by=user, category=category)
    after = timezone.now()

    assert issue.due_at is not None
    # due_at should be ~48h after creation
    assert before + timedelta(hours=47) < issue.due_at < after + timedelta(hours=49)


@pytest.mark.django_db
def test_due_at_not_set_without_category():
    apt = ApartmentFactory()
    user = UserFactory()
    issue = IssueFactory(apartment=apt, reported_by=user, category=None)
    assert issue.due_at is None


@pytest.mark.django_db
def test_is_overdue_true_when_past_due():
    apt = ApartmentFactory()
    user = UserFactory()
    issue = IssueFactory(
        apartment=apt,
        reported_by=user,
        due_at=timezone.now() - timedelta(hours=1),
        status="reported",
    )
    assert issue.is_overdue is True


@pytest.mark.django_db
def test_is_overdue_false_when_not_yet_due():
    apt = ApartmentFactory()
    user = UserFactory()
    issue = IssueFactory(
        apartment=apt,
        reported_by=user,
        due_at=timezone.now() + timedelta(hours=24),
        status="reported",
    )
    assert issue.is_overdue is False


@pytest.mark.django_db
def test_is_overdue_false_when_done():
    apt = ApartmentFactory()
    user = UserFactory()
    issue = IssueFactory(
        apartment=apt,
        reported_by=user,
        due_at=timezone.now() - timedelta(hours=1),
        status="done",
    )
    assert issue.is_overdue is False


@pytest.mark.django_db
def test_valid_transition_reported_to_accepted():
    apt = ApartmentFactory()
    user = UserFactory()
    issue = IssueFactory(apartment=apt, reported_by=user, status="reported")
    issue.transition_to("accepted")
    issue.refresh_from_db()
    assert issue.status == "accepted"


@pytest.mark.django_db
def test_valid_transition_accepted_to_in_progress():
    apt = ApartmentFactory()
    user = UserFactory()
    issue = IssueFactory(apartment=apt, reported_by=user, status="accepted")
    issue.transition_to("in_progress")
    issue.refresh_from_db()
    assert issue.status == "in_progress"


@pytest.mark.django_db
def test_valid_transition_in_progress_to_done_sets_resolved_on():
    apt = ApartmentFactory()
    user = UserFactory()
    issue = IssueFactory(apartment=apt, reported_by=user, status="in_progress")
    issue.transition_to("done")
    issue.refresh_from_db()
    assert issue.status == "done"
    assert issue.resolved_on is not None


@pytest.mark.django_db
def test_invalid_transition_raises_value_error():
    apt = ApartmentFactory()
    user = UserFactory()
    issue = IssueFactory(apartment=apt, reported_by=user, status="reported")
    with pytest.raises(ValueError, match="Cannot transition"):
        issue.transition_to("done")


@pytest.mark.django_db
def test_terminal_state_no_transitions():
    apt = ApartmentFactory()
    user = UserFactory()
    issue = IssueFactory(apartment=apt, reported_by=user, status="done")
    with pytest.raises(ValueError):
        issue.transition_to("in_progress")
