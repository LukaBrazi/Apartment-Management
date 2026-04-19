"""PR-6 removed ``MyApartmentAPIView`` along with the rest of the
tenant-facing ``/apartments/*`` endpoints.  The invariants this file
used to lock in (anonymous → 401, missing apartment → 200 empty dict,
tenant → serialized apartment, no cross-user leak, deterministic
.first()) are obsolete: the frontend no longer reads the legacy
``Apartment`` payload, and the Profile endpoint now owns the tenant's
unit/building fields.

File kept as a no-op stub because the sandbox that generated PR-6
cannot delete files from disk.  Actual removal happens when the branch
is rebased in a non-sandboxed environment.
"""
from __future__ import annotations
