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
from bot_utils import (
    get_random_motivation_message,
    is_valid_morning_time,
    is_valid_time,
)
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


class MorningQuizConversation(Enum):
    FIRST_QUESTION_ANSWER = auto()
    SECOND_QUESTION_ANSWER = auto()
    IS_GOING_TO_HAVE_TRAINING = auto()
    WHEN_GOING_TO_HAVE_TRAINING = auto()


async def start_morning_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with next(get_db()) as db_session:
        if is_user_had_morning_quiz_today(
            chat_id=update.effective_user.id, db_session=db_session
        ):
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"Ви вже проходили ранкове опитування сьогодні!",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END

        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Як ви себе почуваєте?",
            reply_markup=keyboards.default_one_to_ten_keyboard(),
        )
        return MorningQuizConversation.FIRST_QUESTION_ANSWER


async def retrieve_morning_feelings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_text = update.message.text
    if not input_text.isnumeric() or not (1 <= int(input_text) <= 10):
        await update.message.reply_text(
            text="Як ви себе почуваєте? Оберіть один із варіантів нижче!",
            reply_markup=keyboards.default_one_to_ten_keyboard(),
        )
        return MorningQuizConversation.FIRST_QUESTION_ANSWER

    context.user_data["morning_feelings"] = input_text

    await update.message.reply_text(
        text="Скільки годин ви поспали? Введіть час у форматі '08:00'",
    )
    return MorningQuizConversation.SECOND_QUESTION_ANSWER


async def retrieve_morning_sleep_hours(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    input_text = update.message.text

    if not is_valid_time(input_text):
        await update.message.reply_text(
            text="Скільки годин ви поспали? Введіть час у форматі '08:00'",
        )
        return MorningQuizConversation.SECOND_QUESTION_ANSWER

    context.user_data["morning_sleep_time"] = input_text
    await update.message.reply_text(
        text="Чи плануєте ви сьогодні тренування?",
        reply_markup=keyboards.yes_no_keyboard(),
    )

    return MorningQuizConversation.IS_GOING_TO_HAVE_TRAINING


async def retrieve_morning_is_going_to_have_training(update, context):
    user_input = update.message.text

    if user_input not in text_constants.YES_NO_BUTTONS:
        await update.message.reply_text(
            text="Чи плануєте ви сьогодні тренування?",
            reply_markup=keyboards.yes_no_keyboard(),
        )
        return MorningQuizConversation.IS_GOING_TO_HAVE_TRAINING

    context.user_data["is_going_to_have_training"] = user_input

    if user_input == text_constants.YES_NO_BUTTONS[0]:

        await update.message.reply_text(
            text="Введіть, о которій плануєте прийти на тренування? (Наприклад, '15:00')",
        )
        return MorningQuizConversation.WHEN_GOING_TO_HAVE_TRAINING

    with next(get_db()) as db_session:

        save_morning_quiz_results(
            user_id=update.effective_user.id,
            quiz_datetime=datetime.now(timezone),
            user_feelings=context.user_data["morning_feelings"],
            user_sleeping_hours=context.user_data["morning_sleep_time"],
            db_session=db_session,
            is_going_to_have_training=context.user_data["is_going_to_have_training"],
        )
        await update.message.reply_text(
            text=f"Дякую! Ваші дані збережено: \n "
            f"Ви поспали: {context.user_data['morning_sleep_time']} \n "
            f"Почуваєте себе на {context.user_data['morning_feelings']}! \n "
            f"Тренування сьогодні не планується! \n "
            f"Гарного дня!",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END


async def retrieve_morning_training_time(update, context):
    user_input = update.message.text

    if not is_valid_time(user_input):
        await update.message.reply_text(
            text="Введіть, о которій плануєте почати тренування сьогодні? (Наприклад, '15:00')",
        )
        return MorningQuizConversation.WHEN_GOING_TO_HAVE_TRAINING

    hours, minutes = map(int, user_input.split(":"))
    today = datetime.now()
    expected_training_datetime = today.replace(
        hour=hours, minute=minutes, second=0, microsecond=0
    )

    with next(get_db()) as db_session:
        save_morning_quiz_results(
            user_id=update.effective_user.id,
            quiz_datetime=datetime.now(timezone),
            user_feelings=context.user_data["morning_feelings"],
            user_sleeping_hours=context.user_data["morning_sleep_time"],
            db_session=db_session,
            is_going_to_have_training=context.user_data["is_going_to_have_training"],
            expected_training_datetime=expected_training_datetime,
        )

    with next(get_db()) as db_session:
        create_training_notifications(
            chat_id=update.effective_user.id,
            notification_time=user_input,
            db_session=db_session,
        )

    await update.message.reply_text(
        text=f"Дякую! Ваші дані збережено: \n "
        f"Ви поспали: {context.user_data['morning_sleep_time']} \n "
        f"Почуваєте себе на {context.user_data['morning_feelings']}! \n "
        f"Тренування сьогодні планується о {user_input}! \n "
        f"Гарного дня!",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


morning_quiz_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_morning_quiz, pattern="^morning_quiz$")],
    states={
        MorningQuizConversation.FIRST_QUESTION_ANSWER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, retrieve_morning_feelings)
        ],
        MorningQuizConversation.SECOND_QUESTION_ANSWER: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, retrieve_morning_sleep_hours
            )
        ],
        MorningQuizConversation.IS_GOING_TO_HAVE_TRAINING: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                retrieve_morning_is_going_to_have_training,
            )
        ],
        MorningQuizConversation.WHEN_GOING_TO_HAVE_TRAINING: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, retrieve_morning_training_time
            )
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
