import re
from enum import Enum, auto
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import utils.db_utils
from utils import keyboards
import text_constants
from database import get_db
from utils.db_utils import get_training_pdf_message_data
from utils.commands import cancel


class PDFAssignment(Enum):
    HANDLE_USER_CHOICE = auto()
    HANDLE_FILE_MESSAGE = auto()


async def choose_user(update, context):
    await update.message.reply_text(
        text=text_constants.CHOOSE_USER,
        reply_markup=keyboards.pdf_user_list_keyboard(),
    )
    return PDFAssignment.HANDLE_USER_CHOICE


async def handle_user_choice(update, context):
    input_text = update.message.text
    pattern = r"^([\w\s]+) \((\w+)\) - (\d+) action:(\w+)$"
    match = re.match(pattern, input_text)
    if match:
        full_name = match.group(1)
        username = match.group(2)
        user_id = match.group(3)
        action = match.group(4)
        context.user_data["pdf_user_id"] = user_id
        await update.message.reply_text(
            text=text_constants.UPDATING_PDF.format(
                full_name=full_name, username=username
            ),
        )
        return PDFAssignment.HANDLE_FILE_MESSAGE
    else:
        await update.message.reply_text(text=text_constants.UNABLE_TO_RECEIVE_USER_DATA)
        return ConversationHandler.END


async def handle_file_message(update, context):
    pdf_user_id = context.user_data.get("pdf_user_id")
    if not pdf_user_id:
        await update.message.reply_text(
            text=text_constants.SOMETHING_GONE_WRONG,
            reply_markup=keyboards.main_menu_keyboard(update.effective_chat.id),
        )
        return ConversationHandler.END
    message_id = update.message.id
    chat_id = update.effective_chat.id
    with next(get_db()) as db_session:
        utils.db_utils.set_training_pdf_message_id(
            pdf_user_id=pdf_user_id,
            message_id=message_id,
            chat_id=chat_id,
            db_session=db_session,
        )

    with next(get_db()) as db_session:
        training_pdf_message_id, training_pdf_chat_id = get_training_pdf_message_data(
            pdf_user_id, db_session
        )

    await context.bot.send_message(
        chat_id=pdf_user_id, text=text_constants.NEW_TRAINING_FILE
    )
    await context.bot.forward_message(
        chat_id=pdf_user_id,
        from_chat_id=training_pdf_chat_id,
        message_id=training_pdf_message_id,
    )

    await update.message.reply_text(
        text=text_constants.PDF_FILE_ASSIGNED,
        reply_markup=keyboards.main_menu_keyboard(update.effective_chat.id),
    )
    return ConversationHandler.END


pdf_assignment_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.TEXT & filters.Regex(f"^{text_constants.TRAINING_PDF}$"),
            choose_user,
        )
    ],
    states={
        PDFAssignment.HANDLE_USER_CHOICE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                handle_user_choice,
            )
        ],
        PDFAssignment.HANDLE_FILE_MESSAGE: [
            MessageHandler(
                filters.ATTACHMENT & ~filters.COMMAND,
                handle_file_message,
            )
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
