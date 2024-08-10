from aiogram import Router, F, html
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from app.db_operations import is_user_registered, register_new_user, create_new_checker_query, check_query_url_exists, \
    create_new_found_ad
from app.keyboards import get_start_keyboard, get_add_new_or_edit_query_keyboard, \
    get_add_new_query_menu_inline_keyboard
from app.parsing import parse, IncorrectURL
from app.utilities import get_message_text_for_existing_user, get_message_text_for_new_user, \
    transform_query_text_to_olx_url

main_router = Router(name=__name__)


class AddNewCheckerQueryByURL(StatesGroup):
    query_name = State()
    query_url = State()


class AddNewCheckerQueryByQueryText(StatesGroup):
    query_text = State()


# # Функція для відправки стартового повідомлення всім новим користувачам
# @main_router.message(lambda message: message.from_user.is_bot == False)
# async def start_message(message: Message):
#     await message.answer("Привіт! Це стартове повідомлення, яке ти отримав одразу.")


@main_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    if await is_user_registered(message.from_user.id):
        message_text = await get_message_text_for_existing_user(message.from_user)
        await message.answer(message_text, reply_markup=get_add_new_or_edit_query_keyboard())
    else:
        await register_new_user(message.from_user)
        message_text = await get_message_text_for_new_user(message.from_user)
        await message.answer(message_text, reply_markup=get_start_keyboard())


@main_router.callback_query(F.data == 'new_query')
async def command_add_new_query_handler(callback: CallbackQuery) -> None:
    await callback.answer('12345')
    await callback.message.answer(f"Оберіть спосіб додавання нового моніторингу!",
                                  reply_markup=get_add_new_query_menu_inline_keyboard())


@main_router.callback_query(F.data == 'query_by_url')
async def add_query_by_url_step1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('12345')
    await state.set_state(AddNewCheckerQueryByURL.query_name)
    await callback.message.answer('Введіть назву запиту:')


@main_router.message(AddNewCheckerQueryByURL.query_name)
async def add_query_by_url_step2(message: Message, state: FSMContext):
    await state.update_data(query_name=message.text)
    await state.set_state(AddNewCheckerQueryByURL.query_url)
    await message.answer('Введіть URL запиту:')


@main_router.message(AddNewCheckerQueryByURL.query_url)
async def add_query_by_url_step3(message: Message, state: FSMContext):
    await state.update_data(query_url=message.text)
    data = await state.get_data()
    if not await check_query_url_exists(message.from_user.id, data["query_url"]):
        try:
            parsed_ads = parse(data["query_url"])
            if parsed_ads:
                query_id = await create_new_checker_query(message.from_user.id, data["query_name"], data["query_url"])
                for parsed_ad in parsed_ads:
                    await create_new_found_ad(query_id, parsed_ad['ad_url'], parsed_ad['ad_description'],
                                              parsed_ad['ad_price'], parsed_ad['currency'])

                await message.answer(f'Додано моніторинг: {html.bold(data["query_name"])}\n'
                                     f'Знайдено {len(parsed_ads)} поточних оголошень\n'
                                     f'URL запиту: {data["query_url"]}')
            else:
                await message.answer(f'Введений вами URL не містить Olx оголошень')
        except IncorrectURL as e:
            await message.answer(e.message)
    else:
        await message.answer(f'В переліку вже існує моніторинг з URL запиту: {html.bold(data["query_url"])}')
    await state.clear()


@main_router.callback_query(F.data == 'query_by_text')
async def add_query_by_text_step1(callback: CallbackQuery, state: FSMContext):
    await callback.answer('12345')
    await state.set_state(AddNewCheckerQueryByQueryText.query_text)
    await callback.message.answer('Введіть текст запиту:')


@main_router.message(AddNewCheckerQueryByQueryText.query_text)
async def add_query_by_text_step2(message: Message, state: FSMContext):
    await state.update_data(query_text=message.text)
    data = await state.get_data()
    query_url = await transform_query_text_to_olx_url(data["query_text"])
    if not await check_query_url_exists(message.from_user.id, query_url):
        query_id = await create_new_checker_query(message.from_user.id, data["query_text"], query_url)
        parsed_ads = parse(data["query_url"])
        for parsed_ad in parsed_ads:
            await create_new_found_ad(query_id, parsed_ad['ad_url'], parsed_ad['ad_description'],
                                      parsed_ad['ad_price'], parsed_ad['currency'])

        await message.answer(f'Додано моніторинг: {html.bold(data["query_text"])}\n'
                             f'Знайдено {len(parsed_ads)} поточних оголошень\n'
                             f'URL запиту: {query_url}')
    else:
        await message.answer(f'В переліку вже існує моніторинг з URL запиту: {html.bold(query_url)}')
    await state.clear()

# @main_router.message(F.text == 'text64647')
# async def command_add_new_query_handler(message: Message, command: CommandObject) -> None:
#     await message.answer(f"Hellooooo, {command.args}!")
#
#
# @main_router.message()
# async def echo_handler(message: Message) -> None:
#     """
#     Handler will forward receive a message back to the sender
#
#     By default, message handler will handle all message types (like a text, photo, sticker etc.)
#     """
#     try:
#         # Send a copy of the received message
#         await message.send_copy(chat_id=message.chat.id)
#     except TypeError:
#         # But not all the types is supported to be copied so need to handle it
#         await message.answer("Nice try!")
