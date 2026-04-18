"""Shared constants, determinism helpers and Ukrainian name pools for seed_demo.

Everything that multiple ``_seed_*`` modules need lives here so the individual
modules stay narrow and the constants (demo scope markers, base timestamp,
random seed) are defined in exactly one place.

Per ``docs/DEMO_SEED_PLAN.md`` §13 and §11:

* ``DEMO_EMAIL_DOMAIN`` and ``DEMO_BUILDING_NAME`` are **code constants,
  never read from env** — they are the reset filter and must be immutable
  across deploys.
* ``RANDOM_SEED`` + ``Faker.seed`` + fixed ``BASE_TIME`` guarantee that two
  successive ``seed_demo`` runs (without ``--reset``) converge to the same
  state — the idempotency contract.
"""
from __future__ import annotations

import hashlib
import random
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from zoneinfo import ZoneInfo

from faker import Faker

# ───────────────────────────────── constants ──────────────────────────────────

# Scope markers — these are the two strings that define "this is demo data".
# NEVER read from env: env overrides are the attack surface that lets a misconfigured
# pod wipe production.  Renaming either constant requires updating the pin tests in
# ``apps/tests/test_reset_demo_scope.py``.
DEMO_EMAIL_DOMAIN = "@demo.com"
DEMO_BUILDING_NAME = "Зелений Квартал — Демо"

# Kyiv timezone — product and clients live in UA, all timestamps must make sense
# to a person reading the admin at 09:00 Kyiv.
KYIV = ZoneInfo("Europe/Kyiv")

# Fixed reference point — every created_at / due_at is computed as an offset from
# this anchor.  Changing this constant is a breaking change for idempotency tests.
BASE_TIME = datetime(2026, 4, 1, 9, 0, tzinfo=KYIV)

# Seed for every ``random`` / ``Faker`` call in the seed package.  Keep as ``42``
# unless you really mean to regenerate all demo fixtures from scratch.
RANDOM_SEED = 42

# Default password for locally seeded users.  Production seeding MUST pass
# ``--passwords-from-env`` which overrides this with ``$DEMO_PASSWORD``.
DEFAULT_DEMO_PASSWORD = "Demo1234!"  # noqa: S105 — documented default for dev

# Building layout — 1 building, 3 entrances, 48 units per plan §3.
# Entrance "В" is intentionally empty (0 units) as a showcase of the data model.
# Layout picks 4 floors × 6 units/floor so that plan's canonical "А-105" /
# "А-207" / "Б-308" designations have a natural home (slot-5 on floor 1, etc.).
ENTRANCE_NAMES: tuple[str, ...] = ("А", "Б", "В")
POPULATED_ENTRANCES: tuple[str, ...] = ("А", "Б")
FLOORS_PER_ENTRANCE = 4
UNITS_PER_FLOOR = 6  # → 24 units × 2 populated entrances = 48 total

# Stable unit designators handed to the tenant and vacant-apartment demos.
TENANT_UNIT_ENTRANCE = "А"
TENANT_UNIT_NUMBER = "105"  # floor 1, slot 5 — kept stable across reruns
VACANT_UNIT_DESIGNATIONS: tuple[tuple[str, str], ...] = (
    ("А", "203"),  # floor 2, slot 3 — unassigned (admin binds-apt demo)
    ("Б", "402"),  # floor 4, slot 2 — unassigned
)


def unit_number_for(floor: int, slot: int) -> str:
    """Return the canonical Ukrainian unit number string.

    ``floor`` is 1-indexed; ``slot`` is the 1-indexed position on the floor.
    Produces ``"101"`` for ``(1, 1)``, ``"406"`` for ``(4, 6)``.
    """
    return f"{floor}{slot:02d}"


# ───────────────────────────── determinism helpers ────────────────────────────


def init_random() -> Faker:
    """Seed ``random`` + ``Faker`` and return a Ukrainian Faker instance.

    Call this exactly once at the top of ``handle()`` before invoking any
    seed module.  Returning the Faker keeps the import surface small — modules
    that need more exotic locales can still instantiate their own.
    """
    random.seed(RANDOM_SEED)
    Faker.seed(RANDOM_SEED)
    return Faker("uk_UA")


def det_uuid(namespace: str, natural_key: str) -> uuid.UUID:
    """Return a deterministic UUID for a (namespace, natural_key) pair.

    Used where we want stable primary keys across reruns (e.g. deterministic
    Issue IDs for tests) without touching the DB.  SHA-1 is fine here — this
    is not a security context.
    """
    digest = hashlib.sha1(f"{namespace}:{natural_key}".encode()).digest()[:16]
    # Force UUID version 5 bits so repr is well-formed.
    return uuid.UUID(bytes=digest, version=5)


def ua_car_plate(rng: random.Random | None = None) -> str:
    """Generate a Ukrainian-format license plate using Cyrillic look-alikes.

    Example output: ``"АВ1234КК"``.  Kyiv drivers recognize this as the real
    format (the letters are actually Cyrillic but visually identical to Latin
    ones allowed on the plate).
    """
    r = rng or random
    letters = "АВЕКМНОРСТУХ"
    prefix = "".join(r.choices(letters, k=2))
    digits = f"{r.randint(1000, 9999)}"
    suffix = "".join(r.choices(letters, k=2))
    return f"{prefix}{digits}{suffix}"


def dicebear_avatar_url(seed: str) -> str:
    """Return a stable DiceBear avatar URL for ``seed`` (usually user email).

    Using ``initials`` style because it degrades gracefully if the service is
    ever unreachable — you still get readable two-letter fallback.
    """
    return (
        f"https://api.dicebear.com/7.x/initials/svg?"
        f"seed={seed}&backgroundColor=1e88e5,43a047,fb8c00"
    )


# ───────────────────────────────── name pools ─────────────────────────────────
#
# Faker uk_UA gives sensible random names but the director, guards and workers
# are the accounts we hand to real customers — those deserve names that read
# like well-chosen characters rather than ``Faker-generated-noise``.
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NamedOccupation:
    """First name / last name / Profile.Occupation value triple."""

    first: str
    last: str
    occupation: str


DISPATCHERS: tuple[tuple[str, str], ...] = (
    ("Тетяна", "Романенко"),
    ("Олег", "Степаненко"),
)

GUARDS: tuple[tuple[str, str], ...] = (
    ("Микола", "Гвоздюк"),
    ("Андрій", "Лук'яненко"),
    ("Петро", "Савчук"),
)

# ``occupation`` values here MUST match ``Profile.Occupation`` choices in
# ``apps/profiles/models.py`` — validated by the seed safety test.
WORKERS: tuple[NamedOccupation, ...] = (
    NamedOccupation("Василь", "Мельник", "plumber"),
    NamedOccupation("Ігор", "Кравченко", "electrician"),
    NamedOccupation("Степан", "Бойко", "carpenter"),
    NamedOccupation("Петро", "Коваленко", "mason"),
    NamedOccupation("Сергій", "Павленко", "roofer"),
    NamedOccupation("Марія", "Іваницька", "painter"),
    NamedOccupation("Валерій", "Середа", "hvac"),
    NamedOccupation("Наталія", "Борисюк", "painter"),
)

# Resident name pool — expanded up to 35 to cover residents 1..22 plus the two
# ``new*@demo.com`` "no-apartment" demos, plus buffer for ``--residents-count``.
RESIDENTS_POOL: tuple[tuple[str, str], ...] = (
    ("Іван", "Петренко"),
    ("Марія", "Шевченко"),
    ("Андрій", "Бондаренко"),
    ("Олена", "Мельничук"),
    ("Дмитро", "Коваленко"),
    ("Наталія", "Литвиненко"),
    ("Олексій", "Мороз"),
    ("Тетяна", "Савченко"),
    ("Юрій", "Гончаренко"),
    ("Анна", "Кравчук"),
    ("Михайло", "Руденко"),
    ("Оксана", "Ткаченко"),
    ("Віктор", "Полтавець"),
    ("Катерина", "Марченко"),
    ("Богдан", "Сидоренко"),
    ("Ірина", "Василенко"),
    ("Роман", "Карпенко"),
    ("Світлана", "Гриценко"),
    ("Назар", "Яковенко"),
    ("Лідія", "Захарченко"),
    ("Артем", "Костенко"),
    ("Вікторія", "Лисенко"),
    ("Олена", "Нова"),
    ("Роман", "Підполковник"),
    ("Софія", "Островська"),
    ("Тарас", "Загорний"),
    ("Юлія", "Нестеренко"),
    ("Павло", "Білозерський"),
    ("Зоряна", "Волощук"),
    ("Іларія", "Тимошенко"),
    ("Мирослав", "Чередник"),
    ("Галина", "Ярошенко"),
    ("Назарій", "Підгірний"),
    ("Христина", "Давидюк"),
    ("Віталій", "Стельмах"),
)

UA_CITIES: tuple[str, ...] = (
    "Київ",
    "Львів",
    "Одеса",
    "Харків",
    "Дніпро",
    "Чернігів",
    "Полтава",
    "Вінниця",
    "Житомир",
    "Тернопіль",
)


# ─────────────────────────────── transliteration ──────────────────────────────


_UA_TO_LATIN = {
    "А": "a", "Б": "b", "В": "v", "Г": "h", "Ґ": "g", "Д": "d", "Е": "e",
    "Є": "ie", "Ж": "zh", "З": "z", "И": "y", "І": "i", "Ї": "i", "Й": "i",
    "К": "k", "Л": "l", "М": "m", "Н": "n", "О": "o", "П": "p", "Р": "r",
    "С": "s", "Т": "t", "У": "u", "Ф": "f", "Х": "kh", "Ц": "ts", "Ч": "ch",
    "Ш": "sh", "Щ": "shch", "Ь": "", "Ю": "iu", "Я": "ia", "'": "",
}


def translit(text: str) -> str:
    """Cheap Ukrainian → Latin transliteration for username slugs.

    Not a standards-compliant implementation — just enough to produce
    ``"Іван Петренко"`` → ``"ivan_petrenko"`` style usernames that are
    compatible with Django's ``UsernameValidator`` (ASCII letters + underscore).
    """
    out: list[str] = []
    for ch in text:
        upper = ch.upper()
        if upper in _UA_TO_LATIN:
            mapped = _UA_TO_LATIN[upper]
            # Preserve case of the first-letter-of-a-word-ish positions.
            if ch.isupper() and mapped:
                mapped = mapped[0].upper() + mapped[1:]
            out.append(mapped)
        elif ch.isascii():
            out.append(ch)
        else:
            # Anything else (stray punctuation) we drop.
            continue
    return "".join(out).lower()


def username_from_name(first: str, last: str) -> str:
    """Build a deterministic, validator-safe username from Ukrainian first+last."""
    return f"{translit(first)}_{translit(last)}"


# ──────────────────────────── test‑only surface API ───────────────────────────


def all_pool_surfaces() -> Iterable[tuple[str, int]]:
    """Return ``(pool_name, size)`` tuples — used by pin tests to detect drift."""
    return (
        ("DISPATCHERS", len(DISPATCHERS)),
        ("GUARDS", len(GUARDS)),
        ("WORKERS", len(WORKERS)),
        ("RESIDENTS_POOL", len(RESIDENTS_POOL)),
        ("UA_CITIES", len(UA_CITIES)),
    )
