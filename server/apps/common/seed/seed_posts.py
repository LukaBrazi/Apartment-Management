"""Seed demo Posts, Replies and Announcements (plan §6, §7).

Output per the blueprint:

* **12 canonical tags** (plan §6.1) pre-created via ``taggit`` so the
  popular-tags sidebar has immediate content.
* **18 Posts** (plan §6.2) — title + 3-paragraph Ukrainian body, author
  rotated between dispatchers/residents, ``upvotes`` / ``downvotes``
  counts, 1-4 tags each.  Natural key: ``title`` (titles are unique by
  design).
* **Replies** — 1-4 on every 2nd-3rd post, authored by residents (plan §6.3).
* **Bookmarks & upvotes** — a subset of residents bookmark 3-5 posts each,
  ``upvotes``/``downvotes`` M2M rows populated to match the counters so the
  admin dashboard sorting by reputation reads correctly (plan §6.4).
* **5 Announcements** attached to the demo Building (plan §7) — 3 active
  + 2 archived.  Natural key: ``(building, title)``.

Signal hygiene
--------------
``apps.notifications.signals.on_announcement_created`` dispatches a Celery
``notify_building_tenants_announcement`` task on every insert.  We
disconnect it for the duration of the seed and reconnect in a ``finally``.

``Post.save()`` enforces that the author be superuser/staff/tenant.  All
our demo authors (dispatchers=staff, residents=tenant-occupation) pass,
so no workaround is needed.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from .helpers import BASE_TIME  # noqa: F401 — tests reference it

if TYPE_CHECKING:  # pragma: no cover
    from apps.posts.models import Announcement, Post, Reply
    from .seed_building import BuildingSeedResult
    from .seed_users import SeededUser, UsersSeedResult

logger = logging.getLogger(__name__)

POSTS_RNG_SEED = 313131  # keep separate from issues RNG seed

# ──────────────────────────── data pools ────────────────────────────────────

# Plan §6.1 — 12 canonical tag slugs.  taggit lowercases + slugifies on save,
# but these already comply so ``get_or_create(name=..)`` yields stable rows.
CANONICAL_TAGS: tuple[str, ...] = (
    "правила", "ремонт", "заявки", "інструкція", "перепустки", "електрика",
    "сантехніка", "прибирання", "опалення", "паркування", "безпека", "новини",
)

# Plan §6.2 — 18 titles with their tag lists.  Each entry is
# ``(title, tags_tuple, upvotes, downvotes)`` — upvote counts reflect the
# "forum popularity" column on the admin dashboard.
POST_SPECS: tuple[tuple[str, tuple[str, ...], int, int], ...] = (
    ("Правила паркування на території ЖК",
     ("правила", "паркування"), 50, 2),
    ("Як правильно подавати заявку на ремонт",
     ("інструкція", "заявки", "ремонт"), 38, 1),
    ("Графік роботи сантехніка",
     ("сантехніка", "інструкція"), 22, 0),
    ("Економія електроенергії: поради для мешканців",
     ("електрика",), 17, 3),
    ("Підготовка до опалювального сезону",
     ("опалення",), 14, 0),
    ("Нові правила сортування сміття",
     ("правила",), 25, 4),
    ("Оновлення системи перепусток — що нового",
     ("перепустки", "новини"), 30, 1),
    ("Як скликати загальні збори мешканців",
     ("правила",), 11, 0),
    ("Безпека у багатоквартирному будинку: гайд",
     ("безпека", "інструкція"), 19, 2),
    ("Що робити, якщо сусіди шумлять",
     ("правила",), 32, 5),
    ("Ремонт у квартирі: дозволені години робіт",
     ("ремонт", "правила"), 27, 3),
    ("Нові камери на під'їздах — інформація",
     ("безпека", "новини"), 21, 1),
    ("Паркінг підземний: інструкція користування",
     ("паркування", "інструкція"), 18, 2),
    ("Як викликати аварійну службу вночі",
     ("заявки", "інструкція"), 15, 0),
    ("Графік прибирання сходових кліток",
     ("прибирання",), 9, 1),
    ("FAQ — поширені питання мешканців",
     ("інструкція",), 40, 2),
    ("Благодійний захід на День Незалежності",
     ("новини",), 28, 0),
    ("Звіт керуючої компанії за I квартал 2026",
     ("новини",), 24, 1),
)


# Three-paragraph body templates (rotated by idx) — keeps bodies distinct but
# plan-realistic without wiring up the full Faker pipeline.  Ukrainian mimics
# actual management-company forum tone.
BODY_TEMPLATES: tuple[str, ...] = (
    (
        "Шановні мешканці! Цей пост оновлюється щомісяця — звіряйтесь із ним "
        "перед тим як звертатись до управителя. Будемо вдячні за доповнення "
        "у коментарях.\n\n"
        "Детальна інформація нижче. Якщо щось не описано — пишіть через форму "
        "зворотного зв'язку на порталі ApartmentOS або напряму диспетчеру "
        "(dispatcher@demo.com).\n\n"
        "Нагадуємо: форум модерує керуюча компанія, образливі коментарі "
        "видаляємо без попередження. Тримаємо повагу одне до одного."
    ),
    (
        "Дорогі сусіди! Об'єднання співвласників ЖК — це наша спільна відповідальність. "
        "Чим активніше ми беремо участь у житті будинку, тим комфортнішим він стає.\n\n"
        "Нижче — структурована відповідь на часті питання, зібрана диспетчерською "
        "службою. Якщо ваше питання не висвітлено, повідомте нам — додамо у наступній "
        "редакції цього посту.\n\n"
        "Пам'ятайте: більшість питань вирішуються швидше через портал заявок, "
        "ніж через усну бесіду у ліфті. Дякуємо за розуміння."
    ),
    (
        "Публікація підготовлена управителькою ЖК за результатами щомісячних "
        "зборів. Інформація узгоджена з членами ОСББ та профільними "
        "підрядниками.\n\n"
        "Прошу врахувати: у разі виявлення неточностей — звертайтесь до "
        "контактів, вказаних у профілі автора. Відповідь протягом 48 годин "
        "у робочі дні.\n\n"
        "Для мешканців, хто вперше користується порталом — інструкція щодо "
        "реєстрації і створення заявок є у закріпленому пості «FAQ»."
    ),
)


# Plan §6.3 — reply bodies pool.
REPLY_TEMPLATES: tuple[str, ...] = (
    "Дякую, дуже корисно!",
    "А чи є довідник контактів?",
    "Супер, нарешті зрозуміло.",
    "Підтримую, давно пора.",
    "У нас теж така ситуація — згодні.",
    "Додайте, будь ласка, контакти підрядника.",
    "Чудово, що тема обговорюється публічно.",
    "Очікую оновлення у наступному кварталі.",
)


# Plan §7 — 5 announcements, 3 active + 2 archive.  Offsets are days-before-now
# so the timeline makes sense against the current clock (plan §10 daily reset).
ANNOUNCEMENT_SPECS: tuple[tuple[str, str, bool, int], ...] = (
    (
        "Планове відключення води 21.04.2026 з 10:00 до 14:00",
        "Шановні мешканці! У вівторок 21 квітня з 10:00 до 14:00 буде "
        "відключена холодна вода у корпусах А та Б у зв'язку з плановою "
        "заміною магістральної засувки. Гаряча вода — без змін. Просимо "
        "завчасно запастися питною водою. Дякуємо за розуміння.",
        True, 2,  # 2 days ago
    ),
    (
        "Завтра обробка під'їздів дезінфектором",
        "Завтра з 09:00 до 11:00 бригада клінінгу проведе планову обробку "
        "під'їздів і ліфтів дезінфекційним розчином. Просимо у цей час не "
        "перебувати у місцях загального користування. Запах вивітриться "
        "протягом години.",
        True, 1,
    ),
    (
        "Графік роботи консьєржа на травневі свята",
        "Нагадуємо про розклад консьєржа на майські свята: 1 травня — "
        "скорочений день до 16:00, 9 травня — чергування у форматі "
        "«тільки виклик». В інші дні — звичайний графік. Контактний "
        "телефон консьєржа — на дошці оголошень.",
        True, 5,
    ),
    (
        "АРХІВ: Відключення світла 12.03.2026",
        "Планове відключення електропостачання корпусу А відбулося 12 "
        "березня з 09:00 до 15:00 для заміни щитової. Роботи завершені "
        "штатно. Дякуємо за терпіння.",
        False, 40,
    ),
    (
        "АРХІВ: Обробка проти щурів 01.02.2026",
        "У підвальних приміщеннях корпусів А та Б проведена профілактична "
        "обробка проти гризунів. Наступна планова обробка — у жовтні 2026.",
        False, 75,
    ),
)


# ──────────────────────────── dataclass ─────────────────────────────────────


@dataclass
class PostsSeedResult:
    """Handles + counts returned to the orchestrator."""

    tags_created: int = 0
    posts_created: int = 0
    posts_skipped: int = 0
    replies_created: int = 0
    announcements_created: int = 0
    announcements_skipped: int = 0

    posts: list["Post"] = field(default_factory=list, repr=False)
    announcements: list["Announcement"] = field(default_factory=list, repr=False)

    def total_upvotes(self) -> int:
        return sum(p.upvotes for p in self.posts)


# ─────────────────────────────── entrypoint ─────────────────────────────────


def seed(
    *,
    users_result: "UsersSeedResult",
    building_result: "BuildingSeedResult",
    posts_count: int = 18,
    announcements_count: int = 5,
) -> PostsSeedResult:
    """Create/update demo posts + announcements per plan §6–§7."""
    from apps.posts.models import Announcement, Post, Reply
    from taggit.models import Tag

    result = PostsSeedResult()

    # ── 1. Tags ──────────────────────────────────────────────────────────
    for slug in CANONICAL_TAGS:
        _tag, created = Tag.objects.get_or_create(name=slug)
        if created:
            result.tags_created += 1

    # ── 2. Authors — dispatchers + tenant-residents (plan §6.2) ─────────
    authors = _author_pool(users_result)
    if not authors:
        raise RuntimeError("seed_posts: no eligible authors (dispatchers/tenants)")

    rng = random.Random(POSTS_RNG_SEED)

    with _announcement_signal_suspended():
        with transaction.atomic():
            # ── 3. Posts ────────────────────────────────────────────────
            posts = _seed_posts(
                Post, POST_SPECS[:posts_count], authors, rng, result,
            )

            # ── 4. Replies on every 2nd-3rd post ─────────────────────────
            _seed_replies(Reply, posts, users_result, rng, result)

            # ── 5. Bookmarks + upvote M2M ────────────────────────────────
            _seed_engagement(posts, users_result, rng)

            # ── 6. Announcements ────────────────────────────────────────
            _seed_announcements(
                Announcement,
                building_result.building,
                ANNOUNCEMENT_SPECS[:announcements_count],
                result,
            )

    logger.info(
        "seed_posts: tags=+%d posts=+%d(skip=%d) replies=+%d "
        "announcements=+%d(skip=%d)",
        result.tags_created, result.posts_created, result.posts_skipped,
        result.replies_created, result.announcements_created,
        result.announcements_skipped,
    )
    return result


# ───────────────────────────── helpers ──────────────────────────────────────


def _author_pool(users_result: "UsersSeedResult") -> list["SeededUser"]:
    """Dispatchers (first) + first 6 residents — gives the illusion of variety."""
    pool: list["SeededUser"] = []
    pool.extend(users_result.dispatchers)
    # Take a slice of residents with apartments so Post.save() auth-check passes
    # even if someone tightens it to require apartment later.
    pool.extend(r for r in users_result.residents[:6] if r.unit is not None)
    if users_result.tenant is not None:
        pool.append(users_result.tenant)
    return pool


def _seed_posts(
    Post,
    specs: tuple[tuple[str, tuple[str, ...], int, int], ...],
    authors: list["SeededUser"],
    rng: random.Random,
    result: PostsSeedResult,
) -> list["Post"]:
    """Create posts idempotently; set tags and vote counters."""
    now = timezone.now()
    posts: list["Post"] = []

    for idx, (title, tags, upvotes, downvotes) in enumerate(specs):
        author = authors[idx % len(authors)].user
        # Spread created_at across the last 30 days; dispatchers' posts sit
        # more recent than residents' — heuristic for "staff posts more".
        age_days = 2 + (idx * 11) % 28
        created_at = now - timedelta(days=age_days, hours=(idx % 8))

        body = BODY_TEMPLATES[idx % len(BODY_TEMPLATES)]

        post, created = Post.objects.get_or_create(
            title=title,
            defaults={
                "body": body,
                "author": author,
                "upvotes": upvotes,
                "downvotes": downvotes,
            },
        )

        if created:
            # ``created_at`` is ``auto_now_add`` → stomp via queryset update.
            Post.objects.filter(pk=post.pk).update(created_at=created_at)
            result.posts_created += 1
            # Tags are always set on create.
            post.tags.set(tags)
        else:
            result.posts_skipped += 1
            # Don't overwrite on rerun; plan §10 tells callers to use --reset.

        post.refresh_from_db()
        posts.append(post)

    return posts


def _seed_replies(
    Reply,
    posts: list["Post"],
    users_result: "UsersSeedResult",
    rng: random.Random,
    result: PostsSeedResult,
) -> None:
    """Attach 1-4 replies to every 2nd-3rd post (plan §6.3)."""
    resident_users = [r.user for r in users_result.residents if r.user is not None]
    if not resident_users:
        return

    for post_idx, post in enumerate(posts):
        # every 2nd or 3rd — plan wording — take "roughly half".
        if post_idx % 3 == 0 or post_idx % 2 == 0:
            reply_count = 1 + (post_idx % 4)  # 1..4
            for r_idx in range(reply_count):
                body = REPLY_TEMPLATES[(post_idx * 4 + r_idx) % len(REPLY_TEMPLATES)]
                author = resident_users[(post_idx + r_idx) % len(resident_users)]
                _reply, created = Reply.objects.get_or_create(
                    post=post,
                    author=author,
                    body=body,
                )
                if created:
                    result.replies_created += 1


def _seed_engagement(
    posts: list["Post"],
    users_result: "UsersSeedResult",
    rng: random.Random,
) -> None:
    """Populate bookmarked_by / upvoted_by / downvoted_by M2M rows.

    The ``Post.upvotes`` counter on the model is the source of truth for the
    number of upvotes shown; M2M tables exist for audit.  We seed both in
    rough agreement so queries like ``upvoted_by.count() == upvotes`` hold
    within ±1 (exact match would require per-user uniqueness which we
    ensure via ``.set(..)``).
    """
    residents = [r.user for r in users_result.residents if r.user is not None]
    if not residents:
        return

    # Bookmarks — plan §6.4 "частина residents має bookmarked 3-5 постів".
    # Apply to every 3rd resident.
    for r_idx, user in enumerate(residents):
        if r_idx % 3 != 0:
            continue
        bookmark_n = 3 + (r_idx % 3)  # 3..5
        picks = sorted(posts, key=lambda p: (p.upvotes, p.pk), reverse=True)[:bookmark_n]
        user.bookmarked_posts.set(picks)

    # Upvoters: match the counter up to len(residents).
    for post in posts:
        want = min(post.upvotes, len(residents))
        # Pick a deterministic slice rotated by post.pk.
        if hasattr(post.pk, "int"):
            start = post.pk.int % len(residents)
        else:
            start = hash(post.pk) % len(residents)
        upvoters = [residents[(start + i) % len(residents)] for i in range(want)]
        post.upvoted_by.set(upvoters)

        want_down = min(post.downvotes, len(residents) - want)
        downvoters = [
            residents[(start + want + i) % len(residents)] for i in range(want_down)
        ]
        post.downvoted_by.set(downvoters)


def _seed_announcements(
    Announcement,
    building,
    specs: tuple[tuple[str, str, bool, int], ...],
    result: PostsSeedResult,
) -> None:
    """Idempotent announcement upsert scoped to the demo building."""
    now = timezone.now()
    for title, body, is_active, days_ago in specs:
        created_at = now - timedelta(days=days_ago)
        ann, created = Announcement.objects.get_or_create(
            building=building,
            title=title,
            defaults={"body": body, "is_active": is_active},
        )
        if created:
            Announcement.objects.filter(pk=ann.pk).update(created_at=created_at)
            result.announcements_created += 1
        else:
            result.announcements_skipped += 1
        result.announcements.append(ann)


# ──────────────────────── signal disconnect/reconnect ───────────────────────


class _announcement_signal_suspended:
    """Disconnect the ``on_announcement_created`` Celery-fan-out signal."""

    def __enter__(self):
        from apps.posts.models import Announcement
        from apps.notifications.signals import on_announcement_created
        from django.db.models.signals import post_save

        self._post = (post_save, on_announcement_created, Announcement)
        post_save.disconnect(on_announcement_created, sender=Announcement)
        return self

    def __exit__(self, exc_type, exc, tb):
        signal, receiver, sender = self._post
        signal.connect(receiver, sender=sender, weak=False)
        return False
