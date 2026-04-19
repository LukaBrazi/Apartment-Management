"""PR-10: Backfill ``Residency`` from the existing ``Profile.unit`` FK.

Every ``Profile`` that currently points at a ``Unit`` gets exactly one
``Residency`` row — ``role=OWNER``, ``is_primary=True``.  The operation
is idempotent: a pre-existing ``(user, unit)`` pair is respected and,
if that pre-existing row is primary, the backfill leaves it alone.  If
it exists but is not primary, it is promoted to primary (because
``Profile.unit`` is still the authoritative link during PR-10 and the
property resolver falls back to it when no primary Residency is found).

Down-migration is intentionally a no-op: once readers have been moved
to ``Residency`` in PR-10 and ``Profile.unit`` is dropped in PR-11,
destroying backfilled rows would erase ownership data.  To reverse,
revert PR-11 first, then the FK copy becomes the source of truth
again.
"""
from __future__ import annotations

from django.db import migrations


def backfill(apps, schema_editor) -> None:
    Profile = apps.get_model("profiles", "Profile")
    Residency = apps.get_model("apartments", "Residency")

    profiles = (
        Profile.objects.filter(unit__isnull=False)
        .select_related("user", "unit")
    )

    # Group by user to enforce the partial unique invariant — only one
    # primary residency per user.  In practice each Profile belongs to
    # exactly one user, but being defensive keeps this migration safe
    # if historical data has duplicates.
    seen_primary_for_user: set[int] = set()

    for profile in profiles.iterator():
        if profile.user_id is None or profile.unit_id is None:
            continue

        is_primary = profile.user_id not in seen_primary_for_user

        existing = (
            Residency.objects.filter(
                user_id=profile.user_id, unit_id=profile.unit_id
            ).first()
        )
        if existing is None:
            Residency.objects.create(
                user_id=profile.user_id,
                unit_id=profile.unit_id,
                role="owner",
                is_primary=is_primary,
            )
        elif is_primary and not existing.is_primary:
            # Clear any other primaries for this user first — then
            # promote the existing row.  This keeps the partial unique
            # constraint satisfied under SQLite and PostgreSQL alike.
            Residency.objects.filter(
                user_id=profile.user_id, is_primary=True
            ).exclude(pk=existing.pk).update(is_primary=False)
            existing.is_primary = True
            existing.save(update_fields=["is_primary"])

        if is_primary:
            seen_primary_for_user.add(profile.user_id)


def noop_reverse(apps, schema_editor) -> None:
    """Reverse is intentionally a no-op — see module docstring."""
    return


class Migration(migrations.Migration):

    dependencies = [
        ("apartments", "0008_pr9_residency_plus_typed_buildings"),
        ("profiles", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]
