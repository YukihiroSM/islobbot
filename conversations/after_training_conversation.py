from enum import Enum, auto
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
import text_constants
from database import get_db
from utils.db_utils import update_training_after_quiz
from utils.keyboards import (
    default_one_to_ten_keyboard,
    main_menu_keyboard,
    yes_no_keyboard,
)
from utils.commands import cancel


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
        reply_markup=main_menu_keyboard(update.effective_chat.id),
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
