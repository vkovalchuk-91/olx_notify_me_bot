from asgiref.sync import sync_to_async
from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BotCommand, BotCommandScopeDefault, CallbackQuery, Message
from django.conf import settings

from apps.monitors.services import MonitorService
from apps.monitors.tasks import initialize_query_ads_task
from apps.monitors.tasks_logic import InstaMonitorService
from apps.telegram_bot.keyboards import (
    get_add_new_or_edit_query_keyboard,
    get_add_new_query_menu_inline_keyboard,
    get_edit_menu_inline_keyboard,
    get_instagram_edit_menu_inline_keyboard,
    get_instagram_menu_inline_keyboard,
    get_instagram_user_edit_inline_keyboard,
    get_query_edit_inline_keyboard,
    get_start_keyboard,
)

main_router = Router(name='telegram_bot')

register_user = sync_to_async(MonitorService.register_telegram_user, thread_sensitive=False)
generate_web_registration_code = sync_to_async(MonitorService.generate_web_registration_code, thread_sensitive=False)
attach_web_registration_request = sync_to_async(MonitorService.attach_web_registration_request, thread_sensitive=False)
is_user_registered = sync_to_async(MonitorService.is_user_registered, thread_sensitive=False)
get_user_stats = sync_to_async(MonitorService.get_user_stats, thread_sensitive=False)
get_checker_queries_for_user = sync_to_async(MonitorService.get_checker_queries_for_user, thread_sensitive=False)
get_checker_query = sync_to_async(MonitorService.get_checker_query, thread_sensitive=False)
toggle_query_active = sync_to_async(MonitorService.toggle_query_active, thread_sensitive=False)
soft_delete_query = sync_to_async(MonitorService.soft_delete_query, thread_sensitive=False)
query_url_exists = sync_to_async(MonitorService.query_url_exists, thread_sensitive=False)
query_url_is_deleted = sync_to_async(MonitorService.query_url_is_deleted, thread_sensitive=False)
restore_query = sync_to_async(MonitorService.restore_query, thread_sensitive=False)
create_query = sync_to_async(MonitorService.create_query, thread_sensitive=False)
get_instagram_users = sync_to_async(InstaMonitorService.get_subscriptions_for_management, thread_sensitive=False)
get_instagram_user = sync_to_async(InstaMonitorService.get_subscription, thread_sensitive=False)
add_instagram_user = sync_to_async(InstaMonitorService.add_observed_user, thread_sensitive=False)
toggle_instagram_user = sync_to_async(InstaMonitorService.toggle_subscription_active, thread_sensitive=False)
soft_delete_instagram_user = sync_to_async(InstaMonitorService.soft_delete_subscription, thread_sensitive=False)


class AddNewCheckerQueryByURL(StatesGroup):
    query_name = State()
    query_url = State()


class AddNewCheckerQueryByQueryText(StatesGroup):
    query_text = State()


class AddInstagramObservedUser(StatesGroup):
    username = State()


async def set_commands(bot):
    commands = [
        BotCommand(command='start', description='Стартове меню'),
        BotCommand(command='web', description='Код для web-реєстрації'),
        BotCommand(command='about', description='Про проект'),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


@main_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    payload = _get_start_payload(message)
    if payload.startswith('webreg_'):
        await _handle_web_registration_start(message, payload.removeprefix('webreg_'))
        return

    if await is_user_registered(message.from_user.id):
        stats = await get_user_stats(message.from_user.id)
        text = f"Вітаю, {html.bold(message.from_user.full_name)}!\nКількість активних моніторингів {stats['active']}"
        if stats['inactive'] > 0:
            text += f" (+{stats['inactive']} - деактивовано)"
        await message.answer(text, reply_markup=get_add_new_or_edit_query_keyboard())
    else:
        await register_user(message.from_user)
        await message.answer(
            f"Вітаю, {html.bold(message.from_user.full_name)}!\nУ вас відсутні моніторинги",
            reply_markup=get_start_keyboard(),
        )


@main_router.message(Command('about'))
async def command_about_handler(message: Message) -> None:
    await message.answer(
        "Проект створено для перевірки й оповіщення щодо нових OLX/Rieltor оголошень "
        "та Instagram контенту.\nТакож доступний веб-інтерфейс для керування моніторингами.",
        parse_mode='Markdown',
    )


@main_router.message(Command('web'))
async def command_web_registration_handler(message: Message) -> None:
    code = await generate_web_registration_code(message.from_user)
    await message.answer(
        f'{html.bold("Web-реєстрація")}\n'
        f'Telegram ID: {html.code(str(message.from_user.id))}\n'
        f'Код: {html.code(code)}\n\n'
        'Відкрийте сторінку реєстрації на сайті та введіть цей ID і код. '
        'Код діє 15 хвилин.'
    )


async def _handle_web_registration_start(message: Message, token: str) -> None:
    registration_request, error = await attach_web_registration_request(token, message.from_user)
    if error:
        await message.answer(
            'Не вдалося підтвердити web-реєстрацію. '
            'Поверніться на сайт і почніть реєстрацію ще раз.'
        )
        return

    register_url = f'{settings.WEB_REGISTRATION_BASE_URL.rstrip("/")}/register/?token={registration_request.token}'
    await message.answer(
        f'{html.bold("Telegram підтверджено")}\n'
        f'Користувач: {html.bold(message.from_user.full_name)}\n\n'
        f'Поверніться на сайт, щоб створити пароль:\n{register_url}'
    )


def _get_start_payload(message: Message) -> str:
    if not message.text:
        return ''
    parts = message.text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ''


@main_router.callback_query(F.data == 'new_query')
async def command_add_new_query_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    await callback.message.answer(
        'Оберіть спосіб додавання нового OLX/Rieltor моніторингу!',
        reply_markup=get_add_new_query_menu_inline_keyboard(),
    )


@main_router.callback_query(F.data == 'edit_queries')
async def command_edit_queries_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    checker_queries = await get_checker_queries_for_user(callback.from_user.id)
    await callback.message.answer(
        'Оберіть моніторинг для редагування:\n✅ - активний моніторинг\n🚫 - деактивований моніторинг',
        reply_markup=get_edit_menu_inline_keyboard(checker_queries),
    )


@main_router.callback_query(F.data.startswith('query_edit'))
async def command_query_edit_handler(callback: CallbackQuery) -> None:
    query_id = int(callback.data.split('_')[-1])
    checker_query = await get_checker_query(query_id)
    await callback.answer('')
    status = '✅' if checker_query.is_active else '🚫'
    await callback.message.answer(
        f'{html.bold("Назва моніторингу:")} "{checker_query.query_name}" ({status})',
        reply_markup=get_query_edit_inline_keyboard(query_id, checker_query.is_active),
    )


@main_router.callback_query(F.data.startswith('query_activate'))
async def command_query_activate_handler(callback: CallbackQuery) -> None:
    query_id = int(callback.data.split('_')[-1])
    checker_query = await toggle_query_active(query_id)
    await callback.answer(f'{"Активовано" if checker_query.is_active else "Деактивовано"} моніторинг "{checker_query.query_name}"')
    checker_queries = await get_checker_queries_for_user(callback.from_user.id)
    await callback.message.answer(
        'Оберіть моніторинг для редагування:\n✅ - активний моніторинг\n🚫 - деактивований моніторинг',
        reply_markup=get_edit_menu_inline_keyboard(checker_queries),
    )


@main_router.callback_query(F.data.startswith('query_delete'))
async def command_query_delete_handler(callback: CallbackQuery) -> None:
    query_id = int(callback.data.split('_')[-1])
    checker_query = await get_checker_query(query_id)
    await soft_delete_query(query_id)
    await callback.answer(f'Видалено моніторинг "{checker_query.query_name}"')
    checker_queries = await get_checker_queries_for_user(callback.from_user.id)
    await callback.message.answer(
        'Оберіть моніторинг для редагування:\n✅ - активний моніторинг\n🚫 - деактивований моніторинг',
        reply_markup=get_edit_menu_inline_keyboard(checker_queries),
    )


@main_router.callback_query(F.data == 'query_by_url')
async def add_query_by_url_step1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.set_state(AddNewCheckerQueryByURL.query_name)
    await callback.message.answer('Введіть назву запиту (ця назва буде відображатися в переліку запитів):')


@main_router.message(AddNewCheckerQueryByURL.query_name)
async def add_query_by_url_step2(message: Message, state: FSMContext):
    await state.update_data(query_name=message.text)
    await state.set_state(AddNewCheckerQueryByURL.query_url)
    await message.answer('Введіть URL запиту OLX або rieltor.ua:')


@main_router.message(AddNewCheckerQueryByURL.query_url)
async def add_query_by_url_step3(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    query_url = message.text.strip()
    if await query_url_exists(message.from_user.id, query_url):
        if await query_url_is_deleted(message.from_user.id, query_url):
            await restore_query(message.from_user.id, query_url)
            await message.answer(f'Відновлено з видалених моніторинг з URL запиту: {html.bold(query_url)}')
        else:
            await message.answer(f'В переліку вже існує моніторинг з URL запиту: {html.bold(query_url)}')
        return

    if not MonitorService.is_supported_ads_url(query_url):
        await message.answer('Підтримуються тільки сервіси OLX та rieltor.ua')
        return

    query = await create_query(message.from_user.id, data['query_name'], query_url, False)
    initialize_query_ads_task.delay(query.pk)
    await message.answer(
        f'Додано моніторинг: {html.bold(data["query_name"])}\n'
        f'Первинна перевірка запущена у фоні.\nURL запиту: {query_url}'
    )


@main_router.callback_query(F.data == 'query_by_text')
async def add_query_by_text_step1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.set_state(AddNewCheckerQueryByQueryText.query_text)
    await callback.message.answer('Введіть текст запиту:')


@main_router.message(AddNewCheckerQueryByQueryText.query_text)
async def add_query_by_text_step2(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    query_text = message.text.strip()
    query_url = MonitorService.transform_query_text_to_olx_url(query_text)
    if await query_url_exists(message.from_user.id, query_url):
        if await query_url_is_deleted(message.from_user.id, query_url):
            await restore_query(message.from_user.id, query_url)
            await message.answer(f'Відновлено з видалених моніторинг з URL запиту: {html.bold(query_url)}')
        else:
            await message.answer(f'В переліку вже існує моніторинг з URL запиту: {html.bold(query_url)}')
        return
    query = await create_query(message.from_user.id, query_text, query_url, False)
    initialize_query_ads_task.delay(query.pk)
    await message.answer(
        f'Додано моніторинг: {html.bold(query_text)}\n'
        f'Первинна перевірка запущена у фоні.\nURL запиту: {query_url}'
    )


@main_router.callback_query(F.data == 'insta_menu')
async def instagram_menu_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    await callback.message.answer(
        'Оберіть дію для Instagram моніторингів:',
        reply_markup=get_instagram_menu_inline_keyboard(),
    )


@main_router.callback_query(F.data == 'insta_add')
async def instagram_add_step1(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer('')
    await state.set_state(AddInstagramObservedUser.username)
    await callback.message.answer('Введіть Instagram username без @ або з @:')


@main_router.message(AddInstagramObservedUser.username)
async def instagram_add_step2(message: Message, state: FSMContext) -> None:
    await state.clear()
    user, created, restored = await add_instagram_user(message.text, message.from_user.id)
    if created:
        await message.answer(f'Додано Instagram моніторинг: @{html.bold(user.username)}')
    elif restored:
        await message.answer(f'Відновлено Instagram моніторинг: @{html.bold(user.username)}')
    else:
        await message.answer(f'Підписку на Instagram моніторинг @{html.bold(user.username)} оновлено')


@main_router.callback_query(F.data == 'insta_edit')
async def instagram_edit_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    users = await get_instagram_users(callback.from_user.id)
    await callback.message.answer(
        'Оберіть Instagram username для редагування:\n✅ - активний\n🚫 - деактивований',
        reply_markup=get_instagram_edit_menu_inline_keyboard(users),
    )


@main_router.callback_query(F.data.startswith('insta_user_edit_'))
async def instagram_user_edit_handler(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split('_')[-1])
    subscription = await get_instagram_user(user_id, callback.from_user.id)
    await callback.answer('')
    if not subscription:
        await callback.message.answer('Instagram моніторинг не знайдено')
        return
    status = '✅' if subscription.is_active else '🚫'
    await callback.message.answer(
        f'{html.bold("Instagram username:")} @{subscription.observed_user.username} ({status})',
        reply_markup=get_instagram_user_edit_inline_keyboard(subscription.pk, subscription.is_active),
    )


@main_router.callback_query(F.data.startswith('insta_user_toggle_'))
async def instagram_user_toggle_handler(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split('_')[-1])
    subscription = await toggle_instagram_user(user_id, callback.from_user.id)
    await callback.answer(
        f'{"Активовано" if subscription.is_active else "Деактивовано"} '
        f'@{subscription.observed_user.username}'
    )
    users = await get_instagram_users(callback.from_user.id)
    await callback.message.answer(
        'Оберіть Instagram username для редагування:\n✅ - активний\n🚫 - деактивований',
        reply_markup=get_instagram_edit_menu_inline_keyboard(users),
    )


@main_router.callback_query(F.data.startswith('insta_user_delete_'))
async def instagram_user_delete_handler(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split('_')[-1])
    subscription = await soft_delete_instagram_user(user_id, callback.from_user.id)
    await callback.answer(f'Видалено підписку на Instagram моніторинг @{subscription.observed_user.username}')
    users = await get_instagram_users(callback.from_user.id)
    await callback.message.answer(
        'Оберіть Instagram username для редагування:\n✅ - активний\n🚫 - деактивований',
        reply_markup=get_instagram_edit_menu_inline_keyboard(users),
    )
