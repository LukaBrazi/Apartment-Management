"""Seed demo News articles and NewsCategories (portal «Новини» section).

Design
------
* **4 categories** with distinct colours — portal visitors see coloured badges.
* **8 news items** — 5 published + 1 pinned + 2 drafts — so the admin panel
  shows realistic variety (published/draft toggle) and the portal feed has
  enough articles to scroll.
* All items are scoped to the demo organisation so reset_scope can clean them
  up in one filter.
* ``is_published=True`` + ``published_at`` is set for all live items;
  ``published_at`` is spread over the last 30 days so the timeline looks
  natural.
* Natural key: ``(organization, title)`` — rerunning without ``--reset`` is
  idempotent.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.news.models import News, NewsCategory
    from .seed_building import BuildingSeedResult
    from .seed_organization import OrganizationSeedResult
    from .seed_users import UsersSeedResult

logger = logging.getLogger(__name__)


# ─────────────────────────────── categories ─────────────────────────────────

CATEGORY_SPECS: tuple[tuple[str, str], ...] = (
    ("Оновлення",     "#2F6FED"),  # blue
    ("Обслуговування", "#10B981"),  # green
    ("Заходи",        "#F59E0B"),  # amber
    ("Важливо",       "#EF4444"),  # red
)


# ──────────────────────────────── news items ────────────────────────────────
# (title, excerpt, body, category_name, is_published, pinned, days_ago, external_url)

NEWS_SPECS: tuple[tuple[str, str, str, str, bool, bool, int, str], ...] = (
    (
        "Портал ApartmentOS оновлено до версії 2.4",
        "Вийшло велике оновлення порталу: нова сторінка новин, "
        "покращений пошук, бейдж непрочитаних повідомлень у меню.",
        "Шановні мешканці!\n\n"
        "Ми раді повідомити про вихід оновлення ApartmentOS 2.4. "
        "Основні зміни:\n\n"
        "• Новий розділ «Новини» — актуальна інформація від управителя "
        "прямо на порталі, без Telegram і паперових оголошень.\n"
        "• Бейдж непрочитаних новин у лівому меню — ви завжди бачите, "
        "коли з'явилось щось нове.\n"
        "• Пошук по заявках став швидшим.\n"
        "• Виправлено кілька дрібних помилок у мобільній версії.\n\n"
        "Дякуємо за вашу активність і відгуки — саме вони допомагають "
        "нам робити портал кращим.",
        "Оновлення", True, True, 3, "",
    ),
    (
        "Планове технічне обслуговування ліфтів — квітень 2026",
        "З 28 по 30 квітня сервісна бригада проведе щорічне ТО ліфтів "
        "у корпусах А та Б. Можливі короткі зупинки.",
        "Повідомляємо про плановий технічний огляд ліфтового обладнання.\n\n"
        "**Терміни:** 28–30 квітня 2026 р.\n"
        "**Корпуси:** А (під'їзди 1–3) та Б (під'їзди 4–6).\n"
        "**Час проведення:** з 09:00 до 16:00.\n\n"
        "Під час роботи можливі короткі зупинки ліфтів (до 15 хвилин). "
        "Просимо враховувати це при плануванні виходів, особливо мешканців "
        "із дітьми та людей з обмеженими можливостями.\n\n"
        "Контакт: dispatcher@demo.com або через форму заявок на порталі.",
        "Обслуговування", True, False, 5, "",
    ),
    (
        "День відкритих дверей ОСББ — 10 травня 2026",
        "Запрошуємо всіх мешканців на щорічні збори та день відкритих "
        "дверей. Звіт управителя, Q&A, розіграш призів.",
        "Щорічні загальні збори співвласників та День відкритих дверей "
        "відбудеться **10 травня 2026 о 17:00** у залі на першому поверсі "
        "корпусу А.\n\n"
        "**Порядок денний:**\n"
        "1. Звіт управителя за 2025 рік.\n"
        "2. Фінансовий звіт ОСББ.\n"
        "3. Плани на 2026 рік (реконструкція паркінгу, нові камери).\n"
        "4. Питання та відповіді.\n"
        "5. Розіграш подарункових сертифікатів серед присутніх.\n\n"
        "Явка бажана — рішення приймаються кворумом. "
        "Чим більше мешканців, тим сильніший голос ЖК.",
        "Заходи", True, False, 7, "",
    ),
    (
        "Нові правила паркування з 1 травня 2026",
        "З 1 травня запроваджуються нові правила користування "
        "гостьовим паркінгом: обмеження до 3 годин, система перепусток.",
        "Шановні мешканці та гості!\n\n"
        "З **1 травня 2026 року** набувають чинності оновлені правила "
        "користування гостьовим паркінгом ЖК.\n\n"
        "**Ключові зміни:**\n"
        "• Гостьові місця — не більше 3 годин підряд.\n"
        "• Гості з ночівлею — необхідна разова перепустка через портал "
        "(розділ «Перепустки»).\n"
        "• Мешканці — продовжуємо діючу систему постійних перепусток.\n\n"
        "Порушники отримуватимуть попереджувальні наліпки, при повторних "
        "порушеннях — евакуація авто за рахунок власника.\n\n"
        "Питання — dispatcher@demo.com.",
        "Важливо", True, False, 10, "",
    ),
    (
        "Встановлено нові шлагбауми на в'їздах",
        "Завершено монтаж автоматичних шлагбаумів. "
        "Активуйте ваш автомобільний номер у налаштуваннях профілю.",
        "Роботи з монтажу автоматичних шлагбаумів на обох в'їздах на "
        "територію ЖК завершені.\n\n"
        "**Як активувати в'їзд:**\n"
        "1. Зайдіть у «Профіль» → «Мій транспорт».\n"
        "2. Додайте номерний знак авто.\n"
        "3. Після перевірки охороною (до 24 год.) шлагбаум відкриватиметься "
        "автоматично.\n\n"
        "Гості реєструються через розділ «Перепустки» — охорона видасть "
        "тимчасовий код.\n\n"
        "Дякуємо за терпіння під час будівельних робіт!",
        "Оновлення", True, False, 14, "",
    ),
    (
        "Профілактика системи опалення — вересень 2026",
        "У вересні планується промивка та балансування системи опалення. "
        "Деталі будуть оголошені додатково.",
        "Шановні мешканці!\n\n"
        "Попередньо повідомляємо: у **вересні 2026 року** буде проведено "
        "планову промивку та гідравлічне балансування системи опалення.\n\n"
        "Конкретні дати будуть уточнені та опубліковані окремою новиною "
        "не пізніше серпня. Орієнтовна тривалість — 3–5 робочих днів.\n\n"
        "Ваш управитель.",
        "Обслуговування", True, False, 20, "",
    ),
    # Drafts — visible in admin but not in portal feed
    (
        "Підсумки опитування мешканців щодо облаштування дитячого майданчика",
        "Результати опитування: більшість підтримала встановлення "
        "нових гірок та пісочниці.",
        "Чернетка. Буде опублікована після фінального узгодження бюджету.",
        "Заходи", False, False, 25, "",
    ),
    (
        "Нові контакти аварійних служб",
        "Оновлений перелік контактів сантехніка, електрика та "
        "аварійної служби на 2026 рік.",
        "Чернетка. В процесі оновлення контактів у відповідних службах.",
        "Обслуговування", False, False, 28, "",
    ),
)


# ─────────────────────────────── dataclass ──────────────────────────────────


@dataclass
class NewsSeedResult:
    categories_created: int = 0
    news_created: int = 0
    news_skipped: int = 0


# ──────────────────────────────── entrypoint ────────────────────────────────


def seed(
    *,
    users_result: "UsersSeedResult",
    organization_result: "OrganizationSeedResult",
    news_count: int = 8,
) -> NewsSeedResult:
    """Create demo News categories and articles.

    Scoped to the demo organisation so reset_scope can clean up with a
    single ``News.objects.filter(organization=demo_org).delete()``.
    """
    from apps.news.models import News, NewsCategory

    organization = organization_result.organization
    # Use the first dispatcher as author — they are staff so no save() guard.
    author = (
        users_result.dispatchers[0].user
        if users_result.dispatchers
        else None
    )

    result = NewsSeedResult()

    with transaction.atomic():
        # ── 1. Categories ────────────────────────────────────────────────
        categories: dict[str, "NewsCategory"] = {}
        for name, color in CATEGORY_SPECS:
            cat, created = NewsCategory.objects.get_or_create(
                name=name,
                defaults={"color": color},
            )
            if created:
                result.categories_created += 1
            categories[name] = cat

        # ── 2. News items ─────────────────────────────────────────────────
        now = timezone.now()
        for spec in NEWS_SPECS[:news_count]:
            title, excerpt, body, cat_name, is_published, pinned, days_ago, ext_url = spec
            category = categories.get(cat_name)
            published_at = (now - timedelta(days=days_ago)) if is_published else None

            news_item, created = News.objects.get_or_create(
                organization=organization,
                title=title,
                defaults={
                    "excerpt": excerpt,
                    "body": body,
                    "category": category,
                    "author": author,
                    "is_published": is_published,
                    "pinned": pinned,
                    "published_at": published_at,
                    "external_url": ext_url,
                },
            )
            if created:
                result.news_created += 1
            else:
                result.news_skipped += 1

    logger.info(
        "seed_news: categories=+%d news=+%d(skip=%d)",
        result.categories_created, result.news_created, result.news_skipped,
    )
    return result
