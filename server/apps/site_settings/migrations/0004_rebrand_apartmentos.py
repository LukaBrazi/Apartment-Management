# Data migration: rebrand stale SiteSettings rows from EstateOS → ApartmentOS.
#
# Context
# -------
# Commit 19428d2 ("refactor: remove self-registration & Google OAuth, rebrand
# to ApartmentOS") changed the *model defaults* for hero_title, cta_text, etc.
# But Django's ``default=`` only applies when a brand-new row is INSERTed — it
# does NOT rewrite rows that already exist.  Production DBs created before the
# rebrand still carry the old "Welcome to EstateOS" / "Create Your Account"
# strings, so apartmentos.org still shows the stale brand.
#
# This migration does two things:
#   1. Aligns the schema-level defaults (hero_subtitle, platform_name) that
#      were still carrying EstateOS wording in ``models.py``.
#   2. Rewrites any existing row whose field *exactly* matches the old default
#      to the new ApartmentOS value.  Rows that were customised by an admin
#      (e.g. a white-label client with their own ЖК branding) are left alone.
#
# Idempotent: running twice is a no-op.

from django.db import migrations, models


# ─── Stale → Fresh value map ─────────────────────────────────────────────────
# Each tuple: (field_name, {set of old values that should be rewritten}, new_default)
# A row is only updated if its current value is in the "stale set" — so any
# admin-customized branding (white-label clients with their own hero/CTA)
# survives untouched.  The stale set for `cta_url` covers every historic
# registration route we've shipped (``/register``, ``/signup``, ``/agents``,
# ``/create-account``) plus the English CTA text values.
_STALE_DEFAULTS: tuple[tuple[str, frozenset[str], str], ...] = (
    ("hero_title", frozenset({"Welcome to EstateOS"}), "Вітаємо в ApartmentOS"),
    (
        "hero_subtitle",
        frozenset({"Are you a new tenant? Or an existing tenant?"}),
        "Увійдіть до свого акаунту",
    ),
    (
        "cta_text",
        frozenset({"Create Your Account", "Sign Up", "Register"}),
        "Увійти",
    ),
    (
        "cta_url",
        frozenset({"/register", "/signup", "/agents", "/create-account"}),
        "/login",
    ),
    ("platform_name", frozenset({"EstateOS"}), "ApartmentOS"),
)


def rebrand_forward(apps, schema_editor):
    """Rewrite stale EstateOS defaults to ApartmentOS on every SiteSettings row."""
    SiteSettings = apps.get_model("site_settings", "SiteSettings")
    for settings_obj in SiteSettings.objects.all().iterator():
        changed_fields: list[str] = []
        for field_name, stale_values, new_value in _STALE_DEFAULTS:
            if getattr(settings_obj, field_name, None) in stale_values:
                setattr(settings_obj, field_name, new_value)
                changed_fields.append(field_name)
        if changed_fields:
            settings_obj.save(update_fields=changed_fields)


def rebrand_reverse(apps, schema_editor):
    """Reverse: restore the first-listed EstateOS wording (manual rollback only)."""
    SiteSettings = apps.get_model("site_settings", "SiteSettings")
    for settings_obj in SiteSettings.objects.all().iterator():
        changed_fields: list[str] = []
        for field_name, stale_values, new_value in _STALE_DEFAULTS:
            # Restore to the first historical value in the stale set (deterministic).
            first_stale = next(iter(sorted(stale_values)))
            if getattr(settings_obj, field_name, None) == new_value:
                setattr(settings_obj, field_name, first_stale)
                changed_fields.append(field_name)
        if changed_fields:
            settings_obj.save(update_fields=changed_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("site_settings", "0003_org_scoped_settings"),
    ]

    operations = [
        # 1. Align schema-level defaults so newly-created rows match ApartmentOS.
        migrations.AlterField(
            model_name="sitesettings",
            name="hero_subtitle",
            field=models.CharField(
                default="Увійдіть до свого акаунту",
                max_length=300,
                verbose_name="hero subtitle",
            ),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="platform_name",
            field=models.CharField(
                default="ApartmentOS",
                help_text="The name of the property management platform (white-label).",
                max_length=100,
                verbose_name="platform name",
            ),
        ),
        # 2. Rewrite any existing rows that still carry the stale EstateOS values.
        migrations.RunPython(rebrand_forward, rebrand_reverse),
    ]
