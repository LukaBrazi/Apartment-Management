"""Seed demo VehiclePasses per plan §8.

22 passes across 5 buckets:

* 8 × ``pending`` dated next-7-days (tenant-initiated upcoming visits)
* 3 × ``pending`` dated today (showcases the guard-closes-pass flow)
* 4 × ``closed`` closed today (guard@demo.com closed — shows audit log)
* 5 × ``closed`` closed within the last week (variety of guards)
* 2 × ``closed`` closed 30+ days ago (archive)

Natural key: ``(tenant, visit_date, car_number)``.  Using
``get_or_create`` with that triple keeps rerun idempotent without
colliding on today's reseed.

Signal hygiene
--------------
``apps.notifications.signals.on_pass_saved`` fires a Celery task when a
``closed`` pass lands.  Disconnected for the full loop and reconnected
in the context-manager's ``__exit__``.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from .helpers import ua_car_plate

if TYPE_CHECKING:  # pragma: no cover
    from apps.passes.models import VehiclePass
    from .seed_users import SeededUser, UsersSeedResult

logger = logging.getLogger(__name__)

PASSES_RNG_SEED = 77777


# Pass spec: (bucket_name, count, day_offset_range, status, closed_age_range).
# Interpreted per helper ``_generate_entries``.
PASS_BUCKETS: tuple[tuple[str, int, tuple[int, int], str, tuple[int, int] | None], ...] = (
    ("upcoming",       8, (1, 7),    "pending", None),
    ("today_pending",  3, (0, 0),    "pending", None),
    ("closed_today",   4, (0, 0),    "closed",  (0, 0)),
    ("closed_week",    5, (-7, -1),  "closed",  (-7, -1)),
    ("closed_archive", 2, (-40, -32), "closed", (-40, -32)),
)


@dataclass
class PassesSeedResult:
    created: int = 0
    skipped: int = 0
    pending: int = 0
    closed: int = 0
    passes: list["VehiclePass"] = field(default_factory=list, repr=False)


# ──────────────────────────── public entry ──────────────────────────────────


def seed(
    *,
    users_result: "UsersSeedResult",
    count: int = 22,
) -> PassesSeedResult:
    """Create the 22 demo vehicle passes (plan §8)."""
    from apps.passes.models import VehiclePass

    result = PassesSeedResult()
    rng = random.Random(PASSES_RNG_SEED)

    tenants = _tenant_pool(users_result)
    if not tenants:
        raise RuntimeError("seed_passes: no tenants with apartments")
    guards = users_result.guards
    if not guards:
        raise RuntimeError("seed_passes: no guards seeded")

    entries = _generate_entries(count)

    with _pass_signal_suspended():
        with transaction.atomic():
            for i, (bucket, status, visit_offset, closed_offset) in enumerate(entries):
                tenant = tenants[i % len(tenants)]
                guard = guards[i % len(guards)]
                car = ua_car_plate(rng)
                visit_date = (timezone.localdate() + timedelta(days=visit_offset))

                defaults = {
                    "unit": tenant.unit,
                    "status": status,
                    "comment": _comment_for(bucket),
                }
                if status == "closed" and closed_offset is not None:
                    defaults["closed_by"] = guard.user
                    defaults["closed_at"] = timezone.now() + timedelta(
                        days=closed_offset, hours=(i % 8),
                    )

                obj, created = VehiclePass.objects.get_or_create(
                    tenant=tenant.user,
                    visit_date=visit_date,
                    car_number=car,
                    defaults=defaults,
                )
                if created:
                    result.created += 1
                else:
                    result.skipped += 1

                result.passes.append(obj)
                if obj.status == "pending":
                    result.pending += 1
                else:
                    result.closed += 1

    logger.info(
        "seed_passes: created=%d skipped=%d pending=%d closed=%d",
        result.created, result.skipped, result.pending, result.closed,
    )
    return result


# ────────────────────────── internal helpers ────────────────────────────────


def _tenant_pool(users_result: "UsersSeedResult") -> list["SeededUser"]:
    """Residents with apartments — the only users who can create passes."""
    pool = [r for r in users_result.residents if r.unit is not None]
    if users_result.tenant is not None and users_result.tenant.unit is not None:
        pool.insert(0, users_result.tenant)
    return pool


def _generate_entries(
    count: int,
) -> list[tuple[str, str, int, int | None]]:
    """Expand PASS_BUCKETS → deterministic list of ``count`` entries.

    Returns tuples of ``(bucket_name, status, visit_day_offset, closed_day_offset)``.
    If ``count < 22``, proportionally shrink each bucket keeping at least 1.
    """
    plan_total = sum(n for _, n, _, _, _ in PASS_BUCKETS)
    scale = count / plan_total
    remaining = count
    scaled: list[tuple[str, int, tuple[int, int], str, tuple[int, int] | None]] = []
    for name, n, visit_range, status, closed_range in PASS_BUCKETS:
        take = max(1, int(round(n * scale)))
        take = min(take, remaining)
        scaled.append((name, take, visit_range, status, closed_range))
        remaining -= take
    if remaining > 0:
        # Stuff into the biggest bucket.
        idx = max(range(len(scaled)), key=lambda i: scaled[i][1])
        name, n, vr, st, cr = scaled[idx]
        scaled[idx] = (name, n + remaining, vr, st, cr)

    out: list[tuple[str, str, int, int | None]] = []
    for name, n, visit_range, status, closed_range in scaled:
        lo_v, hi_v = visit_range
        for i in range(n):
            visit_off = lo_v + (i % (hi_v - lo_v + 1))
            closed_off = None
            if closed_range is not None:
                lo_c, hi_c = closed_range
                closed_off = lo_c + (i % (hi_c - lo_c + 1))
            out.append((name, status, visit_off, closed_off))
    return out


def _comment_for(bucket: str) -> str:
    return {
        "upcoming": "Привезуть меблі, будь ласка пропустіть.",
        "today_pending": "Гості на день народження, очікую з 18:00.",
        "closed_today": "Пропущено охороною, все добре.",
        "closed_week": "Візит завершено, пропуск закрито.",
        "closed_archive": "Архівний пропуск минулого місяця.",
    }.get(bucket, "")


class _pass_signal_suspended:
    """Disconnect ``on_pass_saved`` so we don't queue Celery notifications."""

    def __enter__(self):
        from apps.notifications.signals import on_pass_saved
        from apps.passes.models import VehiclePass
        from django.db.models.signals import post_save

        self._spec = (post_save, on_pass_saved, VehiclePass)
        post_save.disconnect(on_pass_saved, sender=VehiclePass)
        return self

    def __exit__(self, exc_type, exc, tb):
        signal, receiver, sender = self._spec
        signal.connect(receiver, sender=sender, weak=False)
        return False
