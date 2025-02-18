import datetime
import os
import re
from datetime import time as datetime_time
from random import shuffle

from telegram import Update
from telegram.ext import CallbackContext

from database import get_db
from utils.db_utils import is_active_user, is_admin_user
from config import BASE_DIR


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


def get_random_motivation_message():
    with open(os.path.join(BASE_DIR, "motivational_messages.txt"), "r", encoding="UTF-8") as input_file:
        lines = input_file.read().split("\n")
        shuffle(lines)
        return f"Трішки мотивації тобі: \n{lines[0]}"


def is_valid_morning_time(time_str: str) -> bool:
    try:
        match = re.match(r"^(0?[0-9]|1[0-9]|2[0-3]):([0-5][0-9])$", time_str)
        min_time = datetime_time(hour=6)
        max_time = datetime_time(hour=12)

        time = datetime.datetime.strptime(time_str, "%H:%M").time()
        if time < min_time or time > max_time:
            return False
        return bool(match)
    except Exception as e:
        return False


def is_valid_time(time_str: str) -> bool:
    try:
        match = re.match(r"^(0?[0-9]|1[0-9]|2[0-3]):([0-5][0-9])$", time_str)
        min_time = datetime_time(hour=0)
        max_time = datetime_time(hour=23)

        time = datetime.datetime.strptime(time_str, "%H:%M").time()
        if time < min_time or time > max_time:
            return False
        return bool(match)
    except Exception as e:
        return False
