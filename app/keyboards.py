from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Додати новий моніторинг', callback_data='new_query')]])


def get_add_new_or_edit_query_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Додати новий моніторинг', callback_data='new_query')],
        [InlineKeyboardButton(text='Керувати поточними моніторингами', callback_data='edit_queries')]])


def get_add_new_query_menu_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Додати моніторинг з текстом запиту', callback_data='query_by_text')],
        [InlineKeyboardButton(text='Додати моніторинг з URL запиту', callback_data='query_by_url')]])


def get_edit_menu_inline_keyboard(checker_queries):
    active_sign = "✅"  # Активний стан
    inactive_sign = "🚫"  # Неактивний стан
    buttons = []
    for query in checker_queries:
        buttons.append([InlineKeyboardButton(
            text=f"{active_sign if query['is_active'] == 1 else inactive_sign} {query['query_name']}",
            callback_data=f"query_edit_{str(query['query_id'])}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_query_edit_inline_keyboard(query_id, is_active):
    activate = "✅ Активувати"  # Активний стан
    deactivate = "🚫 Деактивувати"  # Неактивний стан
    delete = "❌ Видалити"  # Кнопка видалення
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{activate if is_active == 0 else deactivate}",
                              callback_data=f"query_activate_{query_id}")],
        [InlineKeyboardButton(text=delete, callback_data=f"query_delete_{query_id}")]
    ])
