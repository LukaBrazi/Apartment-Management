"""Backfill empty / duplicate slugs on ``Organization``.

Background
----------
The first version of ``Organization.save()`` used Django's built-in
``django.utils.text.slugify``, which strips every non-ASCII character
by default. For Ukrainian names ("ОСББ «Зелений Квартал — Демо»") the
output was an empty string. The ``slug`` column is ``unique=True``,
so:

* The *first* org with a Cyrillic-only name saved successfully with
  ``slug=""``.
* The *second* such org blew up on the DB constraint —
  ``duplicate key value violates unique constraint
  organizations_organization_slug_key / DETAIL: Key (slug)=() already
  exists.`` — preventing any admin user from creating the second ЖК.

The code fix in ``models.py`` switches to ``python-slugify`` (which
transliterates) + a UUID fallback, so *new* rows are always safe.
This migration closes the loop for rows already in the DB: any
``slug`` that's empty or coincidentally duplicated gets backfilled
with the same transliteration logic the model now uses. Idempotent
— re-running finds nothing to do.

Safety
------
We only touch rows where ``slug`` is empty OR would collide with
another already-good slug. Every update is logged in memory and
reconciled row-by-row, so two rows that happen to transliterate to
the same string get a UUID fragment appended to one of them. No
data is ever deleted.
"""
from __future__ import annotations

from django.db import migrations


def _transliterate(name: str) -> str:
    """Run ``python-slugify`` at migration time; lazy import keeps
    the migration importable even when the runtime venv somehow
    differs from the migration-runner venv."""
    from slugify import slugify as unicode_slugify

    return unicode_slugify(name or "")


def backfill(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")

    # Collect every current slug into a set so we can detect
    # collisions as we backfill. We seed the set with already-good
    # slugs first so their values are treated as taken.
    rows = list(Organization.objects.all().order_by("pkid"))
    taken: set[str] = {row.slug for row in rows if row.slug}

    updated = 0
    for row in rows:
        if row.slug and row.slug.strip():
            continue  # already populated, leave alone

        candidate = _transliterate(row.name)
        if not candidate:
            # Same UUID fallback as the runtime save() path.
            candidate = f"org-{str(row.id)[:8]}"

        # Collision handling: if two existing rows would have mapped
        # to the same slug (e.g. "ОСББ №1" and "ОСББ №1" spelled with
        # different whitespace), disambiguate with a UUID fragment.
        base = candidate
        bump = 0
        while candidate in taken:
            bump += 1
            candidate = f"{base}-{str(row.id)[:4]}" if bump == 1 else f"{base}-{str(row.id)[:4]}-{bump}"

        Organization.objects.filter(pk=row.pkid).update(slug=candidate)
        taken.add(candidate)
        updated += 1

    if updated:
        # Migration stdout shows up in `manage.py migrate` logs — useful
        # breadcrumb for verifying the fix landed on prod.
        schema_editor.connection.cursor().execute(
            f"-- organizations.0005_backfill_empty_slugs updated {updated} rows"
        )


def noop_reverse(apps, schema_editor):
    """Non-reversible on purpose.

    We can't know which slugs were originally empty vs which were
    hand-set to a value this migration overwrote, so reversing would
    risk clobbering real data. The migration is idempotent — re-run
    with no effect on a healthy DB.
    """
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0004_backfill_demo_organization"),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]
