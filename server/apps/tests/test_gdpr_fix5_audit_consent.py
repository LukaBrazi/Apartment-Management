"""
GDPR Fix 5 — ConsentLog + GDPRAuditLog моделі.

Перевіряє:
- ConsentLog: створення запису про consent give/withdraw
- ConsentLog: поле user = SET_NULL після видалення user
- GDPRAuditLog: log() helper створює запис з правильними полями
- GDPRAuditLog: поля actor/subject = SET_NULL після видалення user
- GDPRAuditLog: автоматично логується при виклику /api/v1/auth/my-data/
- GDPRAuditLog: автоматично логується при виклику /api/v1/auth/anonymize/
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.common.models import ConsentLog, GDPRAuditLog

User = get_user_model()


@pytest.fixture
def active_user(db):
    return User.objects.create_user(
        username="gdpr5_user",
        email="gdpr5@test.com",
        password="Test1234!",
    )


# ── ConsentLog ────────────────────────────────────────────────────────────────

class TestConsentLog:
    def test_create_consent_given(self, active_user):
        """ConsentLog зберігає запис про надання згоди."""
        log = ConsentLog.objects.create(
            user=active_user,
            purpose=ConsentLog.Purpose.MARKETING,
            given=True,
            ip_address="127.0.0.1",
        )
        assert log.pk is not None
        assert log.given is True
        assert log.purpose == "marketing"

    def test_create_consent_withdrawn(self, active_user):
        """ConsentLog зберігає запис про відкликання згоди."""
        log = ConsentLog.objects.create(
            user=active_user,
            purpose=ConsentLog.Purpose.ANALYTICS,
            given=False,
        )
        assert log.given is False

    def test_consent_user_set_null_on_user_delete(self, active_user):
        """ConsentLog.user = NULL після видалення user (SET_NULL)."""
        log = ConsentLog.objects.create(
            user=active_user,
            purpose=ConsentLog.Purpose.TERMS,
            given=True,
        )
        log_id = log.pk

        active_user.delete()

        log.refresh_from_db()
        assert log.user is None, "user має бути NULL після видалення"
        assert ConsentLog.objects.filter(pk=log_id).exists(), "ConsentLog має зберегтись"

    def test_consent_timestamp_auto_set(self, active_user):
        """ConsentLog.timestamp встановлюється автоматично."""
        before = timezone.now()
        log = ConsentLog.objects.create(
            user=active_user,
            purpose=ConsentLog.Purpose.NOTIFICATIONS,
            given=True,
        )
        assert log.timestamp >= before


# ── GDPRAuditLog ──────────────────────────────────────────────────────────────

class TestGDPRAuditLog:
    def test_log_helper_creates_record(self, active_user):
        """GDPRAuditLog.log() створює запис."""
        entry = GDPRAuditLog.log(
            event=GDPRAuditLog.EventType.DATA_EXPORT,
            subject=active_user,
            actor=active_user,
            detail="Test log",
            ip_address="127.0.0.1",
        )
        assert entry.pk is not None
        assert entry.event == "data_export"
        assert entry.subject == active_user
        assert entry.actor == active_user

    def test_audit_actor_set_null_on_delete(self, active_user, db):
        """GDPRAuditLog.actor = NULL після видалення user."""
        other = User.objects.create_user(
            username="gdpr5_other",
            email="gdpr5_other@test.com",
            password="Test1234!",
        )
        entry = GDPRAuditLog.log(
            event=GDPRAuditLog.EventType.ADMIN_ACCESS,
            subject=active_user,
            actor=other,
        )
        entry_id = entry.pk

        other.delete()

        entry.refresh_from_db()
        assert entry.actor is None, "actor має бути NULL після видалення"
        assert GDPRAuditLog.objects.filter(pk=entry_id).exists()

    def test_audit_subject_set_null_on_delete(self, active_user):
        """GDPRAuditLog.subject = NULL після видалення subject user."""
        entry = GDPRAuditLog.log(
            event=GDPRAuditLog.EventType.ERASURE_REQUEST,
            subject=active_user,
            actor=active_user,
        )
        entry_id = entry.pk

        active_user.delete()

        entry.refresh_from_db()
        assert entry.subject is None
        assert GDPRAuditLog.objects.filter(pk=entry_id).exists()

    def test_data_export_endpoint_creates_audit_log(self, active_user):
        """GET /api/v1/auth/my-data/ автоматично логується."""
        client = APIClient()
        client.force_authenticate(user=active_user)

        before_count = GDPRAuditLog.objects.filter(
            subject=active_user, event=GDPRAuditLog.EventType.DATA_EXPORT
        ).count()

        client.get("/api/v1/auth/my-data/")

        after_count = GDPRAuditLog.objects.filter(
            subject=active_user, event=GDPRAuditLog.EventType.DATA_EXPORT
        ).count()

        assert after_count == before_count + 1, "Audit log не створено для data export"

    def test_anonymize_endpoint_creates_audit_log(self, active_user):
        """POST /api/v1/auth/anonymize/ автоматично логується."""
        client = APIClient()
        client.force_authenticate(user=active_user)

        client.post("/api/v1/auth/anonymize/")

        exists = GDPRAuditLog.objects.filter(
            event=GDPRAuditLog.EventType.ACCOUNT_ANONYMIZED
        ).exists()
        assert exists, "Audit log не створено для anonymize"

    def test_audit_log_ordering(self, active_user):
        """GDPRAuditLog відсортований за -timestamp."""
        GDPRAuditLog.log(event=GDPRAuditLog.EventType.LOGIN, subject=active_user)
        GDPRAuditLog.log(event=GDPRAuditLog.EventType.DATA_EXPORT, subject=active_user)

        logs = list(GDPRAuditLog.objects.filter(subject=active_user))
        if len(logs) >= 2:
            assert logs[0].timestamp >= logs[1].timestamp
