import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.telegram_bot.handlers import main_router, set_commands

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run Telegram bot polling'

    def handle(self, *args, **options):
        if not settings.TELEGRAM_TOKEN:
            self.stderr.write('TELEGRAM_TOKEN is not configured')
            return
        asyncio.run(self._run_bot())

    async def _run_bot(self):
        bot = Bot(
            token=settings.TELEGRAM_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dispatcher = Dispatcher()
        dispatcher.include_router(main_router)
        await set_commands(bot)
        logger.info('Starting Telegram bot polling...')
        await dispatcher.start_polling(bot)
