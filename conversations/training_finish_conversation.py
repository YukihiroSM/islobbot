import logging
from enum import Enum, auto
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from utils import keyboards
import text_constants
from utils.bot_utils import get_random_motivation_message
from config import ADMIN_CHAT_IDS
from database import get_db
from utils.db_utils import (
    get_user_by_chat_id,
    stop_training,
    update_training_notification,
)
from utils.commands import cancel
from utils.menus import training_menu, main_menu


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
