from aiogram import Router, F, html
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from app.db_operations import is_user_registered, register_new_user, create_new_checker_query, check_query_url_exists
from app.keyboards import get_add_new_query_keyboard, get_add_new_or_edit_query_keyboard, \
    get_add_new_query_menu_inline_keyboard
from app.utilities import get_message_text_for_existing_user, get_message_text_for_new_user, \
    transform_query_text_to_olx_url

main_router = Router(name=__name__)


class AddNewCheckerQueryByURL(StatesGroup):
    query_name = State()
    query_url = State()


class AddNewCheckerQueryByQueryText(StatesGroup):
    query_text = State()


@main_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    if is_user_registered(message.from_user.id):
        message_text = get_message_text_for_existing_user(message.from_user)
        await message.answer(message_text, reply_markup=get_add_new_or_edit_query_keyboard())
    else:
        register_new_user(message.from_user)
        message_text = get_message_text_for_new_user(message.from_user)
        await message.answer(message_text, reply_markup=get_add_new_query_keyboard())


@main_router.message(F.text == 'Додати новий моніторинг')
async def command_add_new_query_handler(message: Message) -> None:
    await message.answer(f"Оберіть спосіб додавання нового моніторингу!",
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
    if check_query_url_exists(message.from_user.id, data["query_url"]):
        create_new_checker_query(message.from_user.id, data["query_name"], data["query_url"])
        await message.answer(f'Додано моніторинг: {html.bold(data["query_name"])}\n'
                             f'URL запиту: {data["query_url"]}')
        await state.clear()
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
    query_url = transform_query_text_to_olx_url(data["query_text"])
    if check_query_url_exists(message.from_user.id, query_url):
        create_new_checker_query(message.from_user.id, data["query_text"], query_url)
        await message.answer(f'Додано моніторинг: {html.bold(data["query_text"])}\n'
                             f'URL запиту: {query_url}')
        await state.clear()
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
