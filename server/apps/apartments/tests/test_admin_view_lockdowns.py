"""PR-14 lock-down tests for the apartments admin layer.

These regex-based tests guard the source files themselves against a
regression that would re-open Bug 1 (org-spoofing / invisible building):

* ``BuildingSerializer`` MUST NOT include ``organization`` as a writable
  field — the FK is assigned by ``perform_create`` server-side.
* ``AdminBuildingListCreateAPIView`` MUST override ``perform_create``.
* ``BuildingCreateAPIView`` (legacy endpoint) MUST also override
  ``perform_create`` — frontend currently posts there.

Lock-down regex tests intentionally read source as text — they catch
the regression even if the test author forgot to write a runtime test
for the new branch.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


SERVER_DIR = Path(__file__).resolve().parents[3]
SERIALIZERS = SERVER_DIR / "apps" / "apartments" / "serializers.py"
VIEWS = SERVER_DIR / "apps" / "apartments" / "views.py"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_building_serializer_does_not_expose_organization_as_writable():
    """``BuildingSerializer.Meta.fields`` MUST NOT contain ``organization``.

    Allowing it would let any staff caller spoof the FK.  The read-only
    surrogate ``organization_name`` is fine and stays.
    """
    src = _read(SERIALIZERS)
    # Locate the BuildingSerializer.Meta.fields list.
    match = re.search(
        r"class\s+BuildingSerializer\b.*?class\s+Meta\b.*?fields\s*=\s*\[(?P<fields>.*?)\]",
        src,
        re.DOTALL,
    )
    assert match, "BuildingSerializer.Meta.fields not found"
    fields_block = match.group("fields")
    # Token-level check: a bare ``"organization"`` (not
    # ``"organization_name"``) is forbidden.
    tokens = [t.strip().strip("\"'") for t in fields_block.split(",")]
    assert "organization" not in tokens, (
        "BuildingSerializer.Meta.fields must NOT contain a writable "
        '"organization" field — the FK is set by perform_create. '
        "Use organization_name (read-only) for display instead."
    )


def test_admin_building_list_create_view_overrides_perform_create():
    """``AdminBuildingListCreateAPIView`` MUST define its own
    ``perform_create`` so the org FK is pinned to the caller."""
    src = _read(VIEWS)
    match = re.search(
        r"class\s+AdminBuildingListCreateAPIView\b[\s\S]*?(?=\nclass\s|\Z)",
        src,
    )
    assert match, "AdminBuildingListCreateAPIView class block not found"
    block = match.group(0)
    assert "def perform_create" in block, (
        "AdminBuildingListCreateAPIView must override perform_create() "
        "to assign the caller's organization."
    )


def test_legacy_building_create_view_overrides_perform_create():
    """The legacy ``BuildingCreateAPIView`` is what the frontend currently
    POSTs to. It MUST also pin the org FK — otherwise Bug 1 still bites
    everyone on the unmigrated form path."""
    src = _read(VIEWS)
    match = re.search(
        r"class\s+BuildingCreateAPIView\b[\s\S]*?(?=\nclass\s|\Z)",
        src,
    )
    assert match, "BuildingCreateAPIView class block not found"
    block = match.group(0)
    assert "def perform_create" in block, (
        "BuildingCreateAPIView must override perform_create() — the "
        "frontend currently posts to /buildings/create/."
    )


def test_entrance_grow_url_separate_from_patch_url():
    """The ``grow`` action gets its own URL path (``/grow/``) so it
    doesn't collide with the PATCH-rename surface on the detail
    endpoint.  This sidesteps the awkward 'PATCH detail with side
    effects' anti-pattern and makes audit logs easier to read.
    """
    urls = (SERVER_DIR / "apps" / "apartments" / "urls.py").read_text(encoding="utf-8")
    assert "entrances/<uuid:id>/grow/" in urls
    assert "entrances/<uuid:id>/" in urls
