"""Seed demo users: dispatchers, guards, workers, residents.

Maps plan §4 to concrete Django models.  Approximate totals (plan §0):

* 2 dispatchers (``is_staff=True``)
* 3 guards
* 8 workers (one per Profile.Occupation with some duplication for painter)
* 1 named tenant bound to the canonical ``А-TENANT_UNIT_NUMBER``
* 29 rank-and-file residents distributed across remaining populated units
* 2 unbound residents (``new1@demo.com``, ``new2@demo.com``) with no unit

The split between "named" / "pool" residents lets us keep deterministic
credentials for ``resident1..resident29`` while still pulling first/last
names from a shared Ukrainian pool.  ``residents_count`` is parametrised so
CI smoke can run a thinner seed.

Profile auto-creation: a ``post_save`` signal on ``User`` creates a default
``Profile`` row — we **update** it rather than re-create.  Writes via
``QuerySet.update()`` intentionally bypass ``Profile.save()`` (which would
recompute ``reputation``), because for deterministic seeding we want the
exact values we set.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import transaction

from .helpers import (
    DEFAULT_DEMO_PASSWORD,
    DEMO_EMAIL_DOMAIN,
    DISPATCHERS,
    GUARDS,
    RESIDENTS_POOL,
    TENANT_UNIT_ENTRANCE,
    TENANT_UNIT_NUMBER,
    UA_CITIES,
    VACANT_UNIT_DESIGNATIONS,
    WORKERS,
    dicebear_avatar_url,
    username_from_name,
)

if TYPE_CHECKING:  # pragma: no cover
    from apps.apartments.models import Unit
    from .seed_building import BuildingSeedResult

logger = logging.getLogger(__name__)


# ───────────────────────────── domain objects ────────────────────────────────


@dataclass
class SeededUser:
    """A user handle + the Unit they occupy (``None`` for staff/unbound)."""

    email: str
    user: object  # actual ``User`` instance; typed as object to keep imports lazy
    unit: "Unit | None" = None
    role: str = ""

    @property
    def username(self) -> str:
        return self.user.username  # type: ignore[attr-defined]


@dataclass
class UsersSeedResult:
    """Grouped handles returned to the orchestrator."""

    dispatchers: list[SeededUser] = field(default_factory=list)
    guards: list[SeededUser] = field(default_factory=list)
    workers: list[SeededUser] = field(default_factory=list)
    tenant: SeededUser | None = None
    residents: list[SeededUser] = field(default_factory=list)
    unbound_residents: list[SeededUser] = field(default_factory=list)

    def all(self) -> list[SeededUser]:
        out: list[SeededUser] = []
        out.extend(self.dispatchers)
        out.extend(self.guards)
        out.extend(self.workers)
        if self.tenant is not None:
            out.append(self.tenant)
        out.extend(self.residents)
        out.extend(self.unbound_residents)
        return out

    def workers_by_occupation(self) -> dict[str, list[SeededUser]]:
        """Group workers by ``Profile.Occupation`` for issue assignment."""
        # Local import to avoid bringing Profile into module scope too eagerly.
        from apps.profiles.models import Profile  # noqa: F401  (used via attr)

        grouped: dict[str, list[SeededUser]] = {}
        for w in self.workers:
            occupation = w.user.profile.occupation  # type: ignore[attr-defined]
            grouped.setdefault(occupation, []).append(w)
        return grouped


# ───────────────────────────── public entry point ───────────────────────────


@transaction.atomic
def seed(
    *,
    building_result: "BuildingSeedResult",
    residents_count: int = 32,
    password: str = DEFAULT_DEMO_PASSWORD,
) -> UsersSeedResult:
    """Create/update all demo users and link them to units where appropriate.

    Parameters
    ----------
    building_result:
        Output of :func:`apps.common.seed.seed_building.seed` — provides the
        Building and Unit handles without a DB round-trip.
    residents_count:
        Total residents to create (including the named ``tenant`` and the
        two unbound ``new*`` accounts).  Defaults to plan §0 (32).
    password:
        Password assigned to every user.  On prod callers pass
        ``os.environ["DEMO_PASSWORD"]`` per plan §10.
    """
    if residents_count < 4:
        raise ValueError("residents_count must be ≥ 4 (tenant + 1 resident + 2 new*)")

    from apps.profiles.models import Profile

    result = UsersSeedResult()

    # --- 1. Dispatchers (2, is_staff=True) ----------------------------------
    for idx, (first, last) in enumerate(DISPATCHERS, start=1):
        email = _dispatcher_email(idx)
        user, _ = _ensure_user(email, first, last, password, is_staff=True)
        _patch_profile(
            Profile,
            user,
            occupation=Profile.Occupation.TENANT,  # dispatcher is plan.§4 "tenant"
            gender=Profile.Gender.FEMALE if idx == 1 else Profile.Gender.MALE,
            phone=f"+380501111{idx:03d}",
            city=UA_CITIES[idx % len(UA_CITIES)],
            bio=(
                "Керуюча ЖК. Координую взаємодію мешканців, охорони та технічних "
                "служб. На зв'язку у робочий час через портал ApartmentOS."
            ),
        )
        result.dispatchers.append(
            SeededUser(email=email, user=user, role="dispatcher"),
        )

    # --- 2. Guards (3, Occupation.GUARD) ------------------------------------
    for idx, (first, last) in enumerate(GUARDS, start=1):
        email = _guard_email(idx)
        user, _ = _ensure_user(email, first, last, password, is_staff=False)
        _patch_profile(
            Profile,
            user,
            occupation=Profile.Occupation.GUARD,
            gender=Profile.Gender.MALE,
            phone=f"+380502222{idx:03d}",
            city="Київ",
            bio=(
                "Охоронець ЖК. Контролюю в'їзд транспорту та відвідувачів, "
                "оформлюю перепустки через портал."
            ),
        )
        result.guards.append(SeededUser(email=email, user=user, role="guard"))

    # --- 3. Workers (8, occupation per WORKERS pool) ------------------------
    for idx, worker in enumerate(WORKERS, start=1):
        email = f"{worker.occupation}{idx if idx > 1 and _already_has_occupation(email := f'{worker.occupation}@demo.com', result.workers) else ''}@demo.com"  # noqa: E501
        # Cleaner: regenerate with explicit index for painter2 etc.
        email = _worker_email(worker, idx)
        user, _ = _ensure_user(email, worker.first, worker.last, password, is_staff=False)
        _patch_profile(
            Profile,
            user,
            occupation=worker.occupation,
            gender=Profile.Gender.FEMALE if worker.first.endswith("а") else Profile.Gender.MALE,
            phone=f"+380503333{idx:03d}",
            city=UA_CITIES[(idx * 3) % len(UA_CITIES)],
            bio=(
                f"Працівник ЖК зі спеціалізацією {worker.occupation}. "
                "Приймаю заявки через портал, виконую планові та аварійні роботи."
            ),
        )
        result.workers.append(SeededUser(email=email, user=user, role=worker.occupation))

    # --- 4. Tenant (bound to А-TENANT_UNIT_NUMBER) --------------------------
    tenant_unit = building_result.units_by_key[
        (TENANT_UNIT_ENTRANCE, TENANT_UNIT_NUMBER)
    ]
    tenant_user, _ = _ensure_user(
        "tenant@demo.com", "Іван", "Тестовий", password, is_staff=False,
    )
    _patch_profile(
        Profile,
        tenant_user,
        occupation=Profile.Occupation.TENANT,
        gender=Profile.Gender.MALE,
        phone="+380504444001",
        city="Київ",
        bio=(
            "Мешканець демо-ЖК «Зелений Квартал». Використовую портал для заявок "
            "та перепусток, активний у форумі ОСББ."
        ),
        unit=tenant_unit,
    )
    # PR-11: the tenant's Unit is expressed as a primary ``Residency``
    # row (see ``_patch_profile``); ``Profile.unit`` was dropped.
    result.tenant = SeededUser(
        email="tenant@demo.com", user=tenant_user, unit=tenant_unit, role="tenant",
    )

    # --- 5. Residents 1..(residents_count - 3) bound to remaining units -----
    bound_count = residents_count - 3  # minus tenant, minus 2× new*
    bound_units = _available_units(building_result, skip_unit=tenant_unit)
    if bound_count > len(bound_units):
        raise ValueError(
            f"residents_count={residents_count} exceeds available units "
            f"({len(bound_units)} free after reserving tenant + vacant slots)",
        )

    rng = random.Random(17)  # local deterministic RNG for gender picks etc.
    for idx in range(1, bound_count + 1):
        first, last = RESIDENTS_POOL[(idx - 1) % len(RESIDENTS_POOL)]
        email = f"resident{idx}@demo.com"
        user, _ = _ensure_user(email, first, last, password, is_staff=False)
        unit = bound_units[idx - 1]
        _patch_profile(
            Profile,
            user,
            occupation=Profile.Occupation.TENANT,
            gender=Profile.Gender.FEMALE if rng.random() < 0.5 else Profile.Gender.MALE,
            phone=f"+38050555{idx:04d}",
            city=UA_CITIES[idx % len(UA_CITIES)],
            bio=(
                "Мешканець ЖК. Регулярно користуюся порталом: подаю заявки, "
                "замовляю перепустки для гостей, читаю оголошення."
            ),
            unit=unit,
        )
        result.residents.append(
            SeededUser(email=email, user=user, unit=unit, role="resident"),
        )

    # --- 6. Unbound residents (new1, new2) ----------------------------------
    for idx in (1, 2):
        first, last = RESIDENTS_POOL[-idx]  # last two of pool
        email = f"new{idx}@demo.com"
        user, _ = _ensure_user(email, first, last, password, is_staff=False)
        _patch_profile(
            Profile,
            user,
            occupation=Profile.Occupation.TENANT,
            gender=Profile.Gender.FEMALE if idx == 1 else Profile.Gender.MALE,
            phone=f"+38050666{idx:04d}",
            city=UA_CITIES[idx],
            bio=(
                "Новий мешканець — очікую підтвердження прив'язки квартири "
                "від управителя."
            ),
            # unit intentionally left NULL — demos admin-binds-apartment flow.
        )
        result.unbound_residents.append(
            SeededUser(email=email, user=user, role="new-resident"),
        )

    logger.info(
        "seed_users: dispatchers=%d guards=%d workers=%d residents=%d unbound=%d",
        len(result.dispatchers), len(result.guards), len(result.workers),
        len(result.residents), len(result.unbound_residents),
    )
    return result


# ───────────────────────────── internal helpers ──────────────────────────────


def _dispatcher_email(idx: int) -> str:
    return "dispatcher@demo.com" if idx == 1 else f"dispatcher{idx}@demo.com"


def _guard_email(idx: int) -> str:
    return "guard@demo.com" if idx == 1 else f"guard{idx}@demo.com"


def _worker_email(worker, idx: int) -> str:
    """Produce ``<occupation>[N]@demo.com`` — second painter becomes ``painter2``."""
    # Deterministic dedup: the first user with each occupation gets the plain
    # slug; subsequent ones (we only have a second painter in the pool) are
    # numbered.  Using the overall idx avoids having to track per-occupation
    # counters here.
    if worker.occupation == "painter" and idx > 6:  # second painter sits at index 8
        return f"{worker.occupation}2@demo.com"
    return f"{worker.occupation}@demo.com"


def _already_has_occupation(email: str, workers: list) -> bool:
    """Internal heuristic helper — kept for signature symmetry; not hot path."""
    return any(w.email == email for w in workers)


def _ensure_user(
    email: str,
    first: str,
    last: str,
    password: str,
    *,
    is_staff: bool,
):
    """Idempotent ``get_or_create`` with forced field refresh on rerun.

    Returns ``(user, created)`` — same shape as Django's own helper.
    """
    User = get_user_model()
    username = username_from_name(first, last)
    # Usernames are unique — if an earlier seed assigned the same slug to a
    # different user, append email-hash-ish suffix to disambiguate.
    if User.objects.filter(username=username).exclude(email=email).exists():
        username = f"{username}_{email.split('@')[0]}"

    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": username,
            "first_name": first,
            "last_name": last,
            "is_staff": is_staff,
            "is_active": True,
        },
    )
    # Keep fields in sync on rerun even if user already existed.
    dirty = False
    for attr, value in (
        ("username", username),
        ("first_name", first),
        ("last_name", last),
        ("is_staff", is_staff),
        ("is_active", True),
        ("is_superuser", False),
    ):
        if getattr(user, attr) != value:
            setattr(user, attr, value)
            dirty = True
    user.set_password(password)  # always reset so DEMO_PASSWORD rotations apply
    user.save()
    _ = dirty  # noqa: F841 — intent self-documenting, save() is required for password
    return user, created


def _patch_profile(
    Profile,
    user,
    *,
    occupation: str,
    gender: str,
    phone: str,
    city: str,
    bio: str,
    unit: "Unit | None" = None,
) -> None:
    """Update the auto-created Profile in place.

    Using ``QuerySet.update()`` intentionally skips ``Profile.save()``,
    which recomputes ``reputation`` from ``report_count``.  For seeded data
    we trust ``report_count=0`` / ``reputation=100`` defaults.

    PR-11 removed ``Profile.unit``; the ``unit`` argument now produces a
    primary ``Residency`` instead.  The seed keeps the same call-site
    ergonomics — pass a ``Unit`` and the resident gets it as their
    primary home.
    """
    updates: dict[str, object] = {
        "occupation": occupation,
        "gender": gender,
        "phone_number": phone,
        "country_of_origin": "UA",
        "city_of_origin": city,
        "bio": bio,
    }

    Profile.objects.filter(user=user).update(**updates)

    if unit is not None:
        from apps.apartments.models import Residency, ResidencyRole

        Residency.objects.update_or_create(
            user=user,
            unit=unit,
            defaults={
                "role": ResidencyRole.OWNER,
                "is_primary": True,
            },
        )
        # Demote any other primaries for this user — honour the
        # partial unique invariant explicitly here because
        # ``update_or_create`` does not run model.save().
        Residency.objects.filter(user=user, is_primary=True).exclude(
            unit=unit
        ).update(is_primary=False)
    # After bulk update, touch slug regen if it was never populated (first run).
    # AutoSlugField updates via save(), not update(), so force a refresh if
    # slug is still empty on the freshly-created profile.
    profile = user.profile
    if not profile.slug:
        profile.save(update_fields=[])  # trigger AutoSlugField


def _available_units(building_result, *, skip_unit) -> list:
    """Units that may host rank-and-file residents.

    Excludes the tenant's unit and the pre-declared vacant ones; remaining
    units are returned in a deterministic order (sorted by entrance name
    then numeric unit number) so rerun assignments are stable.
    """
    vacant_keys = set(VACANT_UNIT_DESIGNATIONS)
    ordered: list = []
    for key in sorted(building_result.units_by_key.keys()):
        if key in vacant_keys:
            continue
        unit = building_result.units_by_key[key]
        if unit.pk == skip_unit.pk:
            continue
        ordered.append(unit)
    return ordered
