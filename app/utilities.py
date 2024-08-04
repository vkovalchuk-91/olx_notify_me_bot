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
