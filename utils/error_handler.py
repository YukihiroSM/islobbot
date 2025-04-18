from utils.logger import get_logger

from telegram import Update
from telegram.ext import CallbackContext

from config import ADMIN_CHAT_IDS
from exceptions import UserNotFoundError
import text_constants

logger = get_logger(__name__)


async def error_handler(update: Update, context: CallbackContext):
    try:
        raise context.error
    except UserNotFoundError:
        logger.error(f"User not found! {update.effective_chat.id}")
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text_constants.USER_NOT_FOUND,
            )
    except ValueError as e:
        logger.warning(f"ValueError: {e}")
    except KeyError as e:
        logger.warning(f"KeyError: {e}")
    except Exception as e:
        logger.exception("Unhandled exception")

        if ADMIN_CHAT_IDS:
            for admin_id in ADMIN_CHAT_IDS:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"An unhandled error occurred: {e}",
                )
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text_constants.SOMETHING_GONE_WRONG,
            )
