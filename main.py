import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db_operations import get_all_active_checker_queries, initialize_db, get_all_found_ads, \
    update_found_ad_is_active, create_new_found_ad
from app.handlers import main_router
from app.parsing import parse

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
    await initialize_db()
    await dp.start_polling(bot)


async def check_new_ads():
    active_checker_queries = await get_all_active_checker_queries()
    for query in active_checker_queries:
        saved_in_db_ads = await get_all_found_ads(query['query_id'])
        saved_in_db_ads_dictionary = {ad['ad_url']: [ad['is_active'], ad['ad_id']] for ad in saved_in_db_ads}
        saved_in_db_ads_urls = list(saved_in_db_ads_dictionary.keys())

        parsed_ads = parse(query['query_url'])
        parsed_ads_urls = (ad['ad_url'] for ad in parsed_ads)

        for parsed_ad in parsed_ads:
            print(parsed_ad)
            if parsed_ad['ad_url'] not in saved_in_db_ads_urls:
                await create_new_found_ad(query['query_id'], parsed_ad['ad_url'], parsed_ad['ad_description'],
                                          parsed_ad['ad_price'], parsed_ad['currency'])
                await bot.send_message(query['user_telegram_id'], str(parsed_ad), parse_mode=ParseMode.HTML)
            elif saved_in_db_ads_dictionary[parsed_ad['ad_url']][0] == 0:
                await update_found_ad_is_active(saved_in_db_ads_dictionary[parsed_ad['ad_url']][1], True)
                await bot.send_message(query['user_telegram_id'], f"Оголошення стало знову активним\n" + str(parsed_ad),
                                       parse_mode=ParseMode.HTML)

        for ad_in_db in saved_in_db_ads:
            if ad_in_db['ad_url'] not in parsed_ads_urls and ad_in_db['is_active'] == 1:
                await update_found_ad_is_active(ad_in_db['ad_id'], False)

    # logging.info(ads)
    # await bot.send_message(396264878, str(ads[0]), parse_mode=ParseMode.HTML)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
