import asyncio
import logging

from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BotCommand, BotCommandScopeDefault, CallbackQuery, Message

from notify_bot.context import AppContext
from notify_bot.keyboards import (
    get_add_new_or_edit_query_keyboard,
    get_add_olx_query_menu_inline_keyboard,
    get_edit_menu_inline_keyboard,
    get_instagram_edit_menu_inline_keyboard,
    get_instagram_menu_inline_keyboard,
    get_instagram_user_edit_inline_keyboard,
    get_olx_menu_keyboard,
    get_query_edit_inline_keyboard,
    get_rieltor_menu_keyboard,
    get_start_keyboard,
)
from notify_bot.services import MonitorService
from notify_bot.tasks import initialize_query_ads

logger = logging.getLogger(__name__)
user_router = Router(name='user')

SOURCE_LABELS = {
    'olx': 'OLX',
    'rieltor': 'Rieltor.ua',
}


class AddNewCheckerQueryByURL(StatesGroup):
    query_name = State()
    query_url = State()


class AddNewCheckerQueryByQueryText(StatesGroup):
    query_text = State()


class AddInstagramObservedUser(StatesGroup):
    username = State()


def get_context(message_or_callback) -> AppContext:
    return message_or_callback.bot.app_context


async def _show_insta_for_edit(callback: CallbackQuery, user_id: int) -> None:
    ctx = get_context(callback)
    users = await ctx.insta_service.get_subscriptions_for_management(user_id)
    if users:
        text = (
            'Оберіть Instagram моніторинг для редагування:\n'
            '✅ - активний моніторинг\n🚫 - деактивований моніторинг'
        )
    else:
        text = 'У вас немає Instagram моніторингів'
    await callback.message.answer(text, reply_markup=get_instagram_edit_menu_inline_keyboard(users))


async def _show_queries_for_edit(callback: CallbackQuery, user_id: int, source: str) -> None:
    ctx = get_context(callback)
    queries = await ctx.monitor_service.get_checker_queries_for_user(user_id, source=source)
    label = SOURCE_LABELS[source]
    if queries:
        text = (
            f'Оберіть {label} моніторинг для редагування:\n'
            '✅ - активний моніторинг\n🚫 - деактивований моніторинг'
        )
    else:
        text = f'У вас немає {label} моніторингів'
    await callback.message.answer(text, reply_markup=get_edit_menu_inline_keyboard(queries, source))


async def set_commands(bot):
    commands = [
        BotCommand(command='start', description='Стартове меню'),
        BotCommand(command='about', description='Про проект'),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


@user_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await _send_main_menu(message)


@user_router.callback_query(F.data == 'main_menu')
async def main_menu_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    await _send_main_menu(callback.message, callback.from_user)


async def _send_main_menu(message: Message, from_user=None) -> None:
    user = from_user or message.from_user
    ctx = get_context(message)
    is_admin = ctx.is_admin(user.id)
    existing_user = await ctx.monitor_service.is_user_registered(user.id)
    db_user = await ctx.monitor_service.register_telegram_user(user, is_admin=is_admin)
    is_admin = ctx.is_admin(user.id, db_user)

    if existing_user:
        stats = await ctx.monitor_service.get_user_stats(user.id)
        text = f"Вітаю, {html.bold(user.full_name)}!\nКількість активних моніторингів {stats['active']}"
        if stats['inactive'] > 0:
            text += f" (+{stats['inactive']} - деактивовано)"
        await message.answer(text, reply_markup=get_add_new_or_edit_query_keyboard(is_admin))
    else:
        await message.answer(
            f"Вітаю, {html.bold(user.full_name)}!\nУ вас відсутні моніторинги",
            reply_markup=get_start_keyboard(),
        )


@user_router.message(Command('about'))
async def command_about_handler(message: Message) -> None:
    await message.answer(
        'Проект створено для перевірки й оповіщення щодо нових OLX/Rieltor оголошень '
        'та Instagram контенту через Telegram.',
        parse_mode='Markdown',
    )


@user_router.callback_query(F.data == 'olx_menu')
async def olx_menu_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    await callback.message.answer('OLX моніторинги:', reply_markup=get_olx_menu_keyboard())


@user_router.callback_query(F.data == 'rieltor_menu')
async def rieltor_menu_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    await callback.message.answer('Rieltor.ua моніторинги:', reply_markup=get_rieltor_menu_keyboard())


@user_router.callback_query(F.data == 'new_query_olx')
async def command_add_new_olx_query_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    await callback.message.answer(
        'Оберіть спосіб додавання нового OLX моніторингу:',
        reply_markup=get_add_olx_query_menu_inline_keyboard(),
    )


@user_router.callback_query(F.data == 'new_query_rieltor')
async def command_add_new_rieltor_query_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer('')
    await state.update_data(source='rieltor')
    await state.set_state(AddNewCheckerQueryByURL.query_name)
    await callback.message.answer('Введіть назву Rieltor.ua моніторингу (відображатиметься в переліку):')


@user_router.callback_query(F.data == 'edit_queries_olx')
async def command_edit_olx_queries_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    await _show_queries_for_edit(callback, callback.from_user.id, 'olx')


@user_router.callback_query(F.data == 'edit_queries_rieltor')
async def command_edit_rieltor_queries_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    await _show_queries_for_edit(callback, callback.from_user.id, 'rieltor')


@user_router.callback_query(F.data.startswith('query_edit'))
async def command_query_edit_handler(callback: CallbackQuery) -> None:
    ctx = get_context(callback)
    query_id = int(callback.data.split('_')[-1])
    checker_query = await ctx.monitor_service.get_checker_query(query_id)
    await callback.answer('')
    status = '✅' if checker_query.is_active else '🚫'
    await callback.message.answer(
        f'{html.bold("Назва моніторингу:")} "{checker_query.query_name}" ({status})',
        reply_markup=get_query_edit_inline_keyboard(query_id, checker_query.is_active, checker_query.source),
    )


@user_router.callback_query(F.data.startswith('query_activate'))
async def command_query_activate_handler(callback: CallbackQuery) -> None:
    ctx = get_context(callback)
    query_id = int(callback.data.split('_')[-1])
    checker_query = await ctx.monitor_service.toggle_query_active(query_id)
    await callback.answer(
        f'{"Активовано" if checker_query.is_active else "Деактивовано"} моніторинг "{checker_query.query_name}"'
    )
    await _show_queries_for_edit(callback, callback.from_user.id, checker_query.source)


@user_router.callback_query(F.data.startswith('query_delete'))
async def command_query_delete_handler(callback: CallbackQuery) -> None:
    ctx = get_context(callback)
    query_id = int(callback.data.split('_')[-1])
    checker_query = await ctx.monitor_service.get_checker_query(query_id)
    await ctx.monitor_service.soft_delete_query(query_id)
    await callback.answer(f'Видалено моніторинг "{checker_query.query_name}"')
    await _show_queries_for_edit(callback, callback.from_user.id, checker_query.source)


@user_router.callback_query(F.data == 'query_by_url_olx')
async def add_query_by_url_olx_step0(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.update_data(source='olx')
    await state.set_state(AddNewCheckerQueryByURL.query_name)
    await callback.message.answer('Введіть назву запиту (ця назва буде відображатися в переліку запитів):')


@user_router.callback_query(F.data == 'query_by_url_rieltor')
async def add_query_by_url_rieltor_step0(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.update_data(source='rieltor')
    await state.set_state(AddNewCheckerQueryByURL.query_name)
    await callback.message.answer('Введіть назву Rieltor.ua моніторингу (відображатиметься в переліку):')


@user_router.callback_query(F.data == 'query_by_url')
async def add_query_by_url_step1(callback: CallbackQuery, state: FSMContext):
    await add_query_by_url_olx_step0(callback, state)


@user_router.message(AddNewCheckerQueryByURL.query_name)
async def add_query_by_url_step2(message: Message, state: FSMContext):
    await state.update_data(query_name=message.text)
    await state.set_state(AddNewCheckerQueryByURL.query_url)
    data = await state.get_data()
    if data.get('source') == 'rieltor':
        await message.answer('Введіть URL запиту rieltor.ua:')
    else:
        await message.answer('Введіть URL запиту OLX:')


@user_router.message(AddNewCheckerQueryByURL.query_url)
async def add_query_by_url_step3(message: Message, state: FSMContext):
    ctx = get_context(message)
    data = await state.get_data()
    await state.clear()
    query_url = message.text.strip()

    if await ctx.monitor_service.query_url_exists(message.from_user.id, query_url):
        if await ctx.monitor_service.query_url_is_deleted(message.from_user.id, query_url):
            await ctx.monitor_service.restore_query(message.from_user.id, query_url)
            await message.answer(f'Відновлено з видалених моніторинг з URL запиту: {html.bold(query_url)}')
        else:
            await message.answer(f'В переліку вже існує моніторинг з URL запиту: {html.bold(query_url)}')
        return

    if not MonitorService.is_supported_ads_url(query_url):
        await message.answer('Підтримуються тільки сервіси OLX та rieltor.ua')
        return

    expected_source = data.get('source', 'olx')
    actual_source = 'rieltor' if 'rieltor.ua/' in query_url else 'olx'
    if actual_source != expected_source:
        label = SOURCE_LABELS[expected_source]
        await message.answer(f'Цей URL не належить до {label}. Перевірте посилання.')
        return

    query = await ctx.monitor_service.create_query(message.from_user.id, data['query_name'], query_url, False)
    asyncio.create_task(initialize_query_ads(ctx.bot, ctx.db, ctx.monitor_service, query.id))
    await message.answer(
        f'Додано моніторинг: {html.bold(data["query_name"])}\n'
        f'Первинна перевірка запущена у фоні.\nURL запиту: {query_url}'
    )


@user_router.callback_query(F.data == 'query_by_text')
async def add_query_by_text_step1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.set_state(AddNewCheckerQueryByQueryText.query_text)
    await callback.message.answer('Введіть текст запиту:')


@user_router.message(AddNewCheckerQueryByQueryText.query_text)
async def add_query_by_text_step2(message: Message, state: FSMContext):
    ctx = get_context(message)
    await state.clear()
    query_text = message.text.strip()
    query_url = MonitorService.transform_query_text_to_olx_url(query_text)

    if await ctx.monitor_service.query_url_exists(message.from_user.id, query_url):
        if await ctx.monitor_service.query_url_is_deleted(message.from_user.id, query_url):
            await ctx.monitor_service.restore_query(message.from_user.id, query_url)
            await message.answer(f'Відновлено з видалених моніторинг з URL запиту: {html.bold(query_url)}')
        else:
            await message.answer(f'В переліку вже існує моніторинг з URL запиту: {html.bold(query_url)}')
        return

    query = await ctx.monitor_service.create_query(message.from_user.id, query_text, query_url, False)
    asyncio.create_task(initialize_query_ads(ctx.bot, ctx.db, ctx.monitor_service, query.id))
    await message.answer(
        f'Додано моніторинг: {html.bold(query_text)}\n'
        f'Первинна перевірка запущена у фоні.\nURL запиту: {query_url}'
    )


@user_router.callback_query(F.data == 'insta_menu')
async def instagram_menu_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    await callback.message.answer('Instagram моніторинги:', reply_markup=get_instagram_menu_inline_keyboard())


@user_router.callback_query(F.data == 'insta_add')
async def instagram_add_step1(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer('')
    await state.set_state(AddInstagramObservedUser.username)
    await callback.message.answer('Введіть Instagram username (без @ або з @):')


@user_router.message(AddInstagramObservedUser.username)
async def instagram_add_step2(message: Message, state: FSMContext) -> None:
    ctx = get_context(message)
    await state.clear()
    user, created, restored = await ctx.insta_service.add_observed_user(message.text, message.from_user.id)
    if created:
        await message.answer(f'Додано Instagram моніторинг: @{html.bold(user.username)}')
    elif restored:
        await message.answer(f'Відновлено Instagram моніторинг: @{html.bold(user.username)}')
    else:
        await message.answer(f'Instagram моніторинг @{html.bold(user.username)} оновлено')


@user_router.callback_query(F.data == 'insta_edit')
async def instagram_edit_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    await _show_insta_for_edit(callback, callback.from_user.id)


@user_router.callback_query(F.data.startswith('insta_user_edit_'))
async def instagram_user_edit_handler(callback: CallbackQuery) -> None:
    ctx = get_context(callback)
    user_id = int(callback.data.split('_')[-1])
    subscription = await ctx.insta_service.get_subscription(user_id, callback.from_user.id)
    await callback.answer('')
    if not subscription:
        await callback.message.answer('Instagram моніторинг не знайдено')
        return
    status = '✅' if subscription.is_active else '🚫'
    await callback.message.answer(
        f'{html.bold("Instagram моніторинг:")} @{subscription.observed_user.username} ({status})',
        reply_markup=get_instagram_user_edit_inline_keyboard(subscription.id, subscription.is_active),
    )


@user_router.callback_query(F.data.startswith('insta_user_toggle_'))
async def instagram_user_toggle_handler(callback: CallbackQuery) -> None:
    ctx = get_context(callback)
    user_id = int(callback.data.split('_')[-1])
    subscription = await ctx.insta_service.toggle_subscription_active(user_id, callback.from_user.id)
    await callback.answer(
        f'{"Активовано" if subscription.is_active else "Деактивовано"} '
        f'Instagram моніторинг @{subscription.observed_user.username}'
    )
    await _show_insta_for_edit(callback, callback.from_user.id)


@user_router.callback_query(F.data.startswith('insta_user_delete_'))
async def instagram_user_delete_handler(callback: CallbackQuery) -> None:
    ctx = get_context(callback)
    user_id = int(callback.data.split('_')[-1])
    subscription = await ctx.insta_service.soft_delete_subscription(user_id, callback.from_user.id)
    await callback.answer(f'Видалено Instagram моніторинг @{subscription.observed_user.username}')
    await _show_insta_for_edit(callback, callback.from_user.id)
