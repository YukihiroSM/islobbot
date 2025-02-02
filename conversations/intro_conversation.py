import asyncio
import datetime
import logging
import re
import time
from datetime import datetime
from datetime import time as datetime_time
from datetime import timedelta
from enum import Enum, auto
from ssl import get_default_verify_paths

import schedule
from sqlalchemy.exc import DataError
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import keyboards
import text_constants
from bot_utils import get_random_motivation_message, is_valid_morning_time
from config import ADMIN_CHAT_IDS, BOT_TOKEN, DATABASE_URL, timezone
from database import get_db
from db_utils import (
    add_or_update_user,
    create_training_notifications,
    get_notifications_by_type,
    get_notifications_to_send_by_time,
    get_user_by_chat_id,
    get_user_notification_by_time,
    get_users_with_yesterday_trainings,
    is_user_had_morning_quiz_today,
    is_user_ready_to_use,
    save_morning_quiz_results,
    save_user_notification_preference,
    start_user_training,
    stop_training,
    toggle_user_notification,
    update_notification_sent,
    update_training_after_quiz,
    update_training_notification,
    update_user_full_name,
    update_user_notification_preference_admin_message_sent,
    update_user_notification_preference_next_execution,
    update_user_notification_time,
)
from keyboards import default_one_to_ten_keyboard, main_menu_keyboard, yes_no_keyboard
from main import cancel, start
from models import NotificationType
from text_constants import YES_NO_BUTTONS


class IntroConversation(Enum):
    NEW_COMER = auto()
    GET_NAME = auto()
    GET_TIME = auto()


async def get_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    with next(get_db()) as db_session:
        update_user_full_name(
            chat_id=update.effective_chat.id, full_name=name, db=db_session
        )
        await update.message.reply_text(
            f"Дякую, {name}! Тепер налаштуємо сповіщення. Введіть бажаний час для ранкового сповіщення. "
            f"Його потрібно увести в форматі '08:00'. "
            f"Введіть будь-який зручний час в рамках від 06:00 до 12:00! ",
        )
        return IntroConversation.GET_TIME


async def get_morning_notification_time(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    time_input = update.message.text
    if is_valid_morning_time(time_input):
        with next(get_db()) as db_session:
            hours, minutes = map(int, time_input.split(":")[:2])

            datetime_now = datetime.now(tz=timezone)
            datetime_time_input = timezone.localize(
                datetime(
                    datetime_now.year,
                    datetime_now.month,
                    datetime_now.day,
                    hours,
                    minutes,
                )
            )
            if datetime_now < datetime_time_input:
                next_execution_datetime = datetime_time_input
            else:
                next_execution_datetime = datetime_time_input + timedelta(days=1)
            save_user_notification_preference(
                chat_id=update.effective_user.id,
                notification_type=NotificationType.MORNING_NOTIFICATION,
                notification_time=time_input,
                next_execution_datetime=next_execution_datetime,
                db_session=db_session,
            )

            await update.message.reply_text(
                "Супер! Налаштування завершено! Тепер очікуй від бота сповіщень у вказаний час!",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END
    else:
        await update.message.reply_text(
            f"Невірний формат. Введіть час у форматі '08:00' в рамках від 06:00 до 12:00!"
        )
        return IntroConversation.GET_TIME


intro_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        IntroConversation.GET_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_name)
        ],
        IntroConversation.GET_TIME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, get_morning_notification_time
            )
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
