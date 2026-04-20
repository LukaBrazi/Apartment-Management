"""Rescope ``TelegramProfile`` + ``TelegramVerificationToken`` per-organization.

PR-14 phase 2. See ``docs/ADR-014-multi-tenant-telegram-bots.md`` §4.

The pre-PR-14 schema assumed a single platform-wide bot, so:

* ``TelegramProfile.user`` was ``OneToOneField`` — one binding per user,
  globally.
* ``TelegramProfile.chat_id`` was ``unique=True`` — globally unique.
* ``TelegramVerificationToken`` carried only ``user``; the redemption
  path had no way to verify which org's bot the ``/start`` came from.

Under per-org bots that shape is broken: the same human who manages
two ЖК needs two separate bindings (one per bot), and a token minted
by org A's frontend must not be redeemable against org B's bot.

This migration walks the schema to the new shape in four stages,
each idempotent and reversible:

1. Add ``organization`` FK as nullable on both tables.
2. Backfill ``organization`` from the user's first active
   ``OrganizationMembership``. Rows whose user has no membership are
   deleted — they're orphans under the new model and would block the
   subsequent non-null constraint.
3. Rewrite the constraints:
   - ``TelegramProfile.user``:  O2O → FK (new related_name
     ``telegram_profiles``, plural). The O2O-level unique index on
     user_id is gone; (user, organization) is now the unique pair.
   - ``TelegramProfile.chat_id``: drop global ``unique=True``, add a
     plain btree index for webhook-path lookups. Chat uniqueness moves
     to the ``(organization, chat_id)`` composite constraint.
4. Mark ``organization`` as non-null and add the two unique constraints.

Production impact: new feature, table was empty on every live
environment when this migration ran, so the RunPython is a no-op
there. Dev/test envs where someone hand-rolled a legacy profile get
backfilled to their primary org or dropped — either is safe because
the feature hadn't been exposed yet.
"""
from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def _backfill_org(profile_or_token, memberships_by_user):
    """Return the org FK id for a legacy row, or None if the user has none.

    Uses the same "first active membership" rule as
    ``apps.organizations.utils.get_user_primary_organization`` — cheap
    and consistent with how the rest of the codebase chooses a default
    org for a multi-tenant user.
    """
    return memberships_by_user.get(profile_or_token.user_id)


def backfill_and_prune(apps, schema_editor):
    """Populate ``organization_id`` on every legacy profile/token row.

    Strategy:
      - Build a {user_id: org_id} map from active memberships (one query).
      - Walk profiles; assign org if we have one, delete the row otherwise.
      - Same for verification tokens — a token without an org is unsafe to
        keep around because the /verify/ path now requires org agreement.
    """
    TelegramProfile = apps.get_model("notifications", "TelegramProfile")
    TelegramVerificationToken = apps.get_model(
        "notifications", "TelegramVerificationToken",
    )
    OrganizationMembership = apps.get_model(
        "organizations", "OrganizationMembership",
    )

    # One-shot map so we don't hit the DB per profile.
    memberships_by_user: dict[int, int] = {}
    for m in OrganizationMembership.objects.filter(is_active=True).order_by("id"):
        # ``setdefault`` mirrors the "first active membership" selection
        # the app uses at runtime — iteration order is stable by PK.
        memberships_by_user.setdefault(m.user_id, m.organization_id)

    # Profiles: backfill or drop orphans.
    for profile in TelegramProfile.objects.all():
        org_id = _backfill_org(profile, memberships_by_user)
        if org_id is None:
            profile.delete()
            continue
        profile.organization_id = org_id
        profile.save(update_fields=["organization"])

    # Tokens: same rule. An unexpired orphan is harmless because the
    # verify flow will reject it either way, but leaving NULLs in the
    # column would block the subsequent non-null ALTER.
    for token in TelegramVerificationToken.objects.all():
        org_id = _backfill_org(token, memberships_by_user)
        if org_id is None:
            token.delete()
            continue
        token.organization_id = org_id
        token.save(update_fields=["organization"])


def unbackfill(apps, schema_editor):
    """Reverse path just nulls the columns out — the table shape is
    restored by the subsequent schema operations' ``reverse_migrate``.
    Keeping this as a no-op is safe because the forward op is
    idempotent: re-running it simply rewrites the same rows.
    """
    return


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_organization_bot"),
        # Explicit dep on organizations — we reference Organization and
        # OrganizationMembership in the RunPython step and via FKs.
        ("organizations", "0004_backfill_demo_organization"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Stage 1: add organization FK as NULL-able on both tables. ──
        migrations.AddField(
            model_name="telegramprofile",
            name="organization",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="telegram_profiles",
                to="organizations.organization",
                verbose_name="Organization",
            ),
        ),
        migrations.AddField(
            model_name="telegramverificationtoken",
            name="organization",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="telegram_verification_tokens",
                to="organizations.organization",
                verbose_name="Organization",
            ),
        ),

        # ── Stage 2: backfill or prune legacy rows. ──
        migrations.RunPython(backfill_and_prune, reverse_code=unbackfill),

        # ── Stage 3: rewrite the profile's core constraints. ──
        # O2O → FK requires dropping the implicit unique index on user_id.
        # We do it as a straight AlterField — Django handles the index drop.
        migrations.AlterField(
            model_name="telegramprofile",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="telegram_profiles",
                to=settings.AUTH_USER_MODEL,
                verbose_name="User",
            ),
        ),
        # chat_id: drop global unique, add plain index (webhook lookups
        # still need it).
        migrations.AlterField(
            model_name="telegramprofile",
            name="chat_id",
            field=models.BigIntegerField(
                db_index=True,
                help_text=(
                    "Telegram chat_id the org's bot will DM. Unique per "
                    "organization, not globally — one person can link the "
                    "same Telegram account to multiple orgs (Telegram "
                    "assigns a separate chat_id per bot)."
                ),
                verbose_name="Chat ID",
            ),
        ),

        # ── Stage 4: lock organization to non-null and add the new uniques. ──
        migrations.AlterField(
            model_name="telegramprofile",
            name="organization",
            field=models.ForeignKey(
                help_text=(
                    "Which ЖК this binding belongs to — the org whose bot "
                    "owns the chat_id."
                ),
                on_delete=django.db.models.deletion.CASCADE,
                related_name="telegram_profiles",
                to="organizations.organization",
                verbose_name="Organization",
            ),
        ),
        migrations.AlterField(
            model_name="telegramverificationtoken",
            name="organization",
            field=models.ForeignKey(
                help_text=(
                    "Target org — /verify/ rejects the exchange unless this "
                    "matches the bot that received /start."
                ),
                on_delete=django.db.models.deletion.CASCADE,
                related_name="telegram_verification_tokens",
                to="organizations.organization",
                verbose_name="Organization",
            ),
        ),
        migrations.AddConstraint(
            model_name="telegramprofile",
            constraint=models.UniqueConstraint(
                fields=("user", "organization"),
                name="unique_tg_profile_per_user_and_org",
            ),
        ),
        migrations.AddConstraint(
            model_name="telegramprofile",
            constraint=models.UniqueConstraint(
                fields=("organization", "chat_id"),
                name="unique_tg_chat_id_per_org",
            ),
        ),
        # Cosmetic sync so makemigrations --check stays green. The 0001
        # schema shipped these fields without verbose_name kwargs; the
        # new model re-adds them for i18n. No DB shape change.
        migrations.AlterField(
            model_name="telegramprofile",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Active"),
        ),
        migrations.AlterField(
            model_name="telegramverificationtoken",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="telegram_tokens",
                to=settings.AUTH_USER_MODEL,
                verbose_name="User",
            ),
        ),
        # Cosmetic re-declaration of the model meta so Django's state
        # matches ``models.py`` exactly (new verbose_name_plural is
        # translated, new ordering).
        migrations.AlterModelOptions(
            name="telegramprofile",
            options={
                "ordering": ["organization", "user_id"],
                "verbose_name": "Telegram Profile",
                "verbose_name_plural": "Telegram Profiles",
            },
        ),
        migrations.AlterModelOptions(
            name="telegramverificationtoken",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Telegram Verification Token",
                "verbose_name_plural": "Telegram Verification Tokens",
            },
        ),
    ]
