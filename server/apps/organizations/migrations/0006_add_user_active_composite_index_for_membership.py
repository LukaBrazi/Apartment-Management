"""Migration: add composite (user, is_active) index on OrganizationMembership.

PR-7 — production quick wins. The hot auth path
``apps.organizations.utils.get_user_organizations(user)`` filters
``OrganizationMembership`` by ``user`` and ``is_active=True`` together; a
composite index lets Postgres satisfy the predicate with a single index
seek instead of choosing one of the two single-column indexes and
filtering the rest in memory. This view is hit on every authenticated
request that goes through Issue / VehiclePass / Posts list endpoints.

The migration is index-only: no schema change to columns, no data
migration. Index creation on a small membership table is fast; on
larger production data a future migration may want to add
``CONCURRENTLY`` via ``AddIndexConcurrently`` to avoid a write-lock
window — out of scope for this quick win.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0005_organization_default_features"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="organizationmembership",
            index=models.Index(
                fields=["user", "is_active"],
                name="orgmem_user_active_idx",
            ),
        ),
    ]
