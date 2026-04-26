"""Lock-down test: ensure CSP + security headers stay configured (PR-8).

The actual headers are emitted by Next.js (``client/next.config.mjs``)
not Django, so we cannot hit a URL and assert response headers from
pytest.  But the config file is part of the same repo, so we read it as
text and assert the critical strings are present.

Why this matters: a future "clean up" commit could trivially delete the
``headers()`` callback or strip ``connect-src`` and the whole frontend
would silently lose its CSP — every request would 200 OK in dev (no
CSP enforcement on relaxed dev tools) and only blow up once it hits a
strict browser in production.  This test catches that at PR review.

The assertions are intentionally string-level rather than JS-parser
level: we don't run Node from pytest, and a regex check is enough to
detect "someone removed the entire block".
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# server/ → repo root → client/next.config.mjs
REPO_ROOT = Path(__file__).resolve().parents[4]
NEXT_CONFIG = REPO_ROOT / "client" / "next.config.mjs"


@pytest.fixture(scope="module")
def next_config_text() -> str:
    assert NEXT_CONFIG.exists(), (
        f"Expected Next.js config at {NEXT_CONFIG} — has the project layout "
        "moved?  Update apps/common/tests/test_security_headers.py."
    )
    return NEXT_CONFIG.read_text(encoding="utf-8")


class TestSecurityHeadersConfig:
    def test_csp_header_block_present(self, next_config_text: str):
        """The string ``Content-Security-Policy`` must appear at least
        once in the config.  Removing it would silently disable CSP for
        every Vercel response.
        """
        assert "Content-Security-Policy" in next_config_text, (
            "Content-Security-Policy entry missing from next.config.mjs — "
            "CSP headers were the entire reason PR-8 added the headers() "
            "callback.  If you genuinely need to remove CSP, also remove "
            "this test and document why in docs/SECURITY_BACKLOG.md."
        )

    def test_csp_includes_required_directives(self, next_config_text: str):
        """Sanity: the CSP value covers the directives we rely on for
        defence-in-depth.  A surgical "loosened script-src for one
        analytics tool" change is fine — silently dropping the entire
        ``frame-ancestors`` line is not.
        """
        required_directives = (
            "default-src",
            "script-src",
            "style-src",
            "img-src",
            "connect-src",
            "frame-ancestors",
            "object-src",
        )
        missing = [d for d in required_directives if d not in next_config_text]
        assert not missing, (
            f"CSP is missing required directives: {missing}.  "
            f"See client/next.config.mjs and PR-8 commit notes."
        )

    def test_connect_src_allows_api_origin(self, next_config_text: str):
        """``connect-src`` must list the API origin or fetch() calls
        from the browser get blocked.  This was the #1 footgun while
        rolling out the CSP.
        """
        # Match the actual CSP directive string (inside double-quoted
        # JS literals) rather than any prose mention of "connect-src"
        # in the file's own comments.  The directive line ends at the
        # closing ``"`` of the JS string, never crossing a newline.
        connect_src_match = re.search(
            r'"connect-src[^"\n]+"', next_config_text
        )
        assert connect_src_match, (
            "connect-src directive not found inside a CSP value string."
        )
        line = connect_src_match.group(0)
        assert (
            "api.apartmentos.org" in line
            or "up.railway.app" in line
            or "'self'" in line
        ), (
            f"connect-src must allow at least one API origin "
            f"(api.apartmentos.org / *.up.railway.app / 'self'). "
            f"Got: {line}"
        )

    def test_classic_security_headers_present(self, next_config_text: str):
        """X-Frame-Options, X-Content-Type-Options, Referrer-Policy and
        Permissions-Policy are all part of the same headers() block.
        Lock them in too — they cost nothing and removing them is
        almost always a mistake.
        """
        for header in (
            "X-Frame-Options",
            "X-Content-Type-Options",
            "Referrer-Policy",
            "Permissions-Policy",
        ):
            assert header in next_config_text, (
                f"Header '{header}' missing from next.config.mjs."
            )

    def test_headers_callback_wired(self, next_config_text: str):
        """The ``headers()`` async callback must be reachable from the
        exported config — otherwise the values above are dead code.
        """
        assert "async headers()" in next_config_text, (
            "headers() callback not declared on the exported nextConfig "
            "object — the security headers above are unreachable."
        )
