from datetime import datetime
from enum import Enum, auto
from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from utils import keyboards
import text_constants
from utils.bot_utils import (
    is_valid_time,
)
from config import timezone
from database import get_db
from utils.db_utils import (
    create_training_notifications,
    is_user_had_morning_quiz_today,
    save_morning_quiz_results,
)
from utils.keyboards import main_menu_keyboard
from utils.commands import cancel


class MorningQuizConversation(Enum):
    FIRST_QUESTION_ANSWER = auto()
    SECOND_QUESTION_ANSWER = auto()
    WEIGHT_QUESTION_ANSWER = auto()
    IS_GOING_TO_HAVE_TRAINING = auto()
    WHEN_GOING_TO_HAVE_TRAINING = auto()


async def start_morning_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with next(get_db()) as db_session:
        if is_user_had_morning_quiz_today(
            chat_id=update.effective_user.id, db_session=db_session
        ):
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=text_constants.QUIZ_ALREADY_PASSED,
                reply_markup=main_menu_keyboard(update.effective_chat.id),
            )
            return ConversationHandler.END

        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=text_constants.HOW_DO_YOU_FEEL,
            reply_markup=keyboards.default_one_to_ten_keyboard(),
        )
        return MorningQuizConversation.FIRST_QUESTION_ANSWER


async def retrieve_morning_feelings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_text = update.message.text
    if not input_text.isnumeric() or not (1 <= int(input_text) <= 10):
        await update.message.reply_text(
            text=text_constants.HOW_DO_YOU_FEEL_EXPLAINED,
            reply_markup=keyboards.default_one_to_ten_keyboard(),
        )
        return MorningQuizConversation.FIRST_QUESTION_ANSWER

    context.user_data["morning_feelings"] = input_text

    await update.message.reply_text(
        text=text_constants.HOW_MUCH_SLEEP,
    )
    return MorningQuizConversation.SECOND_QUESTION_ANSWER


async def retrieve_morning_sleep_hours(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    input_text = update.message.text

    if not is_valid_time(input_text):
        await update.message.reply_text(
            text=text_constants.HOW_MUCH_SLEEP,
        )
        return MorningQuizConversation.SECOND_QUESTION_ANSWER

    context.user_data["morning_sleep_time"] = input_text

    await update.message.reply_text(
        text=text_constants.USER_WEIGHT,
    )
    return MorningQuizConversation.WEIGHT_QUESTION_ANSWER


async def retrieve_user_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_text = update.message.text

    if not input_text.isnumeric():
        await update.message.reply_text(
            text=text_constants.USER_WEIGHT,
        )
        return MorningQuizConversation.WEIGHT_QUESTION_ANSWER

    context.user_data["user_weight"] = input_text

    await update.message.reply_text(
        text=text_constants.IS_GOING_TO_TRAIN,
        reply_markup=keyboards.yes_no_keyboard(),
    )
    return MorningQuizConversation.IS_GOING_TO_HAVE_TRAINING


async def retrieve_morning_is_going_to_have_training(update, context):
    user_input = update.message.text

    if user_input not in text_constants.YES_NO_BUTTONS:
        await update.message.reply_text(
            text=text_constants.IS_GOING_TO_TRAIN,
            reply_markup=keyboards.yes_no_keyboard(),
        )
        return MorningQuizConversation.IS_GOING_TO_HAVE_TRAINING

    context.user_data["is_going_to_have_training"] = user_input

    if user_input == text_constants.YES_NO_BUTTONS[0]:
        await update.message.reply_text(
            text=text_constants.WHEN_GOING_TO_TRAIN,
        )
        return MorningQuizConversation.WHEN_GOING_TO_HAVE_TRAINING

    with next(get_db()) as db_session:
        save_morning_quiz_results(
            user_id=update.effective_user.id,
            quiz_datetime=datetime.now(timezone),
            user_feelings=context.user_data["morning_feelings"],
            user_sleeping_hours=context.user_data["morning_sleep_time"],
            user_weight=context.user_data["user_weight"],
            db_session=db_session,
            is_going_to_have_training=context.user_data["is_going_to_have_training"],
        )
        await update.message.reply_text(
            text=text_constants.MORNING_QUIZ_FINAL.format(
                hours_amount=context.user_data["morning_sleep_time"],
                user_weight=context.user_data["user_weight"],
                feeling_mark=context.user_data["morning_feelings"],
            ),
            reply_markup=main_menu_keyboard(update.effective_chat.id),
        )
        return ConversationHandler.END


async def retrieve_morning_training_time(update, context):
    user_input = update.message.text

    if not is_valid_time(user_input):
        await update.message.reply_text(
            text=text_constants.WHEN_GOING_TO_TRAIN,
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
            user_weight=context.user_data["user_weight"],
            expected_training_datetime=expected_training_datetime,
        )

    with next(get_db()) as db_session:
        create_training_notifications(
            chat_id=update.effective_user.id,
            notification_time=user_input,
            db_session=db_session,
        )

    await update.message.reply_text(
        text=text_constants.MORNING_QUIZ_FINAL_WITH_TRAINING.format(
            hours_amount=context.user_data["morning_sleep_time"],
            feeling_mark=context.user_data["morning_feelings"],
            user_weight=context.user_data["user_weight"],
            training_time=expected_training_datetime.time(),
        ),
        reply_markup=main_menu_keyboard(update.effective_chat.id),
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
        MorningQuizConversation.WEIGHT_QUESTION_ANSWER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, retrieve_user_weight)
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
