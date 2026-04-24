"""Resolve the right ``OrganizationBot`` for a delivery decision.

This module sits between the Celery tasks and the ``OrganizationBot``
table.  The contract is simple:

* Given an ``Organization`` or an ``Organization``-shaped thing, return
  the primary active bot for that org — or ``None`` if it isn't set up
  yet, or the org has the feature flag switched off.
* Never raise.  Callers use the return value to decide whether to
  build and send a payload at all; a missing bot must degrade silently
  (see ADR-014 §7).

The feature flag check lives here instead of on the caller because
every notification path would otherwise repeat the same guard, and we
want exactly one place that decides "is Telegram active for this org?".
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apps.notifications.models import OrganizationBot

if TYPE_CHECKING:  # pragma: no cover — typing only
    from apps.organizations.models import Organization

logger = logging.getLogger(__name__)

# Feature-flag key stored inside ``Organization.features`` (JSONField).
# Mirrored in the frontend toggle and in the admin form — keep in sync.
TELEGRAM_FEATURE_FLAG = "telegram_notifications"


def get_bot_for_org(organization: "Organization | None") -> OrganizationBot | None:
    """Return the active bot for ``organization``, falling back to the default bot.

    Resolution order:
    1. organization is None → return None (no org context at all)
    2. feature flag off → return None (explicit opt-out, default bot is NOT used)
    3. org has its own primary active bot → return it
    4. no org bot → fallback to the platform default bot (is_default=True)
    5. no default bot either → return None
    """
    if organization is None:
        return None
    if not organization.is_feature_enabled(TELEGRAM_FEATURE_FLAG):
        return None

    # Org-specific bot takes priority.
    bot = (
        OrganizationBot.objects
        .filter(organization=organization, is_primary=True, is_active=True)
        .first()
    )
    if bot is not None and bot.is_configured:
        return bot

    if bot is not None:
        logger.debug(
            "notifications: bot for org=%s present but not configured, trying default",
            organization.slug,
        )

    # Fallback to platform default bot.
    default_bot = _get_default_bot()
    if default_bot is None:
        logger.debug(
            "notifications: no org bot and no default bot for org=%s",
            getattr(organization, "slug", "?"),
        )
    else:
        logger.debug(
            "notifications: using default bot as fallback for org=%s",
            getattr(organization, "slug", "?"),
        )
    return default_bot


def _get_default_bot() -> OrganizationBot | None:
    """Return the platform-wide default bot, or None if not configured."""
    bot = (
        OrganizationBot.objects
        .filter(is_default=True, is_active=True)
        .first()
    )
    if bot is None or not bot.is_configured:
        return None
    return bot


def resolve_org_from_user_and_context(user, fallback_org=None):
    """Pick the right org for a notification aimed at a specific user.

    Used by tasks that know *who* to notify but not *under which org*.
    Policy:

    1. If ``fallback_org`` is given, prefer it — the task knows exactly
       which tenant's bot should send (e.g. an announcement tied to a
       Building whose org is unambiguous).
    2. Otherwise fall back to the user's first active
       ``OrganizationMembership``. Works for the single-membership case
       which is by far the most common.
    3. Multi-membership without an explicit ``fallback_org`` picks the
       first active membership deterministically by PK, same rule the
       rest of the codebase uses in ``get_user_primary_organization``.
       Callers that care about multi-org users should pass
       ``fallback_org``.

    Returns ``None`` if the user has no memberships at all — callers
    should treat that as "no Telegram for this user" and return.
    """
    if fallback_org is not None:
        return fallback_org

    membership = (
        user.organization_memberships
        .filter(is_active=True)
        .select_related("organization")
        .order_by("id")
        .first()
    )
    return membership.organization if membership else None
