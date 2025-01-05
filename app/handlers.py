import injector

from aiogram import Router, F, html
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import BotCommand, BotCommandScopeDefault, Message, CallbackQuery

from app.parsers import parser_olx
from app.db.db_interface import DatabaseInterface
from app.injector_config import BotModule
from app.keyboards import get_start_keyboard, get_add_new_or_edit_query_keyboard, \
    get_add_new_query_menu_inline_keyboard, get_edit_menu_inline_keyboard, get_query_edit_inline_keyboard
from app.parsers.parser_rieltor import parse_rieltor
from app.handlers_utilities import get_message_text_for_existing_user, get_message_text_for_new_user, \
    transform_query_text_to_olx_url, IncorrectURL

main_router = Router(name=__name__)

db = injector.Injector([BotModule]).get(DatabaseInterface)


class AddNewCheckerQueryByURL(StatesGroup):
    query_name = State()
    query_url = State()


class AddNewCheckerQueryByQueryText(StatesGroup):
    query_text = State()


async def set_commands(bot):
    commands = [BotCommand(command='start', description='Стартове меню'),
                BotCommand(command='about', description='Про проект')]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


@main_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """

    if await db.is_user_registered(message.from_user.id):
        message_text = await get_message_text_for_existing_user(message.from_user)
        await message.answer(message_text, reply_markup=get_add_new_or_edit_query_keyboard())
    else:
        await db.register_new_user(message.from_user)
        message_text = await get_message_text_for_new_user(message.from_user)
        await message.answer(message_text, reply_markup=get_start_keyboard())


@main_router.message(Command('about'))
async def command_about_handler(message: Message) -> None:
    """
    This handler receives messages with `/about` command
    """
    await message.answer(f"Проект створено для перевірки й оповіщення користувача, щодо нових Olx-оголошень, щойно "
                         f"вони з'являються на порталі.\n"
                         f"На разі є можливість додавати запити по введеному текстовому значенню (запит лише по цьому "
                         f"значенню, без будь-яких додаткових фільтрів), а також запити по URL, що веде на "
                         f"Olx-оголошення (введений URL може містити в собі вже безліч застосованих фільтрів). "
                         f"Також є можливість активації/деактивації моніторингових запитів та їх видалення.\n"
                         f"Автор проекту [Ковальчук Володимир](https://t.me/slengpack). Звертайтеся в разі виникнення "
                         f"пропозицій, побажань чи конструктивних відгуків",
                         parse_mode="Markdown")


@main_router.callback_query(F.data == 'new_query')
async def command_add_new_query_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    await callback.message.answer(f"Оберіть спосіб додавання нового моніторингу!",
                                  reply_markup=get_add_new_query_menu_inline_keyboard())


@main_router.callback_query(F.data == 'edit_queries')
async def command_edit_queries_handler(callback: CallbackQuery) -> None:
    await callback.answer('')
    checker_queries = await db.get_checker_queries_by_user(callback.from_user.id)
    await callback.message.answer(f"Оберіть моніторинг для редагування:\n"
                                  f"✅ - активний моніторинг\n"
                                  f"🚫 - деактивований моніторинг",
                                  reply_markup=get_edit_menu_inline_keyboard(checker_queries))


@main_router.callback_query(F.data.startswith('query_edit'))
async def command_edit_queries_handler(callback: CallbackQuery) -> None:
    query_id = int(callback.data.split('_')[-1])
    checker_query = await db.get_checker_query_by_id(query_id)
    await callback.answer('')
    await callback.message.answer(f'{html.bold("Назва моніторингу:")} "{checker_query['query_name']}"',
                                  reply_markup=get_query_edit_inline_keyboard(query_id, checker_query['is_active']))


@main_router.callback_query(F.data.startswith('query_activate'))
async def command_edit_queries_handler(callback: CallbackQuery) -> None:
    query_id = int(callback.data.split('_')[-1])
    checker_query = await db.get_checker_query_by_id(query_id)
    is_active = True if checker_query['is_active'] == 0 else False
    await db.update_checker_query_is_active(query_id, is_active)
    await callback.answer(f'{"Активовано" if is_active else "Деактивовано"} моніторинг "{checker_query['query_name']}"')

    checker_queries = await db.get_checker_queries_by_user(callback.from_user.id)
    await callback.message.answer(f"Оберіть моніторинг для редагування:\n"
                                  f"✅ - активний моніторинг\n"
                                  f"🚫 - деактивований моніторинг",
                                  reply_markup=get_edit_menu_inline_keyboard(checker_queries))


@main_router.callback_query(F.data.startswith('query_delete'))
async def command_edit_queries_handler(callback: CallbackQuery) -> None:
    query_id = int(callback.data.split('_')[-1])
    checker_query_for_delete = await db.get_checker_query_by_id(query_id)
    await db.set_checker_query_deleted(query_id)
    await callback.answer(f'Видалено моніторинг "{checker_query_for_delete['query_name']}"')

    checker_queries = await db.get_checker_queries_by_user(callback.from_user.id)
    await callback.message.answer(f"Оберіть моніторинг для редагування:\n"
                                  f"✅ - активний моніторинг\n"
                                  f"🚫 - деактивований моніторинг",
                                  reply_markup=get_edit_menu_inline_keyboard(checker_queries))


@main_router.callback_query(F.data == 'query_by_url')
async def add_query_by_url_step1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.set_state(AddNewCheckerQueryByURL.query_name)
    await callback.message.answer('Введіть назву запиту (ця назва буде відображатися в переліку запитів):')


@main_router.message(AddNewCheckerQueryByURL.query_name)
async def add_query_by_url_step2(message: Message, state: FSMContext):
    await state.update_data(query_name=message.text)
    await state.set_state(AddNewCheckerQueryByURL.query_url)
    await message.answer('Введіть URL запиту:')


@main_router.message(AddNewCheckerQueryByURL.query_url)
async def add_query_by_url_step3(message: Message, state: FSMContext):
    await state.update_data(query_url=message.text)
    data = await get_data_from_and_clean_state(state)

    if not await db.check_query_url_exists(message.from_user.id, data["query_url"]):
        try:
            parsed_ads = None
            service_title = 'Olx та rieltor.ua'
            if "olx.ua/" in data["query_url"]:
                parsed_ads = await get_olx_parsed_ads(data["query_url"])
                service_title = 'Olx'
            elif "rieltor.ua/" in data["query_url"]:
                parsed_ads = await parse_rieltor(data["query_url"])
                service_title = 'rieltor.ua'
            else:
                await message.answer(f'Підтримуються тільки сервіси {service_title}')
            await save_found_ads_and_inform_user(
                data["query_name"],
                data["query_url"],
                message,
                parsed_ads,
                service_title
            )
        except IncorrectURL as e:
            await message.answer(e.message)
    else:
        await check_and_inform_user_for_deleted_or_existing_query(data["query_url"], message)


@main_router.callback_query(F.data == 'query_by_text')
async def add_query_by_text_step1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.set_state(AddNewCheckerQueryByQueryText.query_text)
    await callback.message.answer('Введіть текст запиту:')


@main_router.message(AddNewCheckerQueryByQueryText.query_text)
async def add_query_by_text_step2(message: Message, state: FSMContext):
    await state.update_data(query_text=message.text)
    data = await get_data_from_and_clean_state(state)

    query_url = await transform_query_text_to_olx_url(data["query_text"])
    if not await db.check_query_url_exists(message.from_user.id, query_url):
        parsed_ads = await get_olx_parsed_ads(query_url)
        await save_found_ads_and_inform_user(
            data["query_text"],
            query_url,
            message,
            parsed_ads,
            "Olx"
        )
    else:
        await check_and_inform_user_for_deleted_or_existing_query(query_url, message)


async def get_data_from_and_clean_state(state):
    data = await state.get_data()
    await state.clear()
    return data


async def get_olx_parsed_ads(query_url):
    olx_queries_with_unique_ads = await parser_olx.get_parsed_ads({1: query_url})
    parsed_ads = None
    if 1 in olx_queries_with_unique_ads:
        parsed_ads = olx_queries_with_unique_ads[1]
    return parsed_ads


async def save_found_ads_and_inform_user(query_name, query_url, message, parsed_ads, service_title):
    if parsed_ads:
        query_id = await db.create_new_checker_query(
            message.from_user.id,
            query_name,
            query_url
        )
        for parsed_ad in parsed_ads:
            await db.create_new_found_ad(
                query_id,
                parsed_ad['ad_url'],
                parsed_ad['ad_description'],
                parsed_ad['ad_price'],
                parsed_ad['currency']
            )

        await message.answer(f'Додано моніторинг: {html.bold(query_name)}\n'
                             f'Знайдено {len(parsed_ads)} поточних оголошень\n'
                             f'URL запиту: {query_url}')
    else:
        await message.answer(f'Введений вами URL не містить {service_title} оголошень')


async def check_and_inform_user_for_deleted_or_existing_query(query_url, message):
    if await db.check_query_url_is_deleted(message.from_user.id, query_url):  # Відновити раніше видалений моніторинг
        query_id = await db.get_user_checker_query_id_by_url(message.from_user.id, query_url)
        await db.set_checker_query_non_deleted_and_active(query_id)
        await message.answer(f'Відновлено з видалених моніторинг з URL запиту: {html.bold(query_url)}')
    else:
        await message.answer(f'В переліку вже існує моніторинг з URL запиту: {html.bold(query_url)}')
