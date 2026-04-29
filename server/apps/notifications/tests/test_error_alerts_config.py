"""Lock-down: production LOGGING wires TelegramErrorHandler to django.request.

Regex-based tests that read production.py as text and assert the critical
config lines exist. Pattern from CLAUDE.md (Lock-down regex tests, 2026-04-26)
— catches regressions that runtime tests can't (e.g. someone removing the
handler from the django.request logger during a refactor).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PROD_PATH = REPO_ROOT / "server" / "config" / "settings" / "production.py"


def test_production_logging_includes_telegram_alerts_handler():
    src = PROD_PATH.read_text()
    assert "telegram_alerts" in src, (
        "production.py LOGGING must register a 'telegram_alerts' handler "
        "(see PR-9 / apps.notifications.error_alerts.TelegramErrorHandler)."
    )
    assert "TelegramErrorHandler" in src, (
        "Handler class must be referenced in production.py LOGGING."
    )


def test_django_request_logger_uses_telegram_alerts():
    src = PROD_PATH.read_text()
    # Heuristic: find the 'django.request' logger block and check it uses
    # telegram_alerts. The block contains nested dicts via 'handlers':
    # ["console", "telegram_alerts"], so we match the outer braces non-greedy.
    block = re.search(
        r'"django\.request"\s*:\s*\{[^}]*\}',
        src,
        flags=re.DOTALL,
    )
    assert block, "production.py must define a 'django.request' logger"
    assert "telegram_alerts" in block.group(0), (
        "django.request logger must include 'telegram_alerts' in its handlers — "
        "otherwise 5xx errors won't reach the Telegram channel."
    )


def test_telegram_alerts_handler_level_is_error():
    """Handler must be ERROR-level so 4xx (WARNING) doesn't flood Telegram."""
    src = PROD_PATH.read_text()
    # Find the telegram_alerts handler block
    block = re.search(
        r'"telegram_alerts"\s*:\s*\{[^}]*\}',
        src,
        flags=re.DOTALL,
    )
    assert block, "production.py must define a 'telegram_alerts' handler"
    handler_src = block.group(0)
    assert '"ERROR"' in handler_src or "'ERROR'" in handler_src, (
        "telegram_alerts handler must have level=ERROR — otherwise 4xx warnings "
        "(which are logged at WARNING by django.request) will flood the channel."
    )
