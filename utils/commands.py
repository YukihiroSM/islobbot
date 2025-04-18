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
import text_constants
from utils.logger import get_logger

logger = get_logger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    logger.info(f"Start command received from user {user_id} (@{username})")
    
    with next(get_db()) as db_session:
        context.user_data["menu_state"] = "starting_using_bot"
        is_new_user = add_or_update_user(
            user_id, username, db_session
        )

        if is_new_user or not is_user_ready_to_use(
            user_id, db_session
        ):
            logger.info(f"New user {user_id} (@{username}) starting introduction conversation")
            await update.message.reply_text(text=text_constants.BOT_DESCRIPTION)
            await update.message.reply_text(text=text_constants.NAME_REQUEST)
            return conversations.intro_conversation.IntroConversation.GET_NAME
        else:
            logger.info(f"Existing user {user_id} (@{username}) returned to bot")
            await update.message.reply_text(
                text=text_constants.FIRST_GREETING.format(
                    username=username
                ),
                reply_markup=main_menu_keyboard(update.effective_chat.id),
            )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} canceled current operation")
    await update.message.reply_text(
        "Операція зупинена.", reply_markup=main_menu_keyboard(update.effective_chat.id)
    )

    return ConversationHandler.END
