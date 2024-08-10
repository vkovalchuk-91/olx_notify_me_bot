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
