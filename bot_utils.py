from telegram import Update
from telegram.ext import CallbackContext
from database import get_db
from db_utils import is_active_user, is_admin_user


def payment_restricted(func):
    async def wrapper(update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        db_session = next(get_db())

        if not is_active_user(chat_id, db_session):
            await context.bot.send_message(
                chat_id=chat_id,
                text="Доступ до бота обмежено. Вам потрібно уточнити дані стосовно оплати!",
            )
            return
        await func(update, context)

    return wrapper


def admin_restricted(func):
    async def wrapper(update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        db_session = next(get_db())
        if not is_admin_user(chat_id, db_session):
            await context.bot.send_message(
                chat_id=chat_id, text="Доступ до цієї команди неможливий!"
            )
            return
        await func(update, context)

    return wrapper
