import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from functools import partial

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from app.check_new_ads_service import check_new_ads
from app.handlers import main_router, set_commands

# Loading variables from the .env file
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Bot token can be obtained via https://t.me/BotFather
USE_AIOHTTP = os.getenv("USE_AIOHTTP", "false").lower() in ["True", "true", "1", "t", "y", "yes"]
REQUEST_INTERVAL_MINUTES = int(os.getenv("REQUEST_INTERVAL_MINUTES"))
INITIAL_REQUEST_DELAY_SECONDS = int(os.getenv("INITIAL_REQUEST_DELAY_SECONDS"))


# All handlers should be attached to the Router (or Dispatcher)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dispatcher = Dispatcher()


async def main() -> None:
    # And the run events dispatching
    scheduler = AsyncIOScheduler()
    scheduler.add_job(partial(check_new_ads, bot, USE_AIOHTTP),
                      "interval", minutes=REQUEST_INTERVAL_MINUTES)
    scheduler.add_job(partial(check_new_ads, bot, USE_AIOHTTP),
                      "date", run_date=datetime.now() + timedelta(seconds=INITIAL_REQUEST_DELAY_SECONDS))
    scheduler.start()
    await set_commands(bot)
    dispatcher.include_router(main_router)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
