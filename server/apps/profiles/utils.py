"""Profile utility functions.

PR-6: consolidate the 3 copy-paste ``get_avatar`` blocks from
``apps.posts.serializers`` into a single helper so changes to the avatar
storage backend, exception handling, or URL construction live in one place.
"""
from __future__ import annotations

import logging
from typing import Optional

from rest_framework.request import Request

from apps.profiles.models import Profile

logger = logging.getLogger(__name__)


def get_avatar_url(user, request: Optional[Request] = None) -> Optional[str]:
    """Return the avatar URL for ``user``, or ``None`` if not available.

    The previous in-line implementation in ``posts/serializers.py``
    swallowed every exception silently with ``except Exception``.  This
    helper narrows the catch to the specific failure modes that actually
    occur (missing profile / missing file / unconfigured storage) and
    logs the unexpected ones at WARNING level so we can spot real
    storage misconfigurations in prod.

    When ``request`` is provided the URL is returned as an absolute URI;
    otherwise the storage-backend's relative URL is returned (matches
    the legacy behaviour).
    """
    try:
        profile = user.profile
    except (AttributeError, Profile.DoesNotExist):
        return None

    avatar = getattr(profile, "avatar", None)
    if not avatar:
        return None

    try:
        url = avatar.url
    except (ValueError, AttributeError) as exc:
        logger.warning(
            "Failed to read avatar URL for user %s: %s", getattr(user, "pk", None), exc
        )
        return None

    if request is not None:
        return request.build_absolute_uri(url)
    return url
