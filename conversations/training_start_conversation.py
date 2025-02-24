from enum import Enum, auto
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from utils import keyboards
import text_constants
from database import get_db
from utils.db_utils import (
    start_user_training, update_training_start_notification, update_pre_training_notification,
    get_training_pdf_message_data,
)
from utils.commands import cancel
from utils.menus import training_menu


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

        with next(get_db()) as db_session:
            training_pdf_message_id, training_pdf_chat_id = get_training_pdf_message_data(update.effective_chat.id, db_session)
        if training_pdf_message_id and training_pdf_chat_id:
            await context.bot.forward_message(
                chat_id=update.effective_chat.id,
                from_chat_id=training_pdf_chat_id,
                message_id=training_pdf_message_id
            )
        else:
            await context.bot.send_document(
                chat_id=update.effective_user.id,
                document=dummy_pdf,
                caption="Ваш файл тренування ще не призначено!",
            )

        await update.message.reply_text(
            "Го го го!! Успіхів у тренуванні, тренування розпочато!",
            reply_markup=keyboards.training_in_progress_keyboard(),
        )
    with next(get_db()) as db_session:
        update_training_start_notification(update.effective_chat.id, db_session)
        update_pre_training_notification(update.effective_chat.id, db_session)
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
