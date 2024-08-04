from aiogram import Router, html, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from app.db_operations import is_user_registered, register_new_user
from app.keyboards import get_add_new_query_keyboard, get_add_new_or_edit_query_keyboard
from app.utilities import get_message_text_for_existing_user, get_message_text_for_new_user

main_router = Router(name=__name__)


class AddNewCheckerQueryByURL(StatesGroup):
    query_name = State()
    query_url = State()


class AddNewCheckerQueryByQueryText(StatesGroup):
    query_name = State()


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
    await message.answer(f"khfdjgfd!", reply_markup=kb.catalog)


@main_router.message(F.text == 'text64647')
async def command_add_new_query_handler(message: Message, command: CommandObject) -> None:
    await message.answer(f"Hellooooo, {command.args}!")


@main_router.message()
async def echo_handler(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")