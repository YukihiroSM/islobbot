import logging

from telegram import Update
from telegram.ext import CallbackContext

from config import ADMIN_CHAT_IDS
from exceptions import UserNotFoundError

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: CallbackContext):
    try:
        raise context.error
    except UserNotFoundError:
        logger.error(msg=f"User not found! {update.effective_chat.id}")
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Не знайдено вашого користувача в системі!",
            )
    except ValueError as e:
        logger.warning(f"ValueError: {e}")
    except KeyError as e:
        logger.warning(f"KeyError: {e}")
    except Exception as e:
        logger.error(msg="Unhandled exception:", exc_info=e)

        if ADMIN_CHAT_IDS:
            for admin_id in ADMIN_CHAT_IDS:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"An unhandled error occurred: {e}",
                )
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="An unexpected error occurred. Please try again.",
            )
