import asyncio
import logging
import sys
from datetime import datetime, timedelta
from functools import partial

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.check_new_ads_service import check_new_ads
from app.db_operations import initialize_db
from app.handlers import main_router, set_commands

# Bot token can be obtained via https://t.me/BotFather
TOKEN = "7303853478:AAGfhzzyiBWesLXG1mEanMucQJwECUBoxRk"

USE_AIOHTTP = False

# All handlers should be attached to the Router (or Dispatcher)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def main() -> None:
    # And the run events dispatching
    scheduler = AsyncIOScheduler()
    scheduler.add_job(partial(check_new_ads, bot, USE_AIOHTTP), "interval", minutes=3)
    scheduler.add_job(partial(check_new_ads, bot, USE_AIOHTTP), "date", run_date=datetime.now() + timedelta(seconds=1))
    scheduler.start()
    await initialize_db()
    await set_commands(bot)
    dp.include_router(main_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
