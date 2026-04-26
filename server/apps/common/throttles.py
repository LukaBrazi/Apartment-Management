"""Custom DRF throttles (PR-8).

``WriteOnlyScopedThrottle`` exists because two of the four endpoints we
want to rate-limit on creation are ``ListCreateAPIView`` mixed
read+write views (most notably ``VehiclePassListCreateAPIView``).  The
standard ``ScopedRateThrottle`` would burn the same budget on every GET
poll the badge counter performs — turning a "30 creates per hour" cap
into "30 page loads per hour".

We sidestep that by short-circuiting ``get_cache_key`` for safe HTTP
methods (GET / HEAD / OPTIONS) — DRF interprets a ``None`` cache key as
"do not throttle this request".  Write methods fall through to the
parent implementation and use the bound ``throttle_scope`` exactly like
``ScopedRateThrottle`` would.

Usage::

    class VehiclePassListCreateAPIView(generics.ListCreateAPIView):
        throttle_classes = [WriteOnlyScopedThrottle]
        throttle_scope = "pass_create"

For pure ``CreateAPIView`` views (``IssueCreateAPIView``,
``PostCreateAPIView``, ``RatingCreateAPIView``) we just use the stock
``ScopedRateThrottle`` — there is no read path on those views so the
write/read distinction is moot.
"""
from __future__ import annotations

from rest_framework.throttling import ScopedRateThrottle


class WriteOnlyScopedThrottle(ScopedRateThrottle):
    """Apply the bound ``throttle_scope`` only on write methods.

    Returning ``None`` from ``get_cache_key`` is DRF's documented opt-out
    for a single request — the parent ``allow_request`` checks for it
    before fetching/incrementing the rate counter.
    """

    def get_cache_key(self, request, view):  # type: ignore[override]
        if request.method.lower() in ("get", "head", "options"):
            return None
        return super().get_cache_key(request, view)
