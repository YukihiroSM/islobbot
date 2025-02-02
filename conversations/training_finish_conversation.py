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
from main import cancel, start, training_menu, main_menu
from models import NotificationType
from text_constants import YES_NO_BUTTONS


class TrainingFinishQuiz(Enum):
    FIRST_QUESTION_ANSWER = auto()
    SECOND_QUESTION_ANSWER = auto()


async def handle_training_stop(update, context):
    if "training_id" not in context.user_data:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Упс! Щось пішло не так під час старту тренування. Давай спробуємо ще раз)",
        )
        await training_menu(update, context)
        return
    context.user_data["menu_state"] = "training_stopped"
    await update.message.reply_text(
        "Супер! Ти справився! Давай оцінимо сьогоднішнє тренування:\n"
        "Оціни, наскільки важке було тренування?",
        reply_markup=keyboards.training_first_question_marks_keyboard(),
    )
    return TrainingFinishQuiz.FIRST_QUESTION_ANSWER


async def handle_training_second_question(update, context):
    user_input = update.message.text
    if user_input not in text_constants.ONE_TO_TEN_MARKS:
        await update.message.reply_text(
            "Оціни, наскільки важке було тренування? (Оціни від 1 до 10, де 1 - погано, є симптоми хвороби, 10 - чудово себе почуваєш)",
            reply_markup=keyboards.training_first_question_marks_keyboard(),
        )
        return TrainingFinishQuiz.FIRST_QUESTION_ANSWER
    context.user_data["menu_state"] = "training_stopped_second_question"
    context.user_data["training_stop_first_question"] = user_input
    await update.message.reply_text(
        "Оціни, чи відчуваєш ти якийсь дискомфорт/болі?",
        reply_markup=keyboards.yes_no_keyboard(),
    )
    return TrainingFinishQuiz.SECOND_QUESTION_ANSWER


async def handle_training_finish(update, context):
    logging.info("Inside handle_training_finish")
    user_input = update.message.text
    if user_input not in text_constants.YES_NO_BUTTONS:
        logging.info("Incorrect input")
        context.user_data["menu_state"] = "training_stopped_second_question"
        await update.message.reply_text(
            "Оціни, чи відчуваєш ти якийсь дискомфорт/болі?",
            reply_markup=keyboards.yes_no_keyboard(),
        )
        return TrainingFinishQuiz.SECOND_QUESTION_ANSWER
    context.user_data["menu_state"] = "training_stopped_finish"
    training_discomfort = user_input
    training_hardness = context.user_data["training_stop_first_question"]
    training_id = context.user_data["training_id"]

    if training_discomfort == text_constants.YES_NO_BUTTONS[0]:
        with next(get_db()) as db_session:
            user = get_user_by_chat_id(
                chat_id=update.effective_chat.id, db_session=db_session
            )
            for admin_chat_id in ADMIN_CHAT_IDS:
                await context.bot.send_message(
                    chat_id=admin_chat_id,
                    text=f"Користувач {user.full_name}(@{user.username}) - {user.chat_id} відчуває болі після тренування!",
                )

    with next(get_db()) as db_session:
        training_duration = stop_training(
            training_id=training_id,
            training_hardness=training_hardness,
            training_discomfort=training_discomfort,
            db_session=db_session,
        )

    with next(get_db()) as db_session:
        update_training_notification(update.effective_chat.id, db_session)

    await context.bot.send_message(
        text=f"Супер! Ти тренувався аж {str(training_duration).split('.')[0]}! \n\n"
        f"{get_random_motivation_message()} \n\n"
        f"Тепер час відпочити)",
        chat_id=update.effective_chat.id,
    )
    await main_menu(update, context)
    return ConversationHandler.END


training_finish_quiz_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.TEXT & filters.Regex(f"^{text_constants.END_TRAINING}$"),
            handle_training_stop,
        )
    ],
    states={
        TrainingFinishQuiz.FIRST_QUESTION_ANSWER: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, handle_training_second_question
            )
        ],
        TrainingFinishQuiz.SECOND_QUESTION_ANSWER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_training_finish)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
