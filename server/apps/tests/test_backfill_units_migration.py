"""PR-7: legacy ``Apartment`` model was deleted; this file is a stub.

The original tests verified the ``0004_backfill_units_from_legacy_apartments``
data migration against a live ``Apartment`` model.  Since PR-7 removed both
``Apartment`` and ``Unit.apartment``, the historical schema those tests
exercised no longer exists at runtime and we can't import ``Apartment``.

The backfill migration file itself remains in the migration graph and
will still run forward correctly for any environment replaying from a
pre-PR-7 baseline — it uses ``apps.get_model()`` to access the historical
models, which Django provides during migration replay regardless of the
current code.
"""
