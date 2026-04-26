"""Re-export shared permission classes from ``apps.common.permissions``.

PR-1 (fix/critical-security) consolidated all permission classes into
``apps.common.permissions`` and removed the silent ``except Exception:
pass`` pattern. This module is kept as a thin re-export so existing
imports (``from apps.passes.permissions import IsGuardOrAdmin, IsTenant``)
keep working.
"""

from apps.common.permissions import IsGuardOrAdmin, IsTenant

__all__ = ["IsGuardOrAdmin", "IsTenant"]
