from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='OLX моніторинги', callback_data='olx_menu')],
        [InlineKeyboardButton(text='Rieltor.ua моніторинги', callback_data='rieltor_menu')],
        [InlineKeyboardButton(text='Instagram моніторинги', callback_data='insta_menu')],
    ])


def get_add_new_or_edit_query_keyboard(is_admin: bool = False):
    rows = [
        [InlineKeyboardButton(text='OLX моніторинги', callback_data='olx_menu')],
        [InlineKeyboardButton(text='Rieltor.ua моніторинги', callback_data='rieltor_menu')],
        [InlineKeyboardButton(text='Instagram моніторинги', callback_data='insta_menu')],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text='Адмін-панель', callback_data='admin_menu')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_olx_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Додати новий OLX моніторинг', callback_data='new_query_olx')],
        [InlineKeyboardButton(text='Керувати OLX моніторингами', callback_data='edit_queries_olx')],
        [InlineKeyboardButton(text='⬅️ Головне меню', callback_data='main_menu')],
    ])


def get_rieltor_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Додати новий Rieltor.ua моніторинг', callback_data='new_query_rieltor')],
        [InlineKeyboardButton(text='Керувати Rieltor.ua моніторингами', callback_data='edit_queries_rieltor')],
        [InlineKeyboardButton(text='⬅️ Головне меню', callback_data='main_menu')],
    ])


def get_instagram_menu_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Додати новий Instagram моніторинг', callback_data='insta_add')],
        [InlineKeyboardButton(text='Керувати Instagram моніторингами', callback_data='insta_edit')],
        [InlineKeyboardButton(text='⬅️ Головне меню', callback_data='main_menu')],
    ])


def get_add_olx_query_menu_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Додати OLX моніторинг з текстом запиту', callback_data='query_by_text')],
        [InlineKeyboardButton(text='Додати OLX моніторинг з URL', callback_data='query_by_url_olx')],
        [InlineKeyboardButton(text='⬅️ Назад', callback_data='olx_menu')],
    ])


def get_edit_menu_inline_keyboard(checker_queries, source: str):
    buttons = []
    for query in checker_queries:
        sign = '✅' if query.is_active else '🚫'
        buttons.append([
            InlineKeyboardButton(
                text=f'{sign} {query.query_name}',
                callback_data=f'query_edit_{query.id}',
            )
        ])
    back_callback = 'olx_menu' if source == 'olx' else 'rieltor_menu'
    buttons.append([InlineKeyboardButton(text='⬅️ Назад', callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_query_edit_inline_keyboard(query_id, is_active, source: str):
    activate = '✅ Активувати'
    deactivate = '🚫 Деактивувати'
    delete = '❌ Видалити'
    edit_callback = f'edit_queries_{source}'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=activate if not is_active else deactivate,
            callback_data=f'query_activate_{query_id}',
        )],
        [InlineKeyboardButton(text=delete, callback_data=f'query_delete_{query_id}')],
        [InlineKeyboardButton(text='⬅️ До списку', callback_data=edit_callback)],
    ])


def get_instagram_edit_menu_inline_keyboard(users):
    buttons = []
    for subscription in users:
        sign = '✅' if subscription.is_active else '🚫'
        buttons.append([
            InlineKeyboardButton(
                text=f'{sign} @{subscription.observed_user.username}',
                callback_data=f'insta_user_edit_{subscription.id}',
            )
        ])
    buttons.append([InlineKeyboardButton(text='⬅️ Назад', callback_data='insta_menu')])
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
        [InlineKeyboardButton(text='⬅️ До списку', callback_data='insta_edit')],
    ])


def get_admin_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Статистика', callback_data='admin_stats')],
        [InlineKeyboardButton(text='Користувачі', callback_data='admin_users')],
        [InlineKeyboardButton(text='Всі моніторинги', callback_data='admin_queries')],
        [InlineKeyboardButton(text='Останні оголошення', callback_data='admin_ads')],
        [InlineKeyboardButton(text='Логи', callback_data='admin_logs')],
        [InlineKeyboardButton(text='Запустити OLX/Rieltor', callback_data='admin_run_ads')],
        [InlineKeyboardButton(text='Запустити Instagram', callback_data='admin_run_insta')],
        [InlineKeyboardButton(text='⬅️ Головне меню', callback_data='main_menu')],
    ])


def get_admin_users_keyboard(users):
    buttons = []
    for user in users:
        sign = '✅' if user.is_active else '🚫'
        admin_mark = ' 👑' if user.is_admin else ''
        label = user.full_name or user.username or str(user.user_telegram_id)
        buttons.append([
            InlineKeyboardButton(
                text=f'{sign}{admin_mark} {label}',
                callback_data=f'admin_user_{user.user_telegram_id}',
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_logs_keyboard(page: int, total_pages: int):
    buttons = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text='◀️ Назад', callback_data=f'admin_logs_page_{page - 1}'))
    nav.append(InlineKeyboardButton(text=f'{page + 1}/{total_pages}', callback_data='admin_logs_noop'))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text='Вперед ▶️', callback_data=f'admin_logs_page_{page + 1}'))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton(text='⬅️ Адмін-панель', callback_data='admin_menu')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_user_edit_keyboard(user_telegram_id: int, is_active: bool, is_admin: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text='✅ Активувати' if not is_active else '🚫 Деактивувати',
            callback_data=f'admin_toggle_active_{user_telegram_id}',
        )],
        [InlineKeyboardButton(
            text='Зняти адміна' if is_admin else 'Зробити адміном',
            callback_data=f'admin_toggle_admin_{user_telegram_id}',
        )],
    ])
