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
    """Return the primary active bot for ``organization``.

    Preconditions checked (in order of cheapness):

    1. ``organization`` must be truthy.  Passing ``None`` is a common
       shape when signal handlers fire before an org is attached — we
       treat it the same as "no bot", not as an error.
    2. The org must have ``telegram_notifications`` enabled in its
       ``features`` JSONField.  That's the customer-facing kill switch.
    3. The org must have an ``OrganizationBot`` row with ``is_primary``
       and ``is_active`` both ``True``.  ``is_configured`` additionally
       verifies the token and username are filled in — otherwise the
       send would fail on the Telegram API side anyway.
    """
    if organization is None:
        return None
    if not organization.is_feature_enabled(TELEGRAM_FEATURE_FLAG):
        return None

    bot = (
        OrganizationBot.objects
        .filter(organization=organization, is_primary=True, is_active=True)
        .first()
    )
    if bot is None:
        logger.debug(
            "notifications: no primary bot for org=%s (feature on, table empty)",
            getattr(organization, "slug", "?"),
        )
        return None
    if not bot.is_configured:
        logger.debug(
            "notifications: bot for org=%s present but not configured "
            "(missing token or username)",
            organization.slug,
        )
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
