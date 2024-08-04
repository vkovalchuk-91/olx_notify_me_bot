from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup


def get_add_new_query_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Додати новий моніторинг')]],
                               resize_keyboard=True,
                               input_field_placeholder='Оберіть пункт меню...')


def get_add_new_or_edit_query_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Додати новий моніторинг')],
                                         [KeyboardButton(text='Керувати поточними моніторингами')]],
                               resize_keyboard=True,
                               input_field_placeholder='Оберіть пункт меню...')


def get_add_new_query_menu_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Додати моніторинг з текстом запиту', callback_data='query_by_text')],
        [InlineKeyboardButton(text='Додати моніторинг з URL запиту', callback_data='query_by_url')]])
