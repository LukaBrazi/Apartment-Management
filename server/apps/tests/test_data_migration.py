"""PR-7 deleted the legacy ``Apartment`` model, which removed the
``Apartment ↔ Unit`` OneToOne linkage these tests were locking in.
The new canonical chain ``Building → Entrance → Unit`` is guarded by
factory-level unique constraints and the ``test_smoke`` / organisation
isolation suites; no separate data-migration invariants remain.

Stub retained because the sandbox that produced PR-7 cannot unlink
files.
"""
from __future__ import annotations
