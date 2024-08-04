import re

from aiogram import html
from aiogram.types import User

from app.db_operations import count_active_checker_queries, count_inactive_checker_queries


def get_message_text_for_existing_user(user: User):
    active_checker_queries = count_active_checker_queries(user.id)
    inactive_checker_queries = count_inactive_checker_queries(user.id)
    queries_count_string = f"Кількість активних моніторингів {active_checker_queries}"
    if inactive_checker_queries > 0:
        queries_count_string += f" (+{inactive_checker_queries} деактивованих моніторингів)"
    return (f"Вітаю, {html.bold(user.full_name)}!"
            f"\n{queries_count_string}")


def get_message_text_for_new_user(user: User):
    return (f"Вітаю, {html.bold(user.full_name)}!"
            f"\nУ вас відсутні моніторинги")


def transform_query_text_to_olx_url(text):
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
    return url_prefix + cleaned_text
