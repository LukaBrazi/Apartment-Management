"""
Management command to run the Telegram bot in polling mode.
Usage: python manage.py run_bot

For production, prefer webhook mode via the /telegram/webhook/ endpoint.
"""
import asyncio
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Start Telegram bot in polling mode"

    def handle(self, *args, **options):
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not token:
            self.stderr.write(self.style.ERROR("TELEGRAM_BOT_TOKEN is not set in settings."))
            return

        self.stdout.write(self.style.SUCCESS("Starting Telegram bot (polling mode)..."))
        asyncio.run(self._run())

    async def _run(self):
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes

        bot_token = settings.TELEGRAM_BOT_TOKEN
        internal_secret = getattr(settings, "TELEGRAM_INTERNAL_SECRET", "")

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle /start command — optionally with a verification token."""
            args = context.args
            if args:
                token_value = args[0]
                chat_id = update.effective_chat.id
                # Call our internal API to verify
                import httpx
                api_url = getattr(settings, "TELEGRAM_BOT_API_BASE", "http://django:8000")
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(
                            f"{api_url}/api/v1/notifications/telegram/verify/",
                            json={"token": token_value, "chat_id": chat_id},
                            headers={"X-Telegram-Internal-Secret": internal_secret},
                            timeout=10,
                        )
                    if resp.status_code == 200:
                        await update.message.reply_text(
                            "✅ *Telegram підключено!*\n\nТепер ви будете отримувати сповіщення від Skandi Apartments.",
                            parse_mode="Markdown",
                        )
                    else:
                        await update.message.reply_text("❌ Невірний або прострочений токен. Спробуйте ще раз.")
                except Exception as e:
                    logger.error(f"Bot verify error: {e}")
                    await update.message.reply_text("Сталася помилка. Спробуйте пізніше.")
            else:
                await update.message.reply_text(
                    "👋 *Вітаємо у Skandi Apartments Bot!*\n\n"
                    "Щоб підключити сповіщення, перейдіть в особистий кабінет на сайті та натисніть «Підключити Telegram».",
                    parse_mode="Markdown",
                )

        async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle /stop command — deactivate notifications."""
            chat_id = update.effective_chat.id
            from apps.notifications.models import TelegramProfile
            updated = TelegramProfile.objects.filter(chat_id=chat_id).update(is_active=False)
            if updated:
                await update.message.reply_text("🔕 Сповіщення вимкнено. Щоб увімкнути знову — /start.")
            else:
                await update.message.reply_text("Профіль не знайдено.")

        async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle /status command."""
            chat_id = update.effective_chat.id
            from apps.notifications.models import TelegramProfile
            try:
                profile = TelegramProfile.objects.select_related("user").get(chat_id=chat_id)
                status_text = "✅ активні" if profile.is_active else "🔕 вимкнені"
                await update.message.reply_text(
                    f"📊 *Статус сповіщень:* {status_text}\n"
                    f"👤 Акаунт: {profile.user.email}",
                    parse_mode="Markdown",
                )
            except TelegramProfile.DoesNotExist:
                await update.message.reply_text("Акаунт не підключено. Використайте /start з токеном.")

        app = Application.builder().token(bot_token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("stop", stop_cmd))
        app.add_handler(CommandHandler("status", status_cmd))

        logger.info("Bot started polling...")
        await app.run_polling(allowed_updates=Update.ALL_TYPES)
