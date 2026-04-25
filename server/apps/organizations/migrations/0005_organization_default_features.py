"""Migration: set default features on Organization and fix empty slugs.

Changes
-------
1. ``features`` field default changes from ``{}`` to the canonical set:
   posts, issues, passes, ratings, announcements = True.
   Data: existing orgs with ``features={}`` are backfilled.

2. **Slug repair** — ``Organization.save()`` previously used
   ``django.utils.text.slugify`` without ``allow_unicode=True``.
   For Cyrillic names (like the demo org "ОСББ «Зелений Квартал — Демо»"
   or any real org named in Ukrainian) the default slugify produces an
   empty string ``""``.  All such orgs ended up with ``slug=""``, and the
   unique constraint on ``slug`` meant the second Cyrillic org could not
   be saved — resulting in a 500 IntegrityError on org creation.
   Data: this migration replaces every ``slug=""`` row with a unique
   unicode slug derived from the org name.
"""
from __future__ import annotations

from django.db import migrations, models
from django.utils.text import slugify


# ── Inline default callable ──────────────────────────────────────────────────
# Defined here (not imported from models) so the migration is self-contained
# and survives model renames / moves without breaking.

def _default_org_features() -> dict:
    return {
        "posts": True,
        "issues": True,
        "passes": True,
        "ratings": True,
        "announcements": True,
    }


DEFAULT_FEATURES = _default_org_features()


# ── Data migrations ──────────────────────────────────────────────────────────

def backfill_features(apps, schema_editor):
    """Give every org with features={} the canonical feature set."""
    Organization = apps.get_model("organizations", "Organization")
    Organization.objects.filter(features={}).update(features=DEFAULT_FEATURES)


def backfill_slugs(apps, schema_editor):
    """Replace every org with slug='' with a unique unicode slug."""
    Organization = apps.get_model("organizations", "Organization")
    broken = list(Organization.objects.filter(slug="").order_by("pkid"))
    for org in broken:
        base = slugify(org.name, allow_unicode=True) or f"org-{org.pkid}"
        slug = base
        counter = 1
        while Organization.objects.filter(slug=slug).exclude(pkid=org.pkid).exists():
            slug = f"{base}-{counter}"
            counter += 1
        Organization.objects.filter(pkid=org.pkid).update(slug=slug)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0004_backfill_demo_organization"),
    ]

    operations = [
        # 1. Update the features field default.
        migrations.AlterField(
            model_name="organization",
            name="features",
            field=models.JSONField(
                default=_default_org_features,
                help_text="Feature flags for this organization",
                verbose_name="Features",
            ),
        ),
        # 2. Backfill features for orgs that still have the old empty default.
        migrations.RunPython(backfill_features, noop_reverse),
        # 3. Repair orgs whose slug is "" due to the missing allow_unicode bug.
        migrations.RunPython(backfill_slugs, noop_reverse),
    ]
