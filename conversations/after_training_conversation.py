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
from utils.logger import get_logger

logger = get_logger(__name__)


class AfterTrainingQuiz(Enum):
    FIRST_QUESTION_ANSWER = auto()
    SECOND_QUESTION_ANSWER = auto()


async def run_after_training_quiz(update, context):
    query = update.callback_query
    query.answer()

    callback_data = query.data
    training_id = callback_data.split(":")[1]
    user_id = update.effective_user.id
    
    logger.info(f"User {user_id} starting after-training quiz for training ID: {training_id}")
    context.user_data["training_id"] = training_id

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text_constants.STRESS_LEVEL_USER_MARK,
        reply_markup=default_one_to_ten_keyboard(),
    )
    return AfterTrainingQuiz.FIRST_QUESTION_ANSWER


async def retrieve_after_training_first_answer(update, context):
    input_text = update.message.text
    user_id = update.effective_user.id
    
    logger.debug(f"User {user_id} provided stress level: {input_text}")

    if input_text not in text_constants.ONE_TO_TEN_MARKS:
        logger.warning(f"User {user_id} provided invalid stress level: {input_text}")
        await update.message.reply_text(
            text=text_constants.STRESS_LEVEL_USER_MARK,
            reply_markup=default_one_to_ten_keyboard(),
        )
        return AfterTrainingQuiz.FIRST_QUESTION_ANSWER

    context.user_data["after_training_stress_level"] = input_text
    await update.message.reply_text(
        text=text_constants.DO_YOU_HAVE_SORENESS, reply_markup=yes_no_keyboard()
    )
    return AfterTrainingQuiz.SECOND_QUESTION_ANSWER


async def retrieve_after_training_second_answer(update, context):
    input_text = update.message.text
    user_id = update.effective_user.id
    
    logger.debug(f"User {user_id} provided soreness level: {input_text}")

    if input_text not in text_constants.YES_NO_BUTTONS:
        logger.warning(f"User {user_id} provided invalid soreness level: {input_text}")
        await update.message.reply_text(
            text=text_constants.DO_YOU_HAVE_SORENESS, reply_markup=yes_no_keyboard()
        )
        return AfterTrainingQuiz.SECOND_QUESTION_ANSWER

    with next(get_db()) as db_session:
        update_training_after_quiz(
            training_id=context.user_data["training_id"],
            stress_level=context.user_data["after_training_stress_level"],
            soreness=input_text,
            db_session=db_session,
        )
    logger.info(f"User {user_id} finished after-training quiz for training ID: {context.user_data['training_id']}")
    await update.message.reply_text(
        text=text_constants.THANKS_FOR_PASSING_QUIZ,
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
