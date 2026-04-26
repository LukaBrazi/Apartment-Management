"""Lock-down test: production.py keeps JSON logging configured (PR-8).

We can't ``import config.settings.production`` from a test because the
prod module reads required env vars (``DJANGO_SECRET_KEY``,
``DATABASE_URL``, ``REDIS_URL``, R2 / SMTP credentials, …) at import
time and a missing one fails the boot loud — which is the *desired*
behaviour for prod, but breaks pytest collection.

Instead, read the file as text and assert the structural pieces of the
JSON LOGGING block are present.  Same pattern as
``test_security_headers`` for the Next.js config.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# server/apps/common/tests/test_logging_config.py
#  → server/apps/common/tests → … → server/config/settings/production.py
PROD_SETTINGS = (
    Path(__file__).resolve().parents[3]
    / "config"
    / "settings"
    / "production.py"
)


@pytest.fixture(scope="module")
def prod_text() -> str:
    assert PROD_SETTINGS.exists(), (
        f"Expected production settings at {PROD_SETTINGS} — has the "
        "layout moved?  Update apps/common/tests/test_logging_config.py."
    )
    return PROD_SETTINGS.read_text(encoding="utf-8")


class TestProductionLoggingConfig:
    def test_json_logger_referenced(self, prod_text: str):
        """The JSON formatter class string must be present.  This is
        the contract: removing it would silently revert prod logs to
        the plain-text base.py format and break log shippers expecting
        structured input.
        """
        assert "pythonjsonlogger.jsonlogger.JsonFormatter" in prod_text, (
            "Expected pythonjsonlogger.jsonlogger.JsonFormatter in "
            "production.py — JSON logging may have been removed.  If "
            "intentional, also drop python-json-logger from "
            "requirements/base.txt and update docs/RAILWAY_SETUP.md."
        )

    def test_logging_dict_overrides_base(self, prod_text: str):
        """``LOGGING = {`` must be assigned at module level, otherwise
        we silently inherit the plain-text dict from base.py.
        """
        assert re.search(r"^LOGGING\s*=\s*\{", prod_text, flags=re.MULTILINE), (
            "production.py must override LOGGING (got no top-level "
            "assignment).  Without the override, prod inherits the "
            "plain-text formatter from base.py."
        )

    def test_canonical_field_renames_present(self, prod_text: str):
        """The rename_fields block normalises ``asctime`` → ``timestamp``
        etc., so log aggregators can rely on canonical names.  Drop
        these and downstream parsers break in subtle ways.
        """
        for canonical in ("timestamp", "level", "logger"):
            assert canonical in prod_text, (
                f"Canonical log field '{canonical}' missing from "
                "production.py LOGGING — rename_fields block was "
                "likely deleted."
            )

    def test_handlers_use_json_formatter(self, prod_text: str):
        """The console handler must reference the ``json`` formatter,
        not ``verbose``/``simple``/etc.  A misnamed reference here
        would silently fall back to Django's default formatter and
        emit unstructured text.
        """
        # Look for the "console" handler block specifically referencing
        # "formatter": "json".  We accept either single or double quotes
        # for robustness against future style edits.
        pattern = re.compile(
            r"\"console\"\s*:\s*\{[^}]*\"formatter\"\s*:\s*\"json\"",
            re.DOTALL,
        )
        assert pattern.search(prod_text), (
            "console handler must declare formatter='json' — check "
            "production.py LOGGING['handlers']['console']."
        )


class TestRequirementsPin:
    """python-json-logger must be pinned in requirements/base.txt.

    Without it the LOGGING dict raises ``ValueError: Unable to
    configure formatter 'json'`` on Django startup, taking the whole
    Railway service offline.
    """

    REQ_BASE = (
        Path(__file__).resolve().parents[3] / "requirements" / "base.txt"
    )

    def test_python_json_logger_pinned(self):
        text = self.REQ_BASE.read_text(encoding="utf-8")
        assert re.search(
            r"python-json-logger\s*==\s*\d+\.\d+\.\d+",
            text,
        ), (
            "python-json-logger must be pinned (==x.y.z) in "
            "requirements/base.txt.  Production logging depends on it."
        )
