"""Seed demo Ratings per plan §9.

35 ratings: every worker receives 3-6 ratings from residents with the
per-occupation average biased to match plan §9 (plumber stars, painter
below-average).  Respects the ``unique_together(rating_user, rated_user)``
— each resident rates a worker at most once.

Natural key: the ``(rating_user, rated_user)`` pair.  Reruns reuse rows
and don't bump counts.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:  # pragma: no cover
    from apps.ratings.models import Rating
    from .seed_users import SeededUser, UsersSeedResult

logger = logging.getLogger(__name__)

RATINGS_RNG_SEED = 909090

# Plan §9 — mean rating target per worker occupation.  Distribution
# around the mean picked to show UI variability (one rating low so the
# profile avg isn't artificially perfect).
OCCUPATION_PROFILES: dict[str, tuple[int, int, tuple[int, ...]]] = {
    # occupation → (ratings_count, target_mean_x10, sample_pool)
    "plumber":     (6, 48, (5, 5, 5, 5, 4, 5)),
    "electrician": (5, 45, (5, 5, 4, 5, 4)),
    "carpenter":   (4, 42, (5, 4, 4, 4)),
    "mason":       (4, 38, (4, 4, 4, 3)),
    "roofer":      (4, 40, (4, 4, 5, 3)),
    "painter":     (3, 35, (4, 3, 4)),
    "hvac":        (5, 46, (5, 5, 4, 5, 4)),
}
# Target total: 6+5+4+4+4+3+5 = 31 + second painter ~4 = 35.

SECOND_PAINTER_SAMPLE: tuple[int, ...] = (4, 4, 5, 4)


COMMENTS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (5, (
        "Дуже швидко прийшов, акуратно полагодив.",
        "Все зробив професійно, рекомендую.",
        "Чудова робота, дякую!",
        "Прийшов вчасно, чистий після себе.",
    )),
    (4, (
        "Добре, але довелось нагадати про час.",
        "Все ок, виконав як і домовились.",
        "Акуратно. Без зайвих питань.",
    )),
    (3, (
        "Терпимо. Є що покращити.",
        "Середня робота, без претензій, але й без захвату.",
    )),
    (2, (
        "Не дуже — довелось викликати іншого майстра.",
    )),
    (1, (
        "Чесно скажу — не дуже. Довелось викликати двічі.",
    )),
)


@dataclass
class RatingsSeedResult:
    created: int = 0
    skipped: int = 0
    by_occupation: dict[str, int] = field(default_factory=dict)
    ratings: list["Rating"] = field(default_factory=list, repr=False)


# ─────────────────────────── public entry ───────────────────────────────────


def seed(*, users_result: "UsersSeedResult") -> RatingsSeedResult:
    """Seed the 35 demo ratings (plan §9)."""
    from apps.ratings.models import Rating

    result = RatingsSeedResult()
    rng = random.Random(RATINGS_RNG_SEED)

    residents = [r for r in users_result.residents if r.user is not None]
    if len(residents) < 6:
        raise RuntimeError("seed_ratings: need ≥ 6 residents for rating spread")

    comment_map: dict[int, tuple[str, ...]] = {r: texts for r, texts in COMMENTS}

    # Group workers by occupation — handle dupes (painter + painter2).
    worker_groups: dict[str, list["SeededUser"]] = {}
    for w in users_result.workers:
        occ = w.role  # seeded role equals occupation string
        worker_groups.setdefault(occ, []).append(w)

    with transaction.atomic():
        for occupation, workers in worker_groups.items():
            _, _, primary_sample = OCCUPATION_PROFILES.get(
                occupation, (3, 40, (4, 4, 3)),
            )

            for w_idx, worker in enumerate(workers):
                sample = (
                    SECOND_PAINTER_SAMPLE if (occupation == "painter" and w_idx > 0)
                    else primary_sample
                )
                created = _rate_worker(
                    Rating, worker, sample, residents, comment_map, rng, result,
                )
                result.by_occupation[worker.email] = created

    logger.info(
        "seed_ratings: created=%d skipped=%d by_email=%s",
        result.created, result.skipped, result.by_occupation,
    )
    return result


def _rate_worker(
    Rating,
    worker,
    sample: tuple[int, ...],
    residents: list,
    comment_map: dict[int, tuple[str, ...]],
    rng: random.Random,
    result: RatingsSeedResult,
) -> int:
    """Create up to ``len(sample)`` ratings for one worker.  Returns # created."""
    # Pick a deterministic residents slice rotated by worker.pk so different
    # workers get ratings from different neighbours (not always the same 5).
    start = worker.user.pk % len(residents)
    want = min(len(sample), len(residents))
    created_count = 0
    for i in range(want):
        rater = residents[(start + i) % len(residents)]
        if rater.user.pk == worker.user.pk:
            continue
        rating_value = sample[i]
        comments = comment_map.get(rating_value, ("",))
        comment = comments[i % len(comments)]

        _obj, created = Rating.objects.get_or_create(
            rating_user=rater.user,
            rated_user=worker.user,
            defaults={"rating": rating_value, "comment": comment},
        )
        if created:
            result.created += 1
            created_count += 1
        else:
            result.skipped += 1
    return created_count
