"""Seed demo News feed — categories, articles and generated cover images.

Problem this solves
-------------------
A tenant logging into the demo ЖК historically saw an empty ``/news``
page because no News rows ever existed in the seed. The rest of the
dataset (Posts, Announcements, Issues, Passes, …) was populated, but
the News feed stayed blank. ``NewsListAPIView`` filters by the user's
organization (or ``organization IS NULL`` for platform-wide news), so
even an admin-created News entry with the wrong org would be
invisible to residents. This module fixes that end-to-end.

What gets seeded
----------------
* **5 NewsCategory rows** — ``Оголошення``, ``Сервіс``, ``Події``,
  ``Ремонт``, ``Безпека``. Each with its own accent colour so the
  badge pill on the news card is visually distinct. Idempotent via
  ``get_or_create(name=...)``.
* **10 News articles** —
    - 3 platform-wide (``organization=NULL``) so every demo tenant,
      regardless of org, sees product-level news.
    - 7 scoped to the demo Organization so tenant@demo.com sees them
      alongside the platform-wide ones.
    - 2 of them ``pinned=True`` (one global, one org-scoped) to test
      the "-pinned, -published_at" ordering in the list view.
    - Bodies are 4 short Ukrainian paragraphs; excerpts are 1-2
      sentences that the card shows.
* **Cover images** generated on the fly via Pillow — a 960×480 PNG
  gradient tinted with the category colour. Saved to the model's
  ``ImageField`` via ``ContentFile`` so the serializer's
  ``cover_image`` URL resolves normally. No network dependency, no
  committed image assets — the seed ships with Pillow as a runtime
  dep already (``requirements/base.txt``).

Idempotency
-----------
Natural key on News is ``title`` (titles are unique by design in the
spec table below).  A rerun without ``--reset`` skips existing rows;
``created_at`` is stomped via a queryset update on first insert so
the "days ago" spacing stays realistic.

Determinism
-----------
Category colour → image gradient is derived purely from the hex
string, so the same seed input produces the same image bytes on every
run. This keeps the idempotency contract (rerun = no diff) intact.

Reset scope
-----------
``apps.common.seed.reset_scope`` identifies demo News rows by
``author_id IN demo_users`` OR ``organization_id IN demo_orgs``. The
``Organization`` FK on News is ``SET_NULL``, so we delete News
*before* the demo Organization to prevent org-scoped news from
leaking out as pseudo-global rows at reset time. Categories are
shared infrastructure (like tags) — we don't delete them.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from io import BytesIO
from typing import TYPE_CHECKING

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:  # pragma: no cover
    from apps.news.models import News, NewsCategory
    from .seed_organization import OrganizationSeedResult
    from .seed_users import UsersSeedResult

logger = logging.getLogger(__name__)


# ──────────────────────────── data pools ────────────────────────────────────


# 5 categories with Tailwind-family accent colours — matches the pill
# styling in ``client/src/app/(estate)/news/page.tsx`` that reads
# ``item.category.color`` directly.
CATEGORY_SPECS: tuple[tuple[str, str], ...] = (
    ("Оголошення", "#2F6FED"),  # blue-600
    ("Сервіс",      "#10B981"),  # emerald-500
    ("Події",       "#F59E0B"),  # amber-500
    ("Ремонт",      "#EF4444"),  # red-500
    ("Безпека",     "#8B5CF6"),  # violet-500
)


# News spec entries:
#   (title, category_name, excerpt, body, pinned, org_scoped, days_ago)
#
# ``org_scoped=True``  → news.organization = demo org, tenant sees it only
#                         if they're in the demo org (they are).
# ``org_scoped=False`` → news.organization = NULL, visible to every
#                         authenticated user (platform-wide news).
NEWS_SPECS: tuple[tuple[str, str, str, str, bool, bool, int], ...] = (
    # ── Pinned, platform-wide ───────────────────────────────────────────
    (
        "Запущено мобільний кабінет ApartmentOS",
        "Оголошення",
        "Ми повністю переробили головний екран під смартфон. "
        "Швидкі дії, картки заявок і новини — тепер під великим пальцем.",
        "Шановні мешканці!\n\n"
        "Сьогодні ми розгорнули оновлення, яке повністю переосмислює "
        "роботу з кабінетом на телефоні. Тепер головний екран показує "
        "ваші активні заявки, свіжі оголошення та швидкі дії одним "
        "дотиком — без нескінченного прокручування.\n\n"
        "Що нового: мобільно-оптимізовані сторінки заявок, перепусток "
        "і профілю; темна тема, що автоматично підхоплюється від "
        "системи; великі тапабельні кнопки замість дрібних іконок.\n\n"
        "Якщо щось працює не так, як раніше — дайте знати диспетчеру. "
        "Ми оновлюємо портал щотижня і реагуємо на ваш фідбек.",
        True,  # pinned
        False,  # platform-wide
        1,
    ),
    # ── Pinned, org-scoped ──────────────────────────────────────────────
    (
        "Планове відключення гарячої води 25–26 квітня",
        "Сервіс",
        "Гідравлічні випробування магістралі: з 08:00 25.04 до 20:00 26.04. "
        "Холодна вода та опалення — без змін.",
        "Шановні мешканці!\n\n"
        "Інформуємо про планові гідравлічні випробування магістралі "
        "гарячого водопостачання ЖК «Зелений Квартал». Подача гарячої "
        "води буде зупинена з 08:00 25 квітня до 20:00 26 квітня.\n\n"
        "Упродовж цього часу в кранах може спостерігатися підвищений "
        "тиск або рідкі сплески тиску у стояках — це нормально, "
        "такий спосіб дозволяє виявити слабкі місця у трубах.\n\n"
        "Холодна вода та опалення працюватимуть у звичайному режимі. "
        "Просимо завчасно запастися теплою водою для побутових "
        "потреб. Дякуємо за розуміння.",
        True,  # pinned
        True,  # org-scoped
        2,
    ),
    # ── Regular platform-wide ───────────────────────────────────────────
    (
        "Нова роль «Охоронець» — інструкція для ЖК",
        "Оголошення",
        "Тепер керуючі компанії можуть створювати акаунти охоронців "
        "із власним порталом для обробки перепусток.",
        "Ми додали окрему роль «Охоронець» для керуючих компаній, "
        "у яких черговий персонал на КПП працює з перепустками.\n\n"
        "У порталі охоронця є спрощений список активних перепусток на "
        "сьогодні, кнопка «Позначити як проїхав» та фільтр по номеру "
        "авто. Нічого зайвого — щоб оператор не витрачав час на меню.\n\n"
        "Додати охоронця можна в розділі «Адміністрація» → «Працівники». "
        "Пароль за замовчуванням надсилається на електронну пошту.\n\n"
        "Детальна інструкція — у центрі підтримки на apartmentos.org.",
        False,
        False,
        5,
    ),
    (
        "Оновлення порталу: 14-денна сесія «Запам'ятати мене»",
        "Оголошення",
        "На сторінці входу з'явилася опція, яка дозволяє не "
        "логінитись знову 14 днів.",
        "У формі логіна з'явилася галочка «Запам'ятати мене на 14 "
        "днів». Якщо її поставити, ваш сеанс зберігатиметься навіть "
        "після закриття браузера протягом двох тижнів.\n\n"
        "За замовчуванням опція вимкнена — це безпечніше для спільних "
        "комп'ютерів і публічних кіосків. Рекомендуємо вмикати її "
        "тільки на власних пристроях.\n\n"
        "Вийти з акаунта можна у будь-який момент через меню "
        "«Профіль» → «Вийти» — це негайно завершить сесію, незалежно "
        "від того, поставили ви галочку чи ні.",
        False,
        False,
        7,
    ),
    (
        "Як працює рейтинг підрядників у ApartmentOS",
        "Події",
        "Мешканці можуть оцінювати роботу сантехніків, електриків та "
        "інших спеціалістів після закриття заявки.",
        "Рейтинги — це спосіб зробити якість сервісу прозорою. Після "
        "того як майстер закриває вашу заявку, ви отримуєте запит на "
        "оцінку від 1 до 5 зірок із коротким коментарем.\n\n"
        "Оцінки підсумовуються у профілі підрядника — керуюча "
        "компанія бачить середню зірку та відгуки, а мешканці — "
        "репутацію перед викликом.\n\n"
        "Ми не показуємо низькі оцінки у чорному списку й не "
        "дозволяємо коментарі без заявки-підстави. Це захищає "
        "сумлінних майстрів від несправедливого буллінгу та утримує "
        "систему чесною для обох сторін.",
        False,
        False,
        11,
    ),
    # ── Regular org-scoped ──────────────────────────────────────────────
    (
        "Прибирання під'їздів 22 квітня",
        "Сервіс",
        "Бригада клінінгу проведе повне миття сходів і ліфтів з "
        "09:00 до 13:00.",
        "Шановні мешканці, 22 квітня з 09:00 до 13:00 клінінгова "
        "бригада проведе повне вологе прибирання сходів, ліфтів і "
        "холів під'їздів у корпусах А та Б.\n\n"
        "На час робіт можливий легкий запах миючого засобу — він "
        "повністю вивітриться протягом години. Просимо не залишати "
        "речі на сходових майданчиках у цей день, щоб бригада могла "
        "обробити підлогу повністю.\n\n"
        "Якщо ви помітите ділянки, які потребують додаткової уваги, "
        "зафіксуйте це через портал заявок — ми передамо інформацію "
        "бригадиру на наступне прибирання.",
        False,
        True,
        3,
    ),
    (
        "Зустріч ОСББ 28 квітня — порядок денний",
        "Події",
        "Щомісячні збори у залі консьєржа. Обговорюємо ремонт "
        "паркування, тарифи на 2026 і нові камери.",
        "Запрошуємо всіх мешканців на щомісячну зустріч ОСББ «Зелений "
        "Квартал» 28 квітня о 19:00 у залі консьєржа корпусу А.\n\n"
        "Порядок денний: (1) звіт керуючої компанії за I квартал, "
        "(2) обговорення ремонту підземного паркування, (3) "
        "затвердження тарифів на комунальні послуги на 2026 рік, "
        "(4) план встановлення додаткових камер на дитячому "
        "майданчику.\n\n"
        "Якщо маєте питання до порядку денного — напишіть їх заздалегідь "
        "через форму зворотного зв'язку на порталі. Ми зведемо всі "
        "звернення і відповімо під час зборів.\n\n"
        "Присутність не обов'язкова, але вітається — від активності "
        "мешканців залежить те, як швидко ухвалюються рішення.",
        False,
        True,
        4,
    ),
    (
        "Ремонт ліфта у корпусі Б — графік робіт",
        "Ремонт",
        "З 19 до 24 квітня у корпусі Б працює тільки вантажний ліфт. "
        "Основний перебуває на плановому ТО.",
        "Шановні мешканці корпусу Б, з 19 до 24 квітня проводиться "
        "планове технічне обслуговування основного пасажирського "
        "ліфта. На цей період доступним залишається вантажний ліфт — "
        "він повноцінно перевозить людей.\n\n"
        "Після ТО ліфт пройде обов'язкове звірення сертифікату "
        "Держпраці — це займає приблизно 2 робочі дні після "
        "завершення робіт. Орієнтовна дата повернення в експлуатацію "
        "— 26 квітня.\n\n"
        "Якщо потрібна допомога з важким багажем у цей період — "
        "консьєрж надає тимчасовий ключ від вантажного ліфта "
        "безкоштовно. Дякуємо за терпіння.",
        False,
        True,
        6,
    ),
    (
        "Нові камери на дитячому майданчику",
        "Безпека",
        "Встановили 4 камери 4K з нічним режимом. Архів зберігається "
        "30 днів на захищеному сервері ОСББ.",
        "Цього тижня на дитячому майданчику між корпусами А та Б "
        "встановлено 4 додаткові камери 4K з інфрачервоним нічним "
        "режимом. Запис ведеться цілодобово, архів зберігається "
        "30 днів на локальному сервері ОСББ у приміщенні консьєржа.\n\n"
        "Доступ до архіву має тільки керуюча компанія та, за "
        "офіційним запитом, правоохоронні органи. Мешканці можуть "
        "запросити перегляд запису через заявку на порталі — "
        "відповідь протягом 48 годин у робочі дні.\n\n"
        "Камери НЕ передають відео у хмару і не використовуються для "
        "розпізнавання облич. Це принципова позиція ОСББ: "
        "спостереження — тільки для безпеки, без профайлингу.",
        False,
        True,
        9,
    ),
    (
        "Підготовка до літнього сезону: поради",
        "Події",
        "Як підготувати квартиру до літа — кондиціонер, сітки від "
        "комарів, економія води.",
        "З настанням теплої погоди рекомендуємо провести кілька "
        "простих процедур у квартирі, щоб літо минуло максимально "
        "комфортно.\n\n"
        "Кондиціонер: перед першим запуском промийте фільтри або "
        "замовте чистку у профільного майстра — за літо пилу "
        "назбирається мінімум, і техніка прослужить на 2-3 роки "
        "довше. Список перевірених майстрів — у розділі "
        "«Техніки» на порталі.\n\n"
        "Сітки від комарів: замовити можна через форму заявок — "
        "ОСББ уклав угоду з постачальником зі знижкою 15% для "
        "мешканців. Термін встановлення — 3-5 робочих днів.\n\n"
        "Економія води: влітку витрати зростають у середньому на "
        "20-30%. Перевірте крани на підтікання — навіть одна крапля "
        "на секунду це 20 літрів на добу.",
        False,
        True,
        14,
    ),
)


# Image canvas dimensions for generated covers. 960×480 matches a 2:1
# aspect ratio that the card's ``h-40 sm:h-44`` CSS crops cleanly.
COVER_WIDTH = 960
COVER_HEIGHT = 480


# ──────────────────────────── dataclass ─────────────────────────────────────


@dataclass
class NewsSeedResult:
    """Handles + counts returned to the orchestrator."""

    categories_created: int = 0
    news_created: int = 0
    news_skipped: int = 0
    covers_generated: int = 0

    news: list["News"] = field(default_factory=list, repr=False)
    categories: list["NewsCategory"] = field(default_factory=list, repr=False)


# ─────────────────────────────── entrypoint ─────────────────────────────────


def seed(
    *,
    users_result: "UsersSeedResult",
    organization_result: "OrganizationSeedResult",
    news_count: int = 10,
) -> NewsSeedResult:
    """Create/update demo News articles + categories.

    Parameters
    ----------
    users_result
        Seed output from ``seed_users``. We pull the first dispatcher
        as the author — the News feed semantically "belongs to" the
        management company, and dispatchers are the closest role.
    organization_result
        Seed output from ``seed_organization``. Org-scoped News rows
        link to ``organization_result.organization``; platform-wide
        ones leave ``organization=NULL`` per spec.
    news_count
        Cap for how many entries from ``NEWS_SPECS`` to create. Tests
        use a small number; the default ``10`` creates the full pool.

    Returns
    -------
    NewsSeedResult
        Counts and handles for the orchestrator's logging line.
    """
    from apps.news.models import News, NewsCategory

    result = NewsSeedResult()

    if not users_result.dispatchers:
        # Can't author News without a dispatcher; skip quietly rather
        # than 500 the whole seed run. This matches the defensive style
        # of the rest of the seed package.
        logger.warning("seed_news: no dispatchers available — skipping News seed")
        return result

    author = users_result.dispatchers[0].user
    organization = organization_result.organization

    with transaction.atomic():
        categories_by_name = _seed_categories(NewsCategory, result)
        _seed_news(
            News,
            NEWS_SPECS[:news_count],
            author=author,
            organization=organization,
            categories_by_name=categories_by_name,
            result=result,
        )

    logger.info(
        "seed_news: categories=+%d news=+%d(skip=%d) covers=%d",
        result.categories_created, result.news_created,
        result.news_skipped, result.covers_generated,
    )
    return result


# ───────────────────────────── helpers ──────────────────────────────────────


def _seed_categories(
    NewsCategory,
    result: NewsSeedResult,
) -> dict[str, "NewsCategory"]:
    """Idempotent category upsert; returns name → instance map."""
    by_name: dict[str, "NewsCategory"] = {}
    for name, color in CATEGORY_SPECS:
        cat, created = NewsCategory.objects.get_or_create(
            name=name,
            defaults={"color": color},
        )
        if created:
            result.categories_created += 1
        else:
            # Re-assert the colour in case an admin hand-edited it —
            # seed is the authoritative source for demo categories.
            if cat.color != color:
                cat.color = color
                cat.save(update_fields=["color"])
        by_name[name] = cat
        result.categories.append(cat)
    return by_name


def _seed_news(
    News,
    specs: tuple[tuple[str, str, str, str, bool, bool, int], ...],
    *,
    author,
    organization,
    categories_by_name: dict,
    result: NewsSeedResult,
) -> None:
    """Idempotent News upsert keyed on title."""
    now = timezone.now()

    for idx, (title, cat_name, excerpt, body, pinned, org_scoped, days_ago) in enumerate(specs):
        category = categories_by_name.get(cat_name)
        published_at = now - timedelta(days=days_ago)

        news, created = News.objects.get_or_create(
            title=title,
            defaults={
                "excerpt": excerpt,
                "body": body,
                "category": category,
                "author": author,
                "organization": organization if org_scoped else None,
                "published_at": published_at,
                "is_published": True,
                "pinned": pinned,
            },
        )

        if created:
            # Generate and attach cover image — only on first insert so
            # rerunning the seed doesn't regenerate MEDIA files for no
            # reason. Pillow is on the hot path here; keep this cheap.
            cover_bytes = _render_cover(
                idx=idx,
                title=title,
                accent_hex=category.color if category else "#2F6FED",
            )
            if cover_bytes is not None:
                filename = f"news-cover-{idx+1:02d}.png"
                news.cover_image.save(
                    filename, ContentFile(cover_bytes), save=True,
                )
                result.covers_generated += 1

            # Stomp created_at so ordering by (-pinned, -published_at,
            # -created_at) falls out right. ``auto_now_add`` ignores
            # the value passed to create(), so we patch via queryset.
            News.objects.filter(pk=news.pk).update(created_at=published_at)
            result.news_created += 1
        else:
            result.news_skipped += 1
            # Defensive backfill: if an older demo row lacks an org
            # link that it now should have, fix it so ``/news``
            # shows it to the right tenants.
            if org_scoped and news.organization_id is None:
                News.objects.filter(pk=news.pk).update(
                    organization=organization,
                )

        news.refresh_from_db()
        result.news.append(news)


# ──────────────────────────── image generation ──────────────────────────────


def _render_cover(*, idx: int, title: str, accent_hex: str) -> bytes | None:
    """Produce a 960×480 PNG gradient tinted with the category colour.

    Deterministic: the gradient direction and secondary colour derive
    from ``idx`` and ``accent_hex`` only, so reruns emit byte-identical
    files. Returns ``None`` if Pillow can't be imported (test-only
    environments where the binary wheel isn't available); callers
    treat missing covers as a warning, not a hard failure.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:  # pragma: no cover — Pillow is a base requirement
        logger.warning("seed_news: Pillow unavailable — covers will be empty")
        return None

    accent = _hex_to_rgb(accent_hex)

    # Two-stop vertical gradient: accent at the top darkened by 20 %,
    # accent at the bottom lightened towards near-white by 85 %. Gives
    # the card a "tinted glass" feel rather than flat colour.
    top = _shade(accent, 0.80)           # 20 % darker
    bottom = _mix(accent, (255, 255, 255), 0.85)  # 85 % toward white

    img = Image.new("RGB", (COVER_WIDTH, COVER_HEIGHT), color=top)
    draw = ImageDraw.Draw(img)

    for y in range(COVER_HEIGHT):
        t = y / (COVER_HEIGHT - 1)
        row_rgb = _mix(top, bottom, t)
        draw.line([(0, y), (COVER_WIDTH, y)], fill=row_rgb)

    # Offset circle as a subtle decorative accent — makes each cover
    # visually unique even though they share the palette. Position
    # derives from ``idx`` so it's deterministic.
    cx = 120 + (idx * 73) % (COVER_WIDTH - 240)
    cy = 80 + (idx * 41) % (COVER_HEIGHT - 160)
    radius = 180
    overlay_color = _mix(accent, (255, 255, 255), 0.35) + (60,)  # RGBA
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=overlay_color,
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert ``#RRGGBB`` to a 0–255 RGB tuple; tolerant of missing ``#``."""
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _mix(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """Linear interpolation between two RGB triples; ``t`` ∈ [0, 1]."""
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _shade(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Multiply each channel by ``factor`` (< 1.0 = darker)."""
    return (
        max(0, min(255, int(rgb[0] * factor))),
        max(0, min(255, int(rgb[1] * factor))),
        max(0, min(255, int(rgb[2] * factor))),
    )
