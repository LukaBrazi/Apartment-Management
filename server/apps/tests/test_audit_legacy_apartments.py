"""PR-7 deleted the legacy ``Apartment`` model and reduced the
``audit_legacy_apartments`` management command to a no-op notice.  The
invariants this file used to guard (bridge counts, tenant→unit backfill
readiness, building-string normalisation, complex→org ambiguity
roll-ups) are obsolete.

Stub retained because the sandbox that produced PR-7 cannot unlink
files; deletion happens when the branch is rebased in a non-sandboxed
environment.
"""
from __future__ import annotations
