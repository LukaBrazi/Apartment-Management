"""Seed demo Issues and Categories — the "flagship" showcase per plan §5.

Output:

* 8 ``Category`` rows (plumbing, electrical, lift, common areas, heating,
  ventilation, facade/roof, yard/parking) with realistic SLA hours.
* 45 ``Issue`` rows distributed exactly per plan §5.1/§5.2:

  * Statuses: 12 reported · 10 accepted · 8 in_progress · 10 done · 5 rejected
  * Priorities: 18 low · 20 medium · 7 high
  * 3 of the (accepted | in_progress) set are ``created_at = BASE_TIME − 14d``
    so ``is_overdue`` flips to True (plan §5.3).

* Assignment rules (plan §5.6):

  * ``in_progress`` and ``done`` — 100 % assigned (by occupation routing).
  * ``accepted`` — 60 % assigned / 40 % awaiting.
  * ``reported`` — ~30 % assigned (proactive).
  * ``rejected`` — 50 % had been assigned at time of rejection.

* View counts (plan §5.4) are modelled by creating a handful of
  ``ContentView`` rows per issue — one per distinct resident — so the
  ``GenericRelation`` returns realistic counts from ``.count()`` queries.

**Signal hygiene.**  ``apps.notifications.signals.cache_issue_old_state``
and ``on_issue_saved`` trigger Celery ``notify_*.delay()`` calls on every
save.  During seeding we disconnect both (and reconnect in a
``finally``) — otherwise ``seed_demo`` enqueues ~45 notification tasks
that fail in a CI environment without a broker.

**Determinism.**  All randomness is drawn from a dedicated
``random.Random(RANDOM_SEED_BASE)`` instance — seeding the module alone
does not perturb the global RNG consumed by users/posts.  Timestamps
are derived from ``BASE_TIME`` so two runs produce identical rows.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .helpers import BASE_TIME  # noqa: F401  — re-exported for tests

if TYPE_CHECKING:  # pragma: no cover
    from apps.issues.models import Category, Issue
    from .seed_building import BuildingSeedResult
    from .seed_users import SeededUser, UsersSeedResult

logger = logging.getLogger(__name__)

# ─────────────────────────────── constants ───────────────────────────────────

# Per-module RNG seed — keeps issue layout stable even if a future seed_users
# change consumes more global random calls.  Mnemonic: "issues" → 105575 ( 👀 ).
ISSUES_RNG_SEED = 105575

# (category_name, SLA hours, default worker occupation for routing).
# Occupations must exist in ``WORKERS`` pool (helpers.py).
CATEGORY_SPECS: tuple[tuple[str, int, str], ...] = (
    ("Сантехніка", 24, "plumber"),
    ("Електрика", 24, "electrician"),
    ("Ліфт", 8, "electrician"),
    ("Загальні приміщення", 72, "mason"),
    ("Опалення та ГВП", 24, "hvac"),
    ("Вентиляція", 72, "hvac"),
    ("Фасад та покрівля", 168, "roofer"),
    ("Двір та паркінг", 120, "mason"),
)


# Per-category issue pool — exactly 45 distinct (title, description) pairs.
# Counts per category: 8 + 7 + 3 + 6 + 5 + 3 + 5 + 8 = 45.
ISSUE_TEMPLATES: dict[str, tuple[tuple[str, str], ...]] = {
    "Сантехніка": (
        ("Протікає кран на кухні",
         "Холодна вода капає з крана цілодобово. Ручка лежить вільно, "
         "не затягується. Підставив відро — збирає за ніч приблизно літр."),
        ("Засмічена каналізація у ванній",
         "Вода в ванні не стікає більше 30 хвилин після купання. "
         "Тросик не допомагає. Сусіди знизу також скаржаться на запах."),
        ("Протікає труба під раковиною",
         "Під кухонною раковиною з'явилась калюжа. Труба з'єднана зі "
         "змішувачем. Замінив прокладку — не допомогло."),
        ("Немає гарячої води третій день",
         "Гаряча вода відсутня з понеділка ранку. Холодна подається "
         "без проблем. Жодного попередження не було."),
        ("Зіпсований змішувач у ванній",
         "Змішувач не перемикає режими — постійно йде холодна. Важіль "
         "крутиться вхолосту."),
        ("Тече унітаз після змиву",
         "Вода тече у бак безперервно, не перекривається поплавком. "
         "Раз на годину шумить — розбуджує вночі."),
        ("Забився сифон раковини",
         "Вода стоїть у раковині, стікає дуже повільно. Запах з труби. "
         "Тросиком не пробивається."),
        ("Низький тиск холодної води",
         "Вже тиждень із крана йде тонкий струмінь. На верхніх поверхах, "
         "за словами сусідів, ситуація краща."),
    ),
    "Електрика": (
        ("Не працює розетка в кухні",
         "Розетка біля холодильника перестала працювати після грози. "
         "Мікрохвильова й холодильник не отримують живлення."),
        ("Перегоріло освітлення на 4 поверсі",
         "Не горять три лампи в коридорі 4-го поверху під'їзду Б. "
         "Ввечері там зовсім темно — небезпечно для мешканців."),
        ("Не спрацьовує домофон на вході",
         "Домофон корпусу А не реагує на натискання кнопок з ранку до вечора. "
         "Ввечері іноді працює. Можливо, перегрів блоку живлення."),
        ("Іскрить розетка у спальні",
         "При підключенні зарядного чути потріскування та запах горілого. "
         "Більше не користуюсь нею до ремонту."),
        ("Миготить світло на сходах",
         "Лампа на майданчику між 2 і 3 поверхом блимає кілька секунд, "
         "потім гасне на 10 хвилин."),
        ("Вимкнулися автомати у щитку",
         "Після ввімкнення пральної машини вибило автомат. Ввімкнути назад "
         "не вдається — одразу вимикається."),
        ("Не працює освітлення у підвалі",
         "Технічний поверх під'їзду А — жодна лампа не горить. "
         "Охорона обходить з ліхтариком."),
    ),
    "Ліфт": (
        ("Ліфт застрягає між поверхами",
         "Ліфт корпусу А зупиняється між 5 і 6 поверхом. Двічі застрягав "
         "з мешканцями. Потрібна термінова перевірка ліфтової компанії."),
        ("Ліфт видає металевий скрип",
         "При русі вгору чути сильний металевий скрегіт між 3-м та 7-м "
         "поверхом. Мешканці бояться користуватися ліфтом."),
        ("Не закриваються двері ліфта",
         "Двері тягнуться до закриття довго, іноді стоять відкритими "
         "по 30 секунд. Кнопка «закрити» не реагує."),
    ),
    "Загальні приміщення": (
        ("Бруд і покинуте сміття у під'їзді",
         "На сходовому майданчику 2 поверху під'їзду А тиждень не "
         "прибирали. Пакети зі сміттям стоять з минулої середи."),
        ("Запах сирості з підвалу",
         "З підвального приміщення корпусу А постійно надходить запах "
         "цвілі. Помітно на першому поверсі. Можливо, підтоплення."),
        ("Зламані поштові скриньки",
         "Шість поштових скриньок у вестибюлі корпусу Б не замикаються "
         "— дверцята відламані. Пошта висипається на підлогу."),
        ("Облуплена штукатурка на сходах",
         "Між 3 і 4 поверхом шматки штукатурки відвалюються від "
         "стіни. Минулого тижня впав шматок розміром з долоню."),
        ("Тріщина у стелі коридору",
         "Тонка тріщина з'явилась у коридорі 1 поверху під'їзду Б. "
         "Розширюється щотижня, видно оголений бетон."),
        ("Зламані перила на сходах",
         "Перила на 5-6 поверсі хитаються, один саморіз випав. "
         "Небезпечно для дітей та літніх мешканців."),
    ),
    "Опалення та ГВП": (
        ("Холодна батарея у спальні",
         "Радіатор у спальні холодний, хоча в решті кімнат опалення "
         "працює нормально. Температура в кімнаті близько 15 °C."),
        ("Повітря у батареї на кухні",
         "Батарея грає нерівномірно, верх холодний, низ теплий. "
         "Чути булькання води всередині."),
        ("Протікає клапан на радіаторі",
         "З-під клапана капає вода — уже кілька крапель на годину. "
         "Підставив лоток, але треба усунути причину."),
        ("Занадто гаряча вода у крані",
         "Температура гарячої води перевищує 70 °C — дитина обпекла "
         "руку. Потрібно перевірити регулятор на ІТП."),
        ("Гул у трубах опалення вночі",
         "Після 23:00 труби гудуть 5-10 хвилин, потім затихають. "
         "Заважає спати дітям."),
    ),
    "Вентиляція": (
        ("Гучна вібрація вентшахти",
         "Вентиляційна шахта на кухні вібрує та видає низький гул, "
         "особливо вночі. Почалося після ремонту на технічному поверсі."),
        ("Зворотна тяга у ванній",
         "З вентиляційного отвору ванної йде запах з інших квартир. "
         "Папірець не притягується, а навпаки відштовхується."),
        ("Засмічена витяжка на кухні",
         "Над плитою тяга майже зникла — за 15 років не чистили. "
         "Дим стоїть усією кухнею."),
    ),
    "Фасад та покрівля": (
        ("Тріщина на фасаді корпусу Б",
         "На рівні 4-5 поверхів із зовнішнього боку корпусу Б з'явилася "
         "горизонтальна тріщина шириною близько 1 см. Зростає від осені."),
        ("Протікання даху після дощу",
         "Після кожного дощу на стелі ванної 5-го поверху з'являються "
         "темні плями та краплі. Шпаклівка вже відшаровується."),
        ("Відпав шматок облицювання",
         "Зі стіни між 2 і 3 поверхом впала плитка — лежала на доріжці. "
         "Поки обгородили конусами."),
        ("Іржа на водостоках",
         "Зовнішні водостоки корпусу А проржавіли — вода стікає не в "
         "трубу, а по стіні. Фасад мокрий."),
        ("Провисла козирок над під'їздом",
         "Козирок під'їзду Б тримається на 2 кріпленнях замість 4. "
         "Після зими просів на 10 см."),
    ),
    "Двір та паркінг": (
        ("Вибоїни на в'їзді до паркінгу",
         "На в'їзді до підземного паркінгу три глибокі вибоїни "
         "після зимових морозів. Дряпали низькі автомобілі."),
        ("Зламалися ворота парковки",
         "Шлагбаум не опускається — стоїть у верхньому положенні. "
         "Машини заїжджають без пропуску."),
        ("Перегорів ліхтар у дворі",
         "Біля дитячого майданчика ліхтар не горить другий тиждень. "
         "Ввечері темно, діти вже не грають."),
        ("Зламана лавка біля під'їзду",
         "Дерев'яна лавка з лівого боку від входу А зламана — дошка "
         "сидіння тріснула. Опори ще цілі."),
        ("Покоцаний бордюр на газоні",
         "Автомобіль в'їхав у бордюр і зрушив плити. Край дороги "
         "без огородження — газон топчуть машини."),
        ("Протікає поливальна система",
         "Біля клумби постійна калюжа — тече зі з'єднання шланга. "
         "Вода стоїть уже три дні."),
        ("Забита зливова решітка",
         "Після дощу біля під'їзду В утворюється озеро до 15 см "
         "глибиною. Решітка заросла гілками та листям."),
        ("Поламаний знак «Стоп»",
         "На перехресті внутрішнього проїзду знак нахилений "
         "і частково закритий кущами. Водії його не бачать."),
    ),
}

# Flattened pool order — defines the issue index ↔ natural key mapping.
# Iteration order of dicts is guaranteed since Python 3.7, so rebuilding this
# list on every call is deterministic.
def _flatten_templates() -> list[tuple[str, str, str]]:
    """Return ``[(category_name, title, description), ...]`` in stable order."""
    rows: list[tuple[str, str, str]] = []
    for cat_name, entries in ISSUE_TEMPLATES.items():
        for title, desc in entries:
            rows.append((cat_name, title, desc))
    return rows


# Status distribution per plan §5.1 — order matters (first 12 are reported, etc).
STATUS_COUNTS: tuple[tuple[str, int], ...] = (
    ("reported", 12),
    ("accepted", 10),
    ("in_progress", 8),
    ("done", 10),
    ("rejected", 5),
)


# Priority distribution per plan §5.2 — interleaved across the status buckets
# via a fixed shuffle so distribution is even (not all "high" landing on
# ``rejected`` issues, for example).
PRIORITY_COUNTS: tuple[tuple[str, int], ...] = (
    ("low", 18),
    ("medium", 20),
    ("high", 7),
)


# ─────────────────────────────── dataclasses ─────────────────────────────────


@dataclass
class IssuesSeedResult:
    """Orchestrator handle — used by seed_ratings, seed_posts, and tests."""

    categories: dict[str, "Category"] = field(default_factory=dict, repr=False)
    issues: list["Issue"] = field(default_factory=list, repr=False)

    created_categories: int = 0
    created_issues: int = 0
    updated_issues: int = 0

    # Counters for tests/orchestrator sanity-checking.
    reported: int = 0
    accepted: int = 0
    in_progress: int = 0
    done: int = 0
    rejected: int = 0
    overdue: int = 0
    high_priority: int = 0
    assigned: int = 0

    def status_counts(self) -> dict[str, int]:
        return {
            "reported": self.reported,
            "accepted": self.accepted,
            "in_progress": self.in_progress,
            "done": self.done,
            "rejected": self.rejected,
        }


# ─────────────────────────────── public entry ───────────────────────────────


def seed(
    *,
    users_result: "UsersSeedResult",
    building_result: "BuildingSeedResult",
    count: int = 45,
) -> IssuesSeedResult:
    """Create/refresh Categories + Issues per plan §5.

    Parameters
    ----------
    users_result:
        Output of :func:`seed_users.seed` — we need residents (reporters) and
        workers-by-occupation (assignees).
    building_result:
        Output of :func:`seed_building.seed` — used to validate that every
        reporter's apartment still lives under the demo Building.
    count:
        Total issues.  Default 45 (plan); tests may pass a smaller value to
        keep fixture DB lightweight.  ``count`` is clamped to the size of the
        flattened template pool.

    Returns
    -------
    IssuesSeedResult
        Category + Issue handles plus per-bucket counts (used by safety tests).
    """
    from apps.issues.models import Category, Issue

    # ── 0. Pre-flight: seed categories and resolve RNG --------------------
    result = IssuesSeedResult()
    result.categories = _upsert_categories(Category, result)

    flattened = _flatten_templates()
    total_available = len(flattened)
    if count > total_available:
        logger.warning(
            "seed_issues: count=%d capped to template pool size %d",
            count, total_available,
        )
        count = total_available
    if count < 5:
        raise ValueError("count must be ≥ 5 (need one issue per status bucket)")

    # Scale status/priority counts proportionally when count<45 (keeps
    # distribution recognisable for CI smoke runs).
    statuses = _distribute(STATUS_COUNTS, count)
    priorities = _distribute(PRIORITY_COUNTS, count)

    rng = random.Random(ISSUES_RNG_SEED)
    priorities_shuffled = priorities[:]
    rng.shuffle(priorities_shuffled)

    reporters = _reporter_pool(users_result)
    if not reporters:
        raise RuntimeError("seed_issues: no residents with apartments — seed users first")

    workers_by_occ = users_result.workers_by_occupation()

    # ── 1. Build issues in a signals-suspended block ----------------------
    with _issue_signals_suspended():
        with transaction.atomic():
            for idx in range(count):
                cat_name, title, description = flattened[idx]
                status = statuses[idx]
                priority = priorities_shuffled[idx]

                category = result.categories[cat_name]
                reporter = reporters[idx % len(reporters)]

                assignee = _choose_assignee(
                    status=status,
                    category_name=cat_name,
                    workers_by_occ=workers_by_occ,
                    idx=idx,
                )

                # Overdue spec (plan §5.3): 3 × (accepted | in_progress)
                # created 14d before BASE_TIME.  Pick deterministic indices
                # so rerun is stable.
                is_overdue = (
                    status in ("accepted", "in_progress")
                    and idx in _OVERDUE_INDICES
                )

                created_at, due_at, resolved_on = _timeline_for(
                    status=status,
                    sla_hours=category.sla_hours,
                    is_overdue=is_overdue,
                    idx=idx,
                )

                natural_key = {"title": title, "reported_by": reporter.user}
                defaults = {
                    # PR-5: no more legacy Apartment mirror; Issue.unit
                    # is the canonical link post-PR-2 dual-read cutover.
                    "unit": reporter.unit,
                    "category": category,
                    "description": description,
                    "status": status,
                    "priority": priority,
                    "due_at": due_at,
                    "resolved_on": resolved_on,
                    "assigned_to": (assignee.user if assignee else None),
                }

                issue, created = Issue.objects.get_or_create(
                    **natural_key, defaults=defaults,
                )

                if created:
                    # ``created_at`` is ``auto_now_add`` — it ignored the value
                    # we passed via ``defaults``.  Stomp it with a queryset
                    # update so the plan timeline (§5.7) holds.
                    Issue.objects.filter(pk=issue.pk).update(created_at=created_at)
                    result.created_issues += 1
                # On rerun (``not created``): intentionally leave the row
                # alone.  Timestamps drift with ``timezone.now()`` across
                # runs and we don't want to flap ``updated_at`` daily.
                # Callers who need to reshape the demo must run with
                # ``--reset`` first (plan §10).

                result.issues.append(issue)

                # Bookkeeping for the report dataclass.
                setattr(result, status, getattr(result, status) + 1)
                if is_overdue:
                    result.overdue += 1
                if priority == "high":
                    result.high_priority += 1
                if assignee is not None:
                    result.assigned += 1

            # ── 2. ContentView rows — low fidelity but feature-visible ────
            _seed_content_views(result.issues, users_result, rng)

    logger.info(
        "seed_issues: categories=%d created=%d updated=%d "
        "by_status=%s overdue=%d high=%d assigned=%d",
        len(result.categories), result.created_issues, result.updated_issues,
        result.status_counts(), result.overdue, result.high_priority,
        result.assigned,
    )
    return result


# ────────────────────────── internal helpers ────────────────────────────────


# Deterministic indices in the (accepted | in_progress) bucket — the first
# accepted (idx 12) + first two in_progress (idx 22, 23) land 14 days in the
# past.  Rerun-stable as long as STATUS_COUNTS doesn't shift.
_OVERDUE_INDICES = frozenset({12, 22, 23})


def _distribute(counts_spec: tuple[tuple[str, int], ...], total: int) -> list[str]:
    """Expand ``((label, n), ...)`` into ``[label, label, ..., label2, ...]``.

    If ``total`` is smaller than the sum, we scale each bucket proportionally
    and distribute the remainder to the largest buckets first.  Keeps the
    plan distribution recognisable under CI smoke overrides.
    """
    plan_total = sum(n for _, n in counts_spec)
    if total == plan_total:
        out: list[str] = []
        for label, n in counts_spec:
            out.extend([label] * n)
        return out

    # Proportional scaling.
    scaled: list[tuple[str, int]] = []
    remainder = total
    for label, n in counts_spec:
        take = max(1, int(round(n * total / plan_total)))
        take = min(take, remainder)
        scaled.append((label, take))
        remainder -= take
    # Stuff any leftover into the biggest bucket (keeps deterministic order).
    if remainder > 0:
        biggest_idx = max(range(len(scaled)), key=lambda i: scaled[i][1])
        label, n = scaled[biggest_idx]
        scaled[biggest_idx] = (label, n + remainder)

    out = []
    for label, n in scaled:
        out.extend([label] * n)
    return out


def _upsert_categories(Category, result: IssuesSeedResult) -> dict[str, "Category"]:
    """Idempotent create/update for the 8 demo categories."""
    cat_map: dict[str, "Category"] = {}
    for name, sla, _occupation in CATEGORY_SPECS:
        cat, created = Category.objects.get_or_create(
            name=name,
            defaults={"sla_hours": sla},
        )
        # Defensive: if SLA drifted, re-align to plan.
        if cat.sla_hours != sla:
            cat.sla_hours = sla
            cat.save(update_fields=["sla_hours"])
        if created:
            result.created_categories += 1
        cat_map[name] = cat
    return cat_map


def _reporter_pool(users_result: "UsersSeedResult") -> list["SeededUser"]:
    """Residents + tenant who have an apartment bound — valid reporters."""
    pool: list["SeededUser"] = []
    if users_result.tenant is not None and users_result.tenant.unit is not None:
        pool.append(users_result.tenant)
    for r in users_result.residents:
        if r.unit is not None:
            pool.append(r)
    return pool


def _choose_assignee(
    *,
    status: str,
    category_name: str,
    workers_by_occ: dict[str, list["SeededUser"]],
    idx: int,
) -> "SeededUser | None":
    """Route to a worker by category → occupation, respecting plan §5.6 ratios.

    Assignment probability by status:
        in_progress, done → 100 %
        accepted          → 60 %  (idx % 5 < 3)
        reported          → 30 %  (idx % 10 < 3)
        rejected          → 50 %  (idx % 2 == 0)

    The modulo pattern is deliberate — it's deterministic across reruns and
    gives an even spread rather than streaks.
    """
    category_to_occ = {
        name: occ for name, _sla, occ in CATEGORY_SPECS
    }

    assign = False
    if status in ("in_progress", "done"):
        assign = True
    elif status == "accepted":
        assign = (idx % 5) < 3
    elif status == "reported":
        assign = (idx % 10) < 3
    elif status == "rejected":
        assign = (idx % 2) == 0

    if not assign:
        return None

    occupation = category_to_occ.get(category_name)
    pool = workers_by_occ.get(occupation, [])
    if not pool:
        # Fall back to any worker — ensures we honour the ratio even when
        # the preferred occupation isn't seeded (thinner CI runs).
        for occ_workers in workers_by_occ.values():
            if occ_workers:
                pool = occ_workers
                break
    if not pool:
        return None
    return pool[idx % len(pool)]


def _timeline_for(
    *,
    status: str,
    sla_hours: int,
    is_overdue: bool,
    idx: int,
) -> tuple["object", "object | None", "object | None"]:
    """Return ``(created_at, due_at, resolved_on)`` tuple per plan §5.7.

    Timeline anchoring is **status-aware** to keep ``is_overdue`` semantics
    aligned with the plan:

    * ``is_overdue == True`` (plan §5.3, 3 rows): anchor 14 days before
      ``timezone.now()`` so ``due_at`` has provably passed.
    * Active states (``reported`` / ``accepted`` / ``in_progress`` not flagged
      overdue): anchor close to ``now`` so ``due_at = now + near-SLA`` stays
      in the future — these must NOT show an "overdue" badge.
    * Terminal states (``done`` / ``rejected``): spread across 1..30 days
      before ``now`` for visual variety; ``is_overdue`` returns False for
      DONE by definition, and rejected issues are filtered out of the
      overdue list in every UI surface.

    Why ``timezone.now()`` instead of ``BASE_TIME``?  The plan stamped
    ``BASE_TIME = 2026-04-01`` as an idempotency anchor, but the ``is_overdue``
    property reads the live clock — anchoring ``due_at`` to a fixed past
    moment flags every active issue as overdue once the wall-clock has
    advanced past it.  Two reruns on the same day still produce identical
    rows; across days there's ~24h drift, which plan §11 tolerates.
    """
    now = timezone.now()

    if is_overdue:
        age = timedelta(days=14, hours=(idx % 12))
        created_at = now - age
    elif status in ("done", "rejected"):
        # Terminal — spread across 1..30 days for variety.
        age_days = 1 + (idx * 7) % 30
        created_at = now - timedelta(days=age_days, hours=(idx % 12))
    else:
        # Active, non-overdue: keep recent so due_at stays future.
        # Cap age so age * 1h < SLA − 1h (ensures due_at > now).
        max_age_hours = max(1, sla_hours - 2)
        age_hours = 1 + (idx % max_age_hours)
        created_at = now - timedelta(hours=age_hours)

    due_at = created_at + timedelta(hours=sla_hours)

    resolved_on = None
    if status == "done":
        resolved_on = (created_at + timedelta(days=1 + (idx % 7))).date()
    elif status == "rejected":
        # Rejected issues also carry ``resolved_on`` — it marks when the
        # admin closed them out.  Exercises the UI "closed" section.
        resolved_on = (created_at + timedelta(days=1 + (idx % 3))).date()

    return created_at, due_at, resolved_on


def _seed_content_views(
    issues: list["Issue"],
    users_result: "UsersSeedResult",
    rng: random.Random,
) -> None:
    """Create ``ContentView`` rows so ``issue.content_views.count()`` is realistic.

    Per plan §5.4:

    * ``reported``   → 1–3 views
    * ``accepted``   → 3–8 views
    * ``in_progress``→ 6–15 views
    * ``done``       → 10–20 views
    * ``rejected``   → 2–6 views

    Bounded by residents pool size to respect ``unique_together``
    (content_type, object_id, user, viewer_ip).
    """
    from apps.common.models import ContentView
    from apps.issues.models import Issue

    issue_ct = ContentType.objects.get_for_model(Issue)

    viewers = [r for r in users_result.residents if r.user is not None]
    if users_result.tenant:
        viewers.append(users_result.tenant)

    if not viewers:  # pragma: no cover — impossible after seed_users
        return

    ranges = {
        "reported": (1, 3),
        "accepted": (3, 8),
        "in_progress": (6, 15),
        "done": (10, 20),
        "rejected": (2, 6),
    }

    rows_to_insert: list[ContentView] = []
    for issue in issues:
        lo, hi = ranges.get(issue.status, (1, 3))
        target = rng.randint(lo, hi)
        target = min(target, len(viewers))
        # Start offset varies per issue so views don't cluster on the same users.
        start = (issue.pk.int if hasattr(issue.pk, "int") else hash(issue.pk)) % len(viewers)
        for i in range(target):
            viewer = viewers[(start + i) % len(viewers)]
            rows_to_insert.append(
                ContentView(
                    content_type=issue_ct,
                    object_id=issue.pk,
                    user=viewer.user,
                    viewer_ip="10.0.0.1",  # fixed fake IP — keeps unique_together happy
                )
            )

    # bulk_create with ignore_conflicts — rerun tolerance.
    ContentView.objects.bulk_create(rows_to_insert, ignore_conflicts=True)


# ──────────────────────── signal disconnect/reconnect ───────────────────────


class _issue_signals_suspended:
    """Context manager — disconnects Issue pre/post_save handlers.

    ``apps.notifications.signals`` dispatches Celery tasks on every Issue
    save.  During seeding we want a quiet DB write — no broker interaction.
    """

    def __enter__(self):
        from apps.issues.models import Issue
        from apps.notifications.signals import (
            cache_issue_old_state,
            on_issue_saved,
        )
        from django.db.models.signals import post_save, pre_save

        self._pre = (pre_save, cache_issue_old_state, Issue)
        self._post = (post_save, on_issue_saved, Issue)

        pre_save.disconnect(cache_issue_old_state, sender=Issue)
        post_save.disconnect(on_issue_saved, sender=Issue)
        return self

    def __exit__(self, exc_type, exc, tb):
        pre_signal, pre_receiver, pre_sender = self._pre
        post_signal, post_receiver, post_sender = self._post
        pre_signal.connect(pre_receiver, sender=pre_sender, weak=False)
        post_signal.connect(post_receiver, sender=post_sender, weak=False)
        return False
