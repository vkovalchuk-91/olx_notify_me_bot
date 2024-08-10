from aiogram import html
from aiogram.enums import ParseMode

from app.db_operations import get_all_active_checker_queries, get_all_found_ads, create_new_found_ad, \
    update_found_ad_is_active
from app.parsing import parse


async def check_new_ads(bot):
    active_checker_queries = await get_all_active_checker_queries()
    for query in active_checker_queries:
        saved_in_db_ads = await get_all_found_ads(query['query_id'])
        saved_in_db_ads_urls = [ad_in_db['ad_url'] for ad_in_db in saved_in_db_ads]
        # Словник, щоб шукати оголошення по URL які вже колись були в базі й стали неактивними, але зараз знову
        # з'явилися в пошуку, ad_id для оновлення статусу is_active=0 саме для цього користувача
        saved_in_db_deactivated_ads = {ad['ad_url']: ad['ad_id'] for ad in saved_in_db_ads if ad['is_active'] == 0}
        saved_in_db_deactivated_urls = list(saved_in_db_deactivated_ads.keys())

        parsed_ads = parse(query['query_url'])
        parsed_ads_urls = [ad['ad_url'] for ad in parsed_ads]

        for parsed_ad in parsed_ads:
            if parsed_ad['ad_url'] not in saved_in_db_ads_urls:  # Відправляємо повідомлення при появі нових оголошень
                await create_new_found_ad(query['query_id'], parsed_ad['ad_url'], parsed_ad['ad_description'],
                                          parsed_ad['ad_price'], parsed_ad['currency'])
                await bot.send_message(query['user_telegram_id'],
                                       f"{html.bold("Додане нове оголошення!")}\n"
                                       f"{html.bold("Запит: ")}{query['query_name']}\n"
                                       f"{html.bold("Опис: ")}{parsed_ad['ad_description']}\n"
                                       f"{html.bold("Ціна: ")}{parsed_ad['ad_price']} {parsed_ad['currency']}\n"
                                       f"{html.bold("URL: ")}{parsed_ad['ad_url']}",
                                       parse_mode=ParseMode.HTML)
            elif parsed_ad['ad_url'] in saved_in_db_deactivated_urls:  # Перевіряємо чи було щойно зпарсяне
                # повідомлення в базі зі статусом is_active=0
                ad_id = saved_in_db_deactivated_ads[parsed_ad['ad_url']]
                await update_found_ad_is_active(ad_id, True)
                await bot.send_message(query['user_telegram_id'],
                                       f"{html.bold("Оголошення стало знову активним!")}\n"
                                       f"{html.bold("Запит: ")}{query['query_name']}\n"
                                       f"{html.bold("Опис: ")}{parsed_ad['ad_description']}\n"
                                       f"{html.bold("Ціна: ")}{parsed_ad['ad_price']} {parsed_ad['currency']}\n"
                                       f"{html.bold("URL: ")}{parsed_ad['ad_url']}",
                                       parse_mode=ParseMode.HTML)

        # Деактивуємо оголошення, які вже не шукаються при парсингу
        for ad_in_db in saved_in_db_ads:
            if ad_in_db['ad_url'] not in parsed_ads_urls and ad_in_db['is_active'] == 1:
                await update_found_ad_is_active(ad_in_db['ad_id'], False)