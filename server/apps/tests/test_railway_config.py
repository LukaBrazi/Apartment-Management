"""Lock-down tests for Railway deployment configuration.

These guard rails ensure future contributors don't re-introduce mistakes
that previously broke production deploys. Each test points to the
docs/RAILWAY_SETUP.md section that explains why.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RAILWAY_TOML = REPO_ROOT / "railway.toml"
RAILWAY_SETUP_DOC = REPO_ROOT / "docs" / "RAILWAY_SETUP.md"


def _railway_toml() -> str:
    assert RAILWAY_TOML.exists(), f"railway.toml missing at {RAILWAY_TOML}"
    return RAILWAY_TOML.read_text()


class TestRailwayTomlGuards:
    def test_no_healthcheck_path_at_root_level(self):
        """``healthcheckPath`` must be configured per-service in Railway
        dashboard, NOT in root railway.toml.

        Background: this repo deploys 3 services from the same Dockerfile —
        Web, Celery Worker, Celery Beat. Only Web has an HTTP server. If
        ``healthcheckPath`` is at root level it propagates to all three,
        and Celery deploys fail with 'service unavailable'.

        See docs/RAILWAY_SETUP.md → 'Найчастіша помилка'.
        """
        src = _railway_toml()

        # Look for an UNCOMMENTED healthcheckPath assignment.
        # Comments in toml start with '#'.
        violations = []
        for line_no, raw in enumerate(src.splitlines(), start=1):
            stripped = raw.strip()
            if stripped.startswith("#"):
                continue
            if "healthcheckPath" in stripped and "=" in stripped:
                violations.append(f"line {line_no}: {stripped}")

        assert not violations, (
            "Active 'healthcheckPath' found in railway.toml — REMOVE it. "
            "It must be set per-service in Railway dashboard (Web only). "
            "Read docs/RAILWAY_SETUP.md before re-adding.\n\n"
            f"Found:\n  " + "\n  ".join(violations)
        )

    def test_no_healthcheck_timeout_at_root_level(self):
        """Same reasoning as healthcheckPath."""
        src = _railway_toml()
        violations = []
        for line_no, raw in enumerate(src.splitlines(), start=1):
            stripped = raw.strip()
            if stripped.startswith("#"):
                continue
            if "healthcheckTimeout" in stripped and "=" in stripped:
                violations.append(f"line {line_no}: {stripped}")
        assert not violations, (
            "Active 'healthcheckTimeout' in railway.toml — remove it.\n  "
            + "\n  ".join(violations)
        )

    def test_railway_setup_doc_exists(self):
        """If anyone deletes the setup doc, this test forces them to think
        twice — the doc is the single source of truth for Railway config."""
        assert RAILWAY_SETUP_DOC.exists(), (
            f"docs/RAILWAY_SETUP.md is missing. Restore it — it is the "
            f"only place that documents per-service Railway config."
        )

    def test_railway_toml_points_to_setup_doc(self):
        """railway.toml must reference docs/RAILWAY_SETUP.md so future
        editors find the explanation when they look at the file."""
        src = _railway_toml()
        assert "docs/RAILWAY_SETUP.md" in src, (
            "railway.toml must reference docs/RAILWAY_SETUP.md in its "
            "comments so future editors find the per-service config rules."
        )
