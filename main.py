import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from notify_bot.admin_handlers import admin_router
from notify_bot.config import Settings
from notify_bot.context import AppContext
from notify_bot.database import Database
from notify_bot.handlers import set_commands, user_router
from notify_bot.scheduler import run_scheduler
from notify_bot.services import InstaMonitorService, MonitorService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)
logger = logging.getLogger(__name__)


async def main():
    settings = Settings.load()
    db = await Database(settings).connect()
    bot = Bot(
        token=settings.telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    bot.app_context = AppContext(
        settings=settings,
        db=db,
        bot=bot,
        monitor_service=MonitorService(db),
        insta_service=InstaMonitorService(db),
    )

    dp = Dispatcher()
    dp.include_router(user_router)
    dp.include_router(admin_router)

    await set_commands(bot)
    scheduler_task = asyncio.create_task(
        run_scheduler(
            bot,
            db,
            settings.request_interval_minutes,
            settings.insta_request_interval_minutes,
        )
    )

    logger.info('Telegram bot started')
    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await db.close()
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
