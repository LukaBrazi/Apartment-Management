"""PR-7 dropped ``Issue.apartment`` entirely, which means there is no
longer any dual-read window to guard.  ``Issue.save()`` now only
validates ``unit``; the migration of legacy writes was completed by the
PR-1 backfill and the schema drop in ``apartments.0005``.

Stub retained because the sandbox that produced PR-7 cannot unlink
files.
"""
from __future__ import annotations
