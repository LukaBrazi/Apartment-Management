# Generated for PR-5 (feat/gdpr-consent-mvp).
#
# Extends ConsentLog with versioned-consent fields (consent_type, version,
# accepted_at) used by the new ToS/Privacy MVP endpoints. Existing
# purpose/given/timestamp columns stay in place for the legacy
# marketing/analytics use case (apps/tests/test_gdpr_fix5_audit_consent.py).
#
# All new columns have safe defaults so the migration is non-destructive on
# existing rows; ordering switches from -timestamp to -accepted_at to match
# the new primary use case.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0001_initial"),
    ]

    operations = [
        # --- New versioned-consent fields ---------------------------------
        migrations.AddField(
            model_name="consentlog",
            name="consent_type",
            field=models.CharField(
                blank=True,
                choices=[("tos", "Terms of Service"), ("privacy", "Privacy Policy")],
                db_index=True,
                default="",
                max_length=20,
                verbose_name="Consent Type",
            ),
        ),
        migrations.AddField(
            model_name="consentlog",
            name="version",
            field=models.CharField(
                blank=True, default="", max_length=20, verbose_name="Version"
            ),
        ),
        migrations.AddField(
            model_name="consentlog",
            name="accepted_at",
            field=models.DateTimeField(
                auto_now_add=True, db_index=True, verbose_name="Accepted At"
            ),
        ),
        # --- Backwards-compatibility tweaks for legacy fields -------------
        migrations.AlterField(
            model_name="consentlog",
            name="purpose",
            field=models.CharField(
                blank=True,
                choices=[
                    ("marketing", "Marketing emails"),
                    ("analytics", "Usage analytics"),
                    ("notifications", "Push notifications"),
                    ("terms", "Terms of service"),
                ],
                db_index=True,
                default="",
                max_length=50,
                verbose_name="Purpose",
            ),
        ),
        migrations.AlterField(
            model_name="consentlog",
            name="given",
            field=models.BooleanField(
                default=True,
                help_text="True = consent given, False = consent withdrawn.",
                verbose_name="Consent Given",
            ),
        ),
        # --- Ordering + new composite index -------------------------------
        migrations.AlterModelOptions(
            name="consentlog",
            options={
                "ordering": ["-accepted_at"],
                "verbose_name": "Consent Log",
                "verbose_name_plural": "Consent Logs",
            },
        ),
        migrations.AddIndex(
            model_name="consentlog",
            index=models.Index(
                fields=["user", "consent_type", "-accepted_at"],
                name="consent_user_type_ts_idx",
            ),
        ),
    ]
