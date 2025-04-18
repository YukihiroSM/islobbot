import datetime
import os
import re
from datetime import time as datetime_time
from random import shuffle

from telegram import Update
from telegram.ext import CallbackContext

from database import get_db
from utils.db_utils import is_active_user, is_admin_user, get_all_users
from config import BASE_DIR
import text_constants
from utils.logger import get_logger

logger = get_logger(__name__)


def payment_restricted(func):
    async def wrapper(update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        logger.debug(f"Checking payment restriction for user {chat_id}")
        db_session = next(get_db())

        if not is_active_user(chat_id, db_session):
            logger.warning(f"User {chat_id} attempted to access payment-restricted function but is not active")
            await context.bot.send_message(
                chat_id=chat_id,
                text=text_constants.BOT_ACCESS_RESTRICTED_PAYMENT,
            )
            return
        logger.debug(f"User {chat_id} passed payment restriction check")
        await func(update, context)

    return wrapper


def admin_restricted(func):
    async def wrapper(update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        logger.debug(f"Checking admin restriction for user {chat_id}")
        db_session = next(get_db())
        if not is_admin_user(chat_id, db_session):
            logger.warning(f"User {chat_id} attempted to access admin-restricted function but is not admin")
            await context.bot.send_message(
                chat_id=chat_id, text=text_constants.BOT_ACCESS_RESTRICTED_ADMIN
            )
            return
        logger.debug(f"User {chat_id} passed admin restriction check")
        await func(update, context)

    return wrapper


def get_random_motivation_message():
    logger.debug("Getting random motivation message")
    motivation_file = os.path.join(BASE_DIR, "motivational_messages.txt")
    try:
        with open(
            motivation_file, "r", encoding="UTF-8"
        ) as input_file:
            lines = input_file.read().split("\n")
            shuffle(lines)
            logger.debug(f"Selected motivation message: {lines[0]}")
            return f"{text_constants.MOTIVATION_PREFIX} \n{lines[0]}"
    except Exception as e:
        logger.error(f"Error reading motivation messages file: {e}")
        return text_constants.MOTIVATION_PREFIX


def is_valid_morning_time(time_str: str) -> bool:
    logger.debug(f"Validating morning time: {time_str}")
    try:
        match = re.match(r"^(0?[0-9]|1[0-9]|2[0-3]):([0-5][0-9])$", time_str)
        min_time = datetime_time(hour=6)
        max_time = datetime_time(hour=12)

        time = datetime.datetime.strptime(time_str, "%H:%M").time()
        if time < min_time or time > max_time:
            logger.debug(f"Time {time_str} is outside morning hours (6:00-12:00)")
            return False
        result = bool(match)
        logger.debug(f"Morning time validation result for {time_str}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error validating morning time {time_str}: {e}")
        return False


def is_valid_time(time_str: str) -> bool:
    logger.debug(f"Validating time: {time_str}")
    try:
        match = re.match(r"^(0?[0-9]|1[0-9]|2[0-3]):([0-5][0-9])$", time_str)
        min_time = datetime_time(hour=0)
        max_time = datetime_time(hour=23)

        time = datetime.datetime.strptime(time_str, "%H:%M").time()
        if time < min_time or time > max_time:
            logger.debug(f"Time {time_str} is outside valid hours (00:00-23:59)")
            return False
        result = bool(match)
        logger.debug(f"Time validation result for {time_str}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error validating time {time_str}: {e}")
        return False


def get_user_list_as_buttons(action):
    logger.debug(f"Getting user list as buttons for action: {action}")
    with next(get_db()) as db_session:
        buttons = []
        users = get_all_users(db_session)
        logger.debug(f"Found {len(users)} users")
        for user in users:
            user_id = user.chat_id
            user_full_name = user.full_name
            user_username = user.username
            buttons.append(
                [f"{user_full_name} ({user_username}) - {user_id} action:{action}"]
            )
    return buttons
