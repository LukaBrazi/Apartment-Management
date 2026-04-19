"""Deprecated.

This suite pinned the legacy ``ProfileSerializer.apartment`` wire
format that shipped Unit data inside a nested Apartment-shaped dict.

The ``apartment`` field has been removed — the frontend now consumes
the flat ``unit_*`` / ``building_*`` aliases directly — so there is
nothing left to pin.  The file is kept as an empty placeholder to
avoid breaking imports in any leftover tooling; delete at will.
"""
