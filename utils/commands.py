from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

import conversations
from database import get_db
from utils.db_utils import (
    add_or_update_user,
    is_user_ready_to_use,
)
from utils.keyboards import main_menu_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with next(get_db()) as db_session:
        context.user_data["menu_state"] = "starting_using_bot"
        is_new_user = add_or_update_user(
            update.effective_user.id, update.effective_user.username, db_session
        )

        if is_new_user or not is_user_ready_to_use(
            update.effective_user.id, db_session
        ):
            await update.message.reply_text(
                "Ласкаво прошу до бота! (Тут має бути якийсь невеличкий опис)"
            )
            await update.message.reply_text("Для початку, введіть своє повне ім'я.")
            return conversations.intro_conversation.IntroConversation.GET_NAME
        else:
            await update.message.reply_text(
                f"Привіт, {update.effective_user.username}!",
                reply_markup=main_menu_keyboard(update.effective_chat.id),
            )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Операція зупинена.", reply_markup=main_menu_keyboard(update.effective_chat.id)
    )

    return ConversationHandler.END
