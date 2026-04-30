"""Lock-down regex tests for the daily TG digest renderer (PR-18).

These tests read ``apps/common/tasks.py`` as text and assert that the
critical morning/evening branches stay wired in the renderer. A normal
refactor that accidentally drops the billing OR security section will
fail here — even before the runtime tests run — so the regression is
caught at static-pattern level too.

Companion to ``test_health_monitoring.py`` runtime checks; do NOT delete
these without also planning a replacement contract elsewhere.
"""
from __future__ import annotations

import re
from pathlib import Path


TASKS_PATH = (
    Path(__file__).resolve().parents[1] / "tasks.py"
)


def _read_tasks() -> str:
    return TASKS_PATH.read_text(encoding="utf-8")


def test_morning_branch_renders_billing_section():
    src = _read_tasks()
    # Helper exists and renders the section header
    assert "_build_morning_message" in src
    assert "_format_billing_section" in src
    assert "💰 Білінг" in src


def test_evening_branch_renders_security_section():
    src = _read_tasks()
    assert "_build_evening_message" in src
    assert "_format_security_section" in src
    assert "🔐 Безпека" in src


def test_daily_task_dispatches_by_local_hour():
    """Branching on ``localtime().hour`` must remain in place."""
    src = _read_tasks()
    # Permit either ``< 12`` or ``hour < 12`` inline branches.
    assert re.search(
        r"is_morning\s*=\s*[^\n]*hour\s*<\s*12", src,
    ), "morning detection on local hour < 12 missing in tasks.py"


def test_daily_task_uses_both_digest_builders():
    """The task must call both digest builders by name."""
    src = _read_tasks()
    assert "build_billing_digest" in src
    assert "build_security_digest" in src


def test_health_section_helper_shared_by_both_branches():
    """``_format_health_lines`` is the canonical health renderer."""
    src = _read_tasks()
    assert "_format_health_lines" in src
    # Both branches must invoke it
    occurrences = src.count("_format_health_lines(")
    assert occurrences >= 2, (
        "morning AND evening builders must both call _format_health_lines"
    )
