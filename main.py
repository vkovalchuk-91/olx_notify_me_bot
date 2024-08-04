import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.handlers import main_router

# Bot token can be obtained via https://t.me/BotFather
TOKEN = "7303853478:AAGfhzzyiBWesLXG1mEanMucQJwECUBoxRk"

# All handlers should be attached to the Router (or Dispatcher)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def main() -> None:
    # And the run events dispatching
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_new_ads, "interval", seconds=30)
    scheduler.start()
    dp.include_router(main_router)
    await dp.start_polling(bot)


async def check_new_ads():
    await bot.send_message(396264878, "Повідомлення кожні 30 секунд", parse_mode=ParseMode.HTML)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
