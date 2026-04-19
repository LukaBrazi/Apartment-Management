"""PR-12: add ``User.is_demo`` flag + backfill existing @demo.com users.

Adding the column defaults to ``False`` for every existing row — including
the demo accounts already in prod. Without a data backfill the very first
nightly ``seed_demo --reset`` after deploy would find **zero** demo users
to scrub (because the new scope filter also keys on ``is_demo=True``) and
the demo dataset would accumulate cruft.

The backfill mirrors the live reset filter: any user whose email ends in
``@demo.com`` AND is **not** a superuser gets flipped to ``is_demo=True``.
Superusers are left alone even if they happen to have a demo email, same
guard that ``reset_scope.py`` applies.
"""
from __future__ import annotations

from django.db import migrations, models


def _flag_existing_demo_users(apps, schema_editor):
    User = apps.get_model("users", "User")
    # Mirror apps.common.seed.helpers.DEMO_EMAIL_DOMAIN — inlined because the
    # helpers module lives outside the migrations graph and its contents
    # should not be coupled to historical migrations.
    User.objects.filter(
        email__iendswith="@demo.com",
        is_superuser=False,
    ).update(is_demo=True)


def _unflag_all_demo_users(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(is_demo=True).update(is_demo=False)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_demo",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    "Marks seed-created demo accounts. The nightly reset "
                    "only deletes users with is_demo=True."
                ),
                verbose_name="Demo Account",
            ),
        ),
        migrations.RunPython(
            _flag_existing_demo_users,
            reverse_code=_unflag_all_demo_users,
        ),
    ]
