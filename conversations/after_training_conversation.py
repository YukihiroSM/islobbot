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


class AfterTrainingQuiz(Enum):
    FIRST_QUESTION_ANSWER = auto()
    SECOND_QUESTION_ANSWER = auto()


async def run_after_training_quiz(update, context):
    query = update.callback_query
    query.answer()

    callback_data = query.data
    training_id = callback_data.split(":")[1]
    context.user_data["training_id"] = training_id

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Оцініть свій рівень стресу (1 - немає стресу, 10 - панічна атака):",
        reply_markup=default_one_to_ten_keyboard(),
    )
    return AfterTrainingQuiz.FIRST_QUESTION_ANSWER


async def retrieve_after_training_first_answer(update, context):
    input_text = update.message.text

    if input_text not in text_constants.ONE_TO_TEN_MARKS:
        await update.message.reply_text(
            text="Оцініть свій рівень стресу (1 - немає стресу, 10 - панічна атака):",
            reply_markup=default_one_to_ten_keyboard(),
        )
        return AfterTrainingQuiz.FIRST_QUESTION_ANSWER

    context.user_data["after_training_stress_level"] = input_text
    await update.message.reply_text(
        text="Чи є у вас крепатура?", reply_markup=yes_no_keyboard()
    )
    return AfterTrainingQuiz.SECOND_QUESTION_ANSWER


async def retrieve_after_training_second_answer(update, context):
    input_text = update.message.text

    if input_text not in text_constants.YES_NO_BUTTONS:
        await update.message.reply_text(
            text="Чи є у вас крепатура?", reply_markup=yes_no_keyboard()
        )
        return AfterTrainingQuiz.SECOND_QUESTION_ANSWER

    with next(get_db()) as db_session:
        update_training_after_quiz(
            training_id=context.user_data["training_id"],
            stress_level=context.user_data["after_training_stress_level"],
            soreness=input_text,
            db_session=db_session,
        )
    await update.message.reply_text(
        text="Дякую, що пройшли опитування! Гарного продовження дня!",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


after_training_quiz_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(run_after_training_quiz, pattern="^after_training_quiz:")
    ],
    states={
        AfterTrainingQuiz.FIRST_QUESTION_ANSWER: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                retrieve_after_training_first_answer,
            )
        ],
        AfterTrainingQuiz.SECOND_QUESTION_ANSWER: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                retrieve_after_training_second_answer,
            )
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
