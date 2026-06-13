from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Додати новий моніторинг', callback_data='new_query')],
        [InlineKeyboardButton(text='Керувати Instagram моніторингами', callback_data='insta_menu')],
    ])


def get_add_new_or_edit_query_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Додати новий моніторинг', callback_data='new_query')],
        [InlineKeyboardButton(text='Керувати поточними моніторингами', callback_data='edit_queries')],
        [InlineKeyboardButton(text='Керувати Instagram моніторингами', callback_data='insta_menu')],
    ])


def get_add_new_query_menu_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Додати OLX моніторинг з текстом запиту', callback_data='query_by_text')],
        [InlineKeyboardButton(text='Додати OLX/Rieltor моніторинг з URL', callback_data='query_by_url')],
    ])


def get_edit_menu_inline_keyboard(checker_queries):
    buttons = []
    for query in checker_queries:
        sign = '✅' if query.is_active else '🚫'
        buttons.append([
            InlineKeyboardButton(
                text=f'{sign} {query.query_name}',
                callback_data=f'query_edit_{query.pk}',
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_query_edit_inline_keyboard(query_id, is_active):
    activate = '✅ Активувати'
    deactivate = '🚫 Деактивувати'
    delete = '❌ Видалити'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=activate if not is_active else deactivate,
            callback_data=f'query_activate_{query_id}',
        )],
        [InlineKeyboardButton(text=delete, callback_data=f'query_delete_{query_id}')],
    ])


def get_instagram_menu_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Додати Instagram username', callback_data='insta_add')],
        [InlineKeyboardButton(text='Керувати Instagram usernames', callback_data='insta_edit')],
    ])


def get_instagram_edit_menu_inline_keyboard(users):
    buttons = []
    for subscription in users:
        sign = '✅' if subscription.is_active else '🚫'
        buttons.append([
            InlineKeyboardButton(
                text=f'{sign} @{subscription.observed_user.username}',
                callback_data=f'insta_user_edit_{subscription.pk}',
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_instagram_user_edit_inline_keyboard(user_id, is_active):
    activate = '✅ Активувати'
    deactivate = '🚫 Деактивувати'
    delete = '❌ Видалити'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=activate if not is_active else deactivate,
            callback_data=f'insta_user_toggle_{user_id}',
        )],
        [InlineKeyboardButton(text=delete, callback_data=f'insta_user_delete_{user_id}')],
    ])
