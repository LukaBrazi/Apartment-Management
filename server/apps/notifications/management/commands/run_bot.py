"""Polling mode for development — one process, all active org bots.

PR-14 phase 5 rewires this command away from the old platform-wide
``TELEGRAM_BOT_TOKEN`` setting. Instead we:

* Enumerate every ``OrganizationBot`` with ``is_active=True`` and a
  non-empty token.
* Build a python-telegram-bot ``Application`` per bot (each needs its
  own token, its own updater, its own polling loop).
* Register shared command handlers that close over ``bot`` so the
  incoming ``chat_id`` is resolved against the right org.

Local-only: production uses the webhook endpoint (see
``TelegramWebhookView``) so we don't pay for N persistent polling
connections in the same pod.

Usage:
    python manage.py run_bot             # poll every active bot
    python manage.py run_bot --bot=id    # poll a single bot (debug)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run Telegram bots in polling mode (dev only — prod uses webhook)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--bot",
            dest="bot_id",
            default=None,
            help=(
                "Optional: run only the bot with this UUID (or bot_username). "
                "By default every active bot is polled concurrently."
            ),
        )

    def handle(self, *args, **options):
        # All DB reads go through sync_to_async inside the asyncio
        # loop; list the targeted bot PKs upfront so we don't hit the
        # ORM from async context unexpectedly.
        from apps.notifications.models import OrganizationBot

        qs = OrganizationBot.objects.filter(is_active=True)
        bot_filter = options.get("bot_id")
        if bot_filter:
            qs = qs.filter(
                models_or(["id", "bot_username"], bot_filter, qs.model),
            )

        bots = [
            b for b in qs.iterator()
            if b.is_configured  # drops rows with empty tokens
        ]
        if not bots:
            self.stderr.write(
                self.style.WARNING(
                    "run_bot: no active bots found — nothing to poll.",
                ),
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"run_bot: polling {len(bots)} bot(s): "
                + ", ".join(f"@{b.bot_username}" for b in bots),
            ),
        )
        asyncio.run(_run_all(bots))


# ── Helpers ────────────────────────────────────────────────────────────────


def models_or(fields, value, model):
    """Return a Q() that ORs equality on each field.

    Supports ``--bot=<UUID>`` and ``--bot=<bot_username>`` without making
    the caller pick. We try each field in turn.
    """
    from django.db.models import Q

    q = Q()
    for f in fields:
        try:
            # Validate field-by-field so a malformed UUID on ``id`` doesn't
            # explode the whole query. Django still validates on execute,
            # but ``bot_username`` accepts free strings.
            model._meta.get_field(f)
            q |= Q(**{f: value})
        except Exception:
            continue
    return q


async def _run_all(bots: Iterable):
    """Fan out one polling ``Application`` per bot and await them all.

    Each bot gets its own ``asyncio.Task`` so a crash in one doesn't
    take the rest down — cancellations are isolated too, so Ctrl-C
    cleanly stops every bot.
    """
    tasks = [asyncio.create_task(_run_one(bot)) for bot in bots]
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()
        raise


async def _run_one(bot):
    """Build and run a python-telegram-bot ``Application`` for one bot."""
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes

    from apps.notifications.update_handlers import (
        handle_start,
        handle_status,
        handle_stop,
    )

    async def _as_handler(sync_handler):
        """Wrap a sync handler (ORM touching) so the PTB handler can
        ``await`` it without hitting Django's async-safety guard."""
        async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat = update.effective_chat
            if chat is None:
                return
            args = context.args or []
            result = await sync_to_async(sync_handler, thread_sensitive=True)(
                bot, chat.id, args,
            )
            if result is None:
                return
            await update.message.reply_text(
                result.reply_text, parse_mode=result.parse_mode,
            )
        return handler

    # handle_stop / handle_status don't take args — adapt signature.
    def _start(bot_, chat_id, args):
        return handle_start(bot_, chat_id, args)

    def _stop(bot_, chat_id, _args):
        return handle_stop(bot_, chat_id)

    def _status(bot_, chat_id, _args):
        return handle_status(bot_, chat_id)

    app = Application.builder().token(bot.bot_token).build()
    app.add_handler(CommandHandler("start", await _as_handler(_start)))
    app.add_handler(CommandHandler("stop", await _as_handler(_stop)))
    app.add_handler(CommandHandler("status", await _as_handler(_status)))

    logger.info("run_bot: polling started for @%s", bot.bot_username)
    try:
        # run_polling blocks until cancelled — it installs its own signal
        # handlers, which is fine because we run this only in dev.
        await app.run_polling(allowed_updates=Update.ALL_TYPES)
    except asyncio.CancelledError:
        logger.info("run_bot: cancelled for @%s", bot.bot_username)
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "run_bot: polling crashed for @%s: %s", bot.bot_username, exc,
        )
