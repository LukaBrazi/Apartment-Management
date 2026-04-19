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

PR-13 extensions
----------------

* Every primary Residency row carries a ``start_date`` so the UI can
  show "mешканець з квітня 2024".
* A multi-unit owner — ``resident3`` — owns a second (otherwise-vacant)
  unit as a non-primary Residency.  This exercises the product's
  "one user → many units" relationship.
* A TENANT Residency — ``renter@demo.com`` — rents one of the demo
  units from the primary owner.  Rounds out the ResidencyRole choices
  beyond OWNER.
* A historical (turnover) Residency carries ``end_date`` in the past
  so the portal's history view has a row to render.
* A cottage owner — ``cottage@demo.com`` — is bound to the PR-13
  cottage Unit.  Keeps the cottage story end-to-end.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import transaction

from .helpers import (
    BASE_TIME,
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
    from apps.organizations.models import Organization
    from .seed_building import BuildingSeedResult
    from .seed_organization import OrganizationSeedResult

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
    # PR-13 additions — kept optional so callers that only care about
    # the four original pools (seed_issues, seed_posts) continue to
    # work without branching on presence.
    cottage_owner: SeededUser | None = None
    renter: SeededUser | None = None
    multi_unit_owner: SeededUser | None = None

    def all(self) -> list[SeededUser]:
        out: list[SeededUser] = []
        out.extend(self.dispatchers)
        out.extend(self.guards)
        out.extend(self.workers)
        if self.tenant is not None:
            out.append(self.tenant)
        out.extend(self.residents)
        out.extend(self.unbound_residents)
        if self.cottage_owner is not None:
            out.append(self.cottage_owner)
        if self.renter is not None:
            out.append(self.renter)
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
    organization_result: "OrganizationSeedResult | None" = None,
    residents_count: int = 32,
    password: str = DEFAULT_DEMO_PASSWORD,
) -> UsersSeedResult:
    """Create/update all demo users and link them to units where appropriate.

    Parameters
    ----------
    building_result:
        Output of :func:`apps.common.seed.seed_building.seed` — provides the
        Building and Unit handles without a DB round-trip.
    organization_result:
        Output of :func:`apps.common.seed.seed_organization.seed` — every
        seeded user gets an active ``OrganizationMembership`` in this org
        with a role derived from their profile (dispatcher→ADMIN,
        guard/worker→STAFF, resident/tenant/renter/cottage_owner→RESIDENT).
        Strict multi-tenant scoping in views (``get_user_organizations``)
        means users without membership see nothing — the demo would be
        invisible to its own accounts without this wiring. Kept optional
        so per-module unit tests can still stand seed_users up on its own,
        but the orchestrator always threads it through.
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

    organization = (
        organization_result.organization if organization_result else None
    )

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
        _ensure_membership(user, organization, role="admin")
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
        _ensure_membership(user, organization, role="staff")
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
        _ensure_membership(user, organization, role="staff")
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
    _ensure_membership(tenant_user, organization, role="resident")
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
        _ensure_membership(user, organization, role="resident")
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
        _ensure_membership(user, organization, role="resident")
        result.unbound_residents.append(
            SeededUser(email=email, user=user, role="new-resident"),
        )

    # --- 7. PR-13 concept extras ------------------------------------------
    # Multi-unit owner, TENANT Residency, turnover (end_date) demo, cottage
    # owner. Kept in a separate helper so the main loop stays readable and
    # the extras can be unit-tested in isolation.
    _seed_pr13_extras(
        result=result,
        building_result=building_result,
        password=password,
        Profile=Profile,
        organization=organization,
    )

    logger.info(
        "seed_users: dispatchers=%d guards=%d workers=%d residents=%d "
        "unbound=%d cottage_owner=%s renter=%s multi_unit_owner=%s",
        len(result.dispatchers), len(result.guards), len(result.workers),
        len(result.residents), len(result.unbound_residents),
        bool(result.cottage_owner), bool(result.renter),
        bool(result.multi_unit_owner),
    )
    return result


def _seed_pr13_extras(
    *,
    result: UsersSeedResult,
    building_result: "BuildingSeedResult",
    password: str,
    Profile,
    organization: "Organization | None" = None,
) -> None:
    """Seed the concept-alignment users introduced in PR-13.

    Writes four new Residency rows on top of the rank-and-file ones:

    1. ``resident3`` (already seeded) gains a secondary Residency on the
       second vacant apartment — shows "one user → many units".
    2. ``resident5`` (already seeded) gains a historical Residency with
       ``end_date`` in the past on a vacant apartment — shows turnover
       so the portal's history view isn't empty.
    3. ``renter@demo.com`` gets a TENANT-role Residency on the first
       vacant apartment — exercises the ResidencyRole.TENANT branch.
    4. ``cottage@demo.com`` is bound to the cottage Unit as an OWNER
       so the cottage building has at least one resident.
    """
    from apps.apartments.models import Residency, ResidencyRole

    from .helpers import VACANT_UNIT_DESIGNATIONS

    vacant_a = building_result.units_by_key.get(VACANT_UNIT_DESIGNATIONS[0])
    vacant_b = building_result.units_by_key.get(VACANT_UNIT_DESIGNATIONS[1])
    cottage_unit = building_result.cottage_unit

    # ── (1) multi-unit owner: pick the 3rd resident if present ─────────
    multi_source: SeededUser | None = None
    if len(result.residents) >= 3 and vacant_a is not None:
        multi_source = result.residents[2]  # resident3 by construction
        Residency.objects.update_or_create(
            user=multi_source.user,
            unit=vacant_a,
            defaults={
                "role": ResidencyRole.OWNER,
                # Non-primary — multi_source's primary stays on their
                # own apartment. Without this we'd violate the partial
                # unique constraint.
                "is_primary": False,
                "start_date": _residency_start_date(
                    f"{multi_source.email}:secondary"
                ),
            },
        )
        result.multi_unit_owner = multi_source

    # ── (2) turnover demo: resident5 gets a past Residency on vacant_b ──
    if len(result.residents) >= 5 and vacant_b is not None:
        turnover_user = result.residents[4].user
        # End date ~2 years ago; start date ~4 years ago. Values are
        # deterministic via BASE_TIME so reruns converge.
        turnover_end = (BASE_TIME - _dt.timedelta(days=730)).date()
        turnover_start = (BASE_TIME - _dt.timedelta(days=1460)).date()
        Residency.objects.update_or_create(
            user=turnover_user,
            unit=vacant_b,
            defaults={
                "role": ResidencyRole.OWNER,
                "is_primary": False,
                "start_date": turnover_start,
                "end_date": turnover_end,
            },
        )

    # ── (3) TENANT Residency: renter@demo.com on vacant_a ──────────────
    # renter@demo.com can share vacant_a with the multi-unit owner
    # above because Residency is keyed on (user, unit) — two different
    # users co-residing the same unit is legal (roommate scenario).
    if vacant_a is not None:
        renter_user, _ = _ensure_user(
            "renter@demo.com", "Орися", "Наймачка", password, is_staff=False,
        )
        _patch_profile(
            Profile,
            renter_user,
            occupation=Profile.Occupation.TENANT,
            gender=Profile.Gender.FEMALE,
            phone="+380507777001",
            city="Київ",
            bio=(
                "Орендую квартиру у демо-ЖК. Активно користуюся порталом "
                "для заявок на ремонт та замовлення перепусток для гостей."
            ),
            unit=vacant_a,
            residency_role=ResidencyRole.TENANT,
            residency_is_primary=True,
            residency_start_date=(BASE_TIME - _dt.timedelta(days=120)).date(),
        )
        _ensure_membership(renter_user, organization, role="resident")
        result.renter = SeededUser(
            email="renter@demo.com",
            user=renter_user,
            unit=vacant_a,
            role="renter",
        )

    # ── (4) cottage owner ──────────────────────────────────────────────
    if cottage_unit is not None:
        cottage_user, _ = _ensure_user(
            "cottage@demo.com", "Ярослав", "Котеджний", password, is_staff=False,
        )
        _patch_profile(
            Profile,
            cottage_user,
            occupation=Profile.Occupation.TENANT,
            gender=Profile.Gender.MALE,
            phone="+380508888001",
            city="Київ",
            bio=(
                "Мешканець котеджу у демо-ЖК. Показую, що ApartmentOS "
                "однаково підходить для багатоквартирних будинків і для "
                "приватних котеджів."
            ),
            unit=cottage_unit,
            residency_role=ResidencyRole.OWNER,
            residency_is_primary=True,
        )
        _ensure_membership(cottage_user, organization, role="resident")
        result.cottage_owner = SeededUser(
            email="cottage@demo.com",
            user=cottage_user,
            unit=cottage_unit,
            role="cottage-owner",
        )


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


def _ensure_membership(user, organization, *, role: str) -> None:
    """Idempotently grant ``user`` an active membership in ``organization``.

    No-op when ``organization`` is None — keeps per-module unit tests
    that exercise ``seed_users`` without an Organization fixture working.

    On rerun the role is re-asserted (a hand-edit that demoted a
    dispatcher to RESIDENT in admin would otherwise survive forever).
    """
    if organization is None:
        return
    from apps.organizations.models import OrganizationMembership

    OrganizationMembership.objects.update_or_create(
        user=user,
        organization=organization,
        defaults={"role": role, "is_active": True},
    )


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
            # PR-12 safety: all seed-created users MUST carry is_demo=True
            # so the nightly reset filter can match them. Without this,
            # users created after the flag was added would survive
            # reset_demo_scope forever.
            "is_demo": True,
        },
    )
    # Keep fields in sync on rerun even if user already existed. Notably
    # re-assert is_demo so hand-edits that clear the flag don't leak a
    # demo account past the nightly reset.
    dirty = False
    for attr, value in (
        ("username", username),
        ("first_name", first),
        ("last_name", last),
        ("is_staff", is_staff),
        ("is_active", True),
        ("is_superuser", False),
        ("is_demo", True),
    ):
        if getattr(user, attr) != value:
            setattr(user, attr, value)
            dirty = True
    user.set_password(password)  # always reset so DEMO_PASSWORD rotations apply
    user.save()
    _ = dirty  # noqa: F841 — intent self-documenting, save() is required for password
    return user, created


def _residency_start_date(email: str) -> _dt.date:
    """Deterministic, human-looking ``start_date`` for a seeded Residency.

    SHA-1 based so the date is stable across Python processes (unlike
    ``hash()``, which depends on ``PYTHONHASHSEED``).  The [30, 1500]
    day window produces a spread between "moved in last month" and
    "has lived here ~4 years", which matches the tenure mix of a real
    ЖК rather than everyone having started on the same day.
    """
    digest = hashlib.sha1(email.encode("utf-8")).digest()
    days = int.from_bytes(digest[:2], "big") % 1470 + 30
    return (BASE_TIME - _dt.timedelta(days=days)).date()


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
    residency_role: str | None = None,
    residency_is_primary: bool = True,
    residency_start_date: _dt.date | None = None,
    residency_end_date: _dt.date | None = None,
) -> None:
    """Update the auto-created Profile in place.

    Using ``QuerySet.update()`` intentionally skips ``Profile.save()``,
    which recomputes ``reputation`` from ``report_count``.  For seeded data
    we trust ``report_count=0`` / ``reputation=100`` defaults.

    PR-11 removed ``Profile.unit``; the ``unit`` argument now produces a
    primary ``Residency`` instead.  The seed keeps the same call-site
    ergonomics — pass a ``Unit`` and the resident gets it as their
    primary home.

    PR-13 adds explicit Residency knobs:

    * ``residency_role`` defaults to ``OWNER`` — pass ``TENANT`` / ``FAMILY``
      to exercise the other choices.
    * ``residency_is_primary`` defaults to ``True`` — pass ``False`` to
      seed a secondary / historical Residency.
    * ``residency_start_date`` defaults to a deterministic hash-derived
      date (see ``_residency_start_date``).
    * ``residency_end_date`` populates the turnover field (e.g. a past
      Residency that no longer counts for billing).
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

        role = residency_role or ResidencyRole.OWNER
        start_date = residency_start_date or _residency_start_date(user.email)

        Residency.objects.update_or_create(
            user=user,
            unit=unit,
            defaults={
                "role": role,
                "is_primary": residency_is_primary,
                "start_date": start_date,
                "end_date": residency_end_date,
            },
        )
        if residency_is_primary:
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
