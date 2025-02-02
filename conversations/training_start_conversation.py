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


class TrainingStartQuiz(Enum):
    FIRST_QUESTION_ANSWER = auto()


async def handle_training_startup(update, context):
    context.user_data["menu_state"] = "training_start"
    await update.message.reply_text(
        "Ура ура! Розпочинаємо тренування!"
        "Почнемо з невеличкого опитування."
        "Як ти себе почуваєш? (Оціни від 1 до 10, де 1 - погано, є симптоми хвороби, 10 - чудово себе почуваєш)",
        reply_markup=keyboards.training_first_question_marks_keyboard(),
    )
    return TrainingStartQuiz.FIRST_QUESTION_ANSWER


async def handle_training_timer_start(update, context):
    user_input = update.message.text
    if user_input not in text_constants.ONE_TO_TEN_MARKS:
        await update.message.reply_text(
            "Як ти себе почуваєш? (Оціни від 1 до 10, де 1 - погано, є симптоми хвороби, 10 - чудово себе почуваєш)",
            reply_markup=keyboards.training_first_question_marks_keyboard(),
        )
        return TrainingStartQuiz.FIRST_QUESTION_ANSWER
    context.user_data["menu_state"] = "training_start_timer_start"
    with next(get_db()) as db_session:
        training_id = start_user_training(
            chat_id=update.effective_chat.id,
            user_state_mark=user_input,
            db_session=db_session,
        )
        if not training_id:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Упс! Щось пішло не так під час старту тренування. Давай спробуємо ще раз)",
            )
            await training_menu(update, context)
        else:
            dummy_pdf = "dummy.pdf"
            context.user_data["training_id"] = training_id

            await context.bot.send_document(
                chat_id=update.effective_user.id,
                document=dummy_pdf,
                caption="Ось ваш файл для тренування!",
            )

            await update.message.reply_text(
                "Го го го!! Успіхів у тренуванні, тренування розпочато!",
                reply_markup=keyboards.training_in_progress_keyboard(),
            )

    return ConversationHandler.END


training_start_quiz_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.TEXT & filters.Regex(f"^{text_constants.START_TRAINING}$"),
            handle_training_startup,
        )
    ],
    states={
        TrainingStartQuiz.FIRST_QUESTION_ANSWER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_training_timer_start)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
