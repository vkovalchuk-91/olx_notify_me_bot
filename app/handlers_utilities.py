import re

import injector
from aiogram import html
from aiogram.types import User

from app.db.db_interface import DatabaseInterface
from app.injector_config import BotModule
from app.parsers import parser_olx

db = injector.Injector([BotModule]).get(DatabaseInterface)


class IncorrectURL(Exception):
    def __init__(self, message="Введений вами URL є некоректним"):
        self.message = message
        super().__init__(self.message)


async def get_message_text_for_existing_user(user: User):
    active_checker_queries = await db.count_active_checker_queries(user.id)
    inactive_checker_queries = await db.count_inactive_checker_queries(user.id)
    queries_count_string = f"Кількість активних моніторингів {active_checker_queries}"
    if inactive_checker_queries > 0:
        queries_count_string += f" (+{inactive_checker_queries} - деактивовано)"
    return (f"Вітаю, {html.bold(user.full_name)}!"
            f"\n{queries_count_string}")


async def get_message_text_for_new_user(user: User):
    return (f"Вітаю, {html.bold(user.full_name)}!"
            f"\nУ вас відсутні моніторинги")


async def transform_query_text_to_olx_url(text):
    url_prefix = "https://www.olx.ua/uk/list/q-"

    cleaned_text = text.replace(' ', '-')
    cleaned_text = re.sub(r'[^a-zA-Zа-яА-ЯёЁіїІЇґҐєЄ0-9\.\'\"!\(\)\*\-+,:;=&\^#\$%@-]', '', cleaned_text)
    cleaned_text = cleaned_text.replace('%', '%25')
    cleaned_text = cleaned_text.replace('*', '%2A')
    cleaned_text = cleaned_text.replace('+', '%2B')
    cleaned_text = cleaned_text.replace(',', '%2C')
    cleaned_text = cleaned_text.replace(':', '%3A')
    cleaned_text = cleaned_text.replace(';', '%3B')
    cleaned_text = cleaned_text.replace('=', '%3D')
    cleaned_text = cleaned_text.replace('^', '%5E')
    cleaned_text = cleaned_text.replace('#', '%23')
    cleaned_text = cleaned_text.replace('$', '%24')
    cleaned_text = cleaned_text.replace('&', '%26')
    cleaned_text = cleaned_text.replace('@', '%40')
    return url_prefix + cleaned_text + '/'


async def get_data_from_and_clean_state(state):
    data = await state.get_data()
    await state.clear()
    return data


async def get_olx_parsed_ads(query_url):
    olx_queries_with_unique_ads = await parser_olx.get_parsed_ads({1: query_url})
    parsed_ads = None
    if 1 in olx_queries_with_unique_ads:
        parsed_ads = olx_queries_with_unique_ads[1]
    return parsed_ads


async def save_found_ads_and_inform_user(query_name, query_url, message, parsed_ads, service_title):
    if parsed_ads:
        query_id = await db.create_new_checker_query(
            message.from_user.id,
            query_name,
            query_url
        )
        for parsed_ad in parsed_ads:
            await db.create_new_found_ad(
                query_id,
                parsed_ad['ad_url'],
                parsed_ad['ad_description'],
                parsed_ad['ad_price'],
                parsed_ad['currency']
            )

        await message.answer(f'Додано моніторинг: {html.bold(query_name)}\n'
                             f'Знайдено {len(parsed_ads)} поточних оголошень\n'
                             f'URL запиту: {query_url}')
    else:
        await message.answer(f'Введений вами URL не містить {service_title} оголошень')


async def check_and_inform_user_for_deleted_or_existing_query(query_url, message):
    if await db.check_query_url_is_deleted(message.from_user.id, query_url):  # Відновити раніше видалений моніторинг
        query_id = await db.get_user_checker_query_id_by_url(message.from_user.id, query_url)
        await db.set_checker_query_non_deleted_and_active(query_id)
        await message.answer(f'Відновлено з видалених моніторинг з URL запиту: {html.bold(query_url)}')
    else:
        await message.answer(f'В переліку вже існує моніторинг з URL запиту: {html.bold(query_url)}')
