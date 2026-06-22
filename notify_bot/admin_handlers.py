import asyncio
import math
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from notify_bot.handlers import get_context
from notify_bot.keyboards import get_admin_logs_keyboard, get_admin_menu_keyboard, get_admin_user_edit_keyboard, get_admin_users_keyboard
from notify_bot.tasks import check_new_ads_async, check_new_insta_content_async

admin_router = Router(name='admin')
ADMIN_LOGS_PAGE_SIZE = 10


@admin_router.callback_query(F.data == 'admin_menu')
async def admin_menu_handler(callback: CallbackQuery):
    ctx = get_context(callback)
    if not ctx.is_admin(callback.from_user.id):
        await callback.answer('Доступ лише для адміністратора', show_alert=True)
        return
    await callback.answer('')
    await callback.message.answer('Адмін-панель:', reply_markup=get_admin_menu_keyboard())


@admin_router.callback_query(F.data == 'admin_stats')
async def admin_stats_handler(callback: CallbackQuery):
    ctx = get_context(callback)
    if not ctx.is_admin(callback.from_user.id):
        await callback.answer('Доступ лише для адміністратора', show_alert=True)
        return
    stats = await ctx.db.dashboard_stats()
    await callback.answer('')
    await callback.message.answer(
        f"{html.bold('Статистика')}\n"
        f"Користувачів: {stats['users']}\n"
        f"Активних моніторингів: {stats['active_queries']}\n"
        f"Деактивованих моніторингів: {stats['inactive_queries']}\n"
        f"OLX: {stats['olx_queries']}\n"
        f"Rieltor: {stats['rieltor_queries']}\n"
        f"Instagram підписок: {stats['insta_subscriptions']}"
    )


@admin_router.callback_query(F.data == 'admin_users')
async def admin_users_handler(callback: CallbackQuery):
    ctx = get_context(callback)
    if not ctx.is_admin(callback.from_user.id):
        await callback.answer('Доступ лише для адміністратора', show_alert=True)
        return
    users = await ctx.db.list_telegram_users()
    await callback.answer('')
    await callback.message.answer('Користувачі:', reply_markup=get_admin_users_keyboard(users))


@admin_router.callback_query(F.data.startswith('admin_user_'))
async def admin_user_detail_handler(callback: CallbackQuery):
    ctx = get_context(callback)
    if not ctx.is_admin(callback.from_user.id):
        await callback.answer('Доступ лише для адміністратора', show_alert=True)
        return
    if callback.data.startswith('admin_user_') and 'toggle' in callback.data:
        return
    user_id = int(callback.data.split('_')[-1])
    user = await ctx.db.get_telegram_user(user_id)
    if not user:
        await callback.answer('Користувача не знайдено', show_alert=True)
        return
    await callback.answer('')
    await callback.message.answer(
        f"{html.bold('Користувач')}\n"
        f"ID: {html.code(str(user.user_telegram_id))}\n"
        f"Ім'я: {user.full_name or '-'}\n"
        f"Username: @{user.username or '-'}\n"
        f"Активний: {'так' if user.is_active else 'ні'}\n"
        f"Адмін: {'так' if user.is_admin else 'ні'}",
        reply_markup=get_admin_user_edit_keyboard(user.user_telegram_id, user.is_active, user.is_admin),
    )


@admin_router.callback_query(F.data.startswith('admin_toggle_active_'))
async def admin_toggle_active_handler(callback: CallbackQuery):
    ctx = get_context(callback)
    if not ctx.is_admin(callback.from_user.id):
        await callback.answer('Доступ лише для адміністратора', show_alert=True)
        return
    user_id = int(callback.data.split('_')[-1])
    user = await ctx.db.get_telegram_user(user_id)
    user = await ctx.db.set_user_active(user_id, not user.is_active)
    await callback.answer('Оновлено')
    await callback.message.answer(
        f"Користувач {user.full_name or user.user_telegram_id}: активний={'так' if user.is_active else 'ні'}",
        reply_markup=get_admin_user_edit_keyboard(user.user_telegram_id, user.is_active, user.is_admin),
    )


@admin_router.callback_query(F.data.startswith('admin_toggle_admin_'))
async def admin_toggle_admin_handler(callback: CallbackQuery):
    ctx = get_context(callback)
    if not ctx.is_admin(callback.from_user.id):
        await callback.answer('Доступ лише для адміністратора', show_alert=True)
        return
    user_id = int(callback.data.split('_')[-1])
    user = await ctx.db.get_telegram_user(user_id)
    user = await ctx.db.set_user_admin(user_id, not user.is_admin)
    await callback.answer('Оновлено')
    await callback.message.answer(
        f"Користувач {user.full_name or user.user_telegram_id}: адмін={'так' if user.is_admin else 'ні'}",
        reply_markup=get_admin_user_edit_keyboard(user.user_telegram_id, user.is_active, user.is_admin),
    )


@admin_router.callback_query(F.data == 'admin_queries')
async def admin_queries_handler(callback: CallbackQuery):
    ctx = get_context(callback)
    if not ctx.is_admin(callback.from_user.id):
        await callback.answer('Доступ лише для адміністратора', show_alert=True)
        return
    queries = await ctx.db.list_all_queries()
    subscriptions = await ctx.db.list_insta_subscriptions()
    await callback.answer('')
    if not queries and not subscriptions:
        await callback.message.answer('Моніторингів немає')
        return

    sections = []
    for source, title in (('olx', 'OLX'), ('rieltor', 'Rieltor.ua')):
        source_queries = [query for query in queries if query.source == source]
        if not source_queries:
            continue
        lines = []
        for query in source_queries[:30]:
            sign = '✅' if query.is_active else '🚫'
            user_label = query.user.full_name if query.user else str(query.user_telegram_id)
            lines.append(f'{sign} {query.query_name} — {user_label}')
        sections.append(html.bold(title) + '\n' + '\n'.join(lines))

    if subscriptions:
        insta_lines = []
        for subscription in subscriptions[:30]:
            sign = '✅' if subscription.is_active else '🚫'
            user_label = subscription.user.full_name if subscription.user else str(subscription.user_telegram_id)
            insta_lines.append(f'{sign} @{subscription.observed_user.username} — {user_label}')
        sections.append(html.bold('Instagram') + '\n' + '\n'.join(insta_lines))

    await callback.message.answer(html.bold('Моніторинги') + '\n\n' + '\n\n'.join(sections))


@admin_router.callback_query(F.data == 'admin_ads')
async def admin_ads_handler(callback: CallbackQuery):
    ctx = get_context(callback)
    if not ctx.is_admin(callback.from_user.id):
        await callback.answer('Доступ лише для адміністратора', show_alert=True)
        return
    ads = await ctx.db.list_recent_ads(limit=15)
    await callback.answer('')
    if not ads:
        await callback.message.answer('Оголошень немає')
        return
    lines = []
    for ad in ads:
        query_name = ad.query.query_name if ad.query else str(ad.query_id)
        lines.append(f'{query_name}: {ad.ad_description[:80]} — {ad.ad_url}')
    await callback.message.answer(html.bold('Останні оголошення') + '\n\n' + '\n\n'.join(lines))


@admin_router.callback_query(F.data == 'admin_insta')
async def admin_insta_handler(callback: CallbackQuery):
    await admin_queries_handler(callback)


def _kyiv_timezone():
    try:
        return ZoneInfo('Europe/Kyiv')
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=2))


def _format_log_time(created_at) -> str:
    if not created_at:
        return '—'
    if created_at.tzinfo is not None:
        created_at = created_at.astimezone(_kyiv_timezone())
    return created_at.strftime('%d.%m.%Y %H:%M:%S')


def _build_logs_text(logs, page: int, total_pages: int, total: int) -> str:
    lines = [
        f"{_format_log_time(log.created_at)} | [{log.level}] {log.job_name or '-'}: {log.message[:120]}"
        for log in logs
    ]
    return (
        f"{html.bold('Логи')} (сторінка {page + 1}/{total_pages}, всього {total})\n\n"
        + '\n'.join(lines)
    )


async def _send_admin_logs(callback: CallbackQuery, page: int, *, edit: bool = False) -> None:
    ctx = get_context(callback)
    total = await ctx.db.count_job_logs()
    if total == 0:
        await callback.message.answer('Логів немає')
        return

    total_pages = max(1, math.ceil(total / ADMIN_LOGS_PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    logs = await ctx.db.get_job_logs(limit=ADMIN_LOGS_PAGE_SIZE, offset=page * ADMIN_LOGS_PAGE_SIZE)
    text = _build_logs_text(logs, page, total_pages, total)
    markup = get_admin_logs_keyboard(page, total_pages)
    if edit:
        try:
            await callback.message.edit_text(text, reply_markup=markup)
            return
        except TelegramBadRequest:
            pass
    await callback.message.answer(text, reply_markup=markup)


@admin_router.callback_query(F.data == 'admin_logs')
async def admin_logs_handler(callback: CallbackQuery):
    ctx = get_context(callback)
    if not ctx.is_admin(callback.from_user.id):
        await callback.answer('Доступ лише для адміністратора', show_alert=True)
        return
    await callback.answer('')
    await _send_admin_logs(callback, page=0)


@admin_router.callback_query(F.data.startswith('admin_logs_page_'))
async def admin_logs_page_handler(callback: CallbackQuery):
    ctx = get_context(callback)
    if not ctx.is_admin(callback.from_user.id):
        await callback.answer('Доступ лише для адміністратора', show_alert=True)
        return
    page = int(callback.data.rsplit('_', 1)[-1])
    await callback.answer('')
    await _send_admin_logs(callback, page=page, edit=True)


@admin_router.callback_query(F.data == 'admin_logs_noop')
async def admin_logs_noop_handler(callback: CallbackQuery):
    await callback.answer()


@admin_router.callback_query(F.data == 'admin_run_ads')
async def admin_run_ads_handler(callback: CallbackQuery):
    ctx = get_context(callback)
    if not ctx.is_admin(callback.from_user.id):
        await callback.answer('Доступ лише для адміністратора', show_alert=True)
        return
    await callback.answer('Запускаю перевірку OLX/Rieltor')
    asyncio.create_task(check_new_ads_async(ctx.bot, ctx.db))


@admin_router.callback_query(F.data == 'admin_run_insta')
async def admin_run_insta_handler(callback: CallbackQuery):
    ctx = get_context(callback)
    if not ctx.is_admin(callback.from_user.id):
        await callback.answer('Доступ лише для адміністратора', show_alert=True)
        return
    await callback.answer('Запускаю перевірку Instagram')
    asyncio.create_task(check_new_insta_content_async(ctx.bot, ctx.db))
