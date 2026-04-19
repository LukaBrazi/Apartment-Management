"""PR-11 stub: the PR-10 ``0009_backfill_residency_from_profile``
migration is historical after PR-11 (it reads ``Profile.unit_id``,
which no longer exists on the live Profile model).  Tests for the
backfill have been retired; the migration itself stays in place so
existing databases still converge via the normal migrate path.
"""
