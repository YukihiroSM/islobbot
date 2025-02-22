from datetime import datetime
from datetime import timedelta
from enum import Enum, auto
from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from utils.bot_utils import is_valid_morning_time
from config import timezone
from database import get_db
from utils.db_utils import (
    save_user_notification_preference,
    update_user_full_name,
)
from utils.keyboards import main_menu_keyboard
from utils.commands import cancel, start
from models import NotificationType


class IntroConversation(Enum):
    NEW_COMER = auto()
    GET_NAME = auto()
    GET_TIME = auto()


async def get_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    with next(get_db()) as db_session:
        update_user_full_name(
            chat_id=update.effective_chat.id, full_name=name, db=db_session
        )
        await update.message.reply_text(
            f"Дякую, {name}! Тепер налаштуємо сповіщення. Введіть бажаний час для ранкового сповіщення. "
            f"Його потрібно увести в форматі '08:00'. "
            f"Введіть будь-який зручний час в рамках від 06:00 до 12:00! ",
        )
        return IntroConversation.GET_TIME


async def get_morning_notification_time(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    time_input = update.message.text
    if is_valid_morning_time(time_input):
        with next(get_db()) as db_session:
            hours, minutes = map(int, time_input.split(":")[:2])

            datetime_now = datetime.now(tz=timezone)
            datetime_time_input = timezone.localize(
                datetime(
                    datetime_now.year,
                    datetime_now.month,
                    datetime_now.day,
                    hours,
                    minutes,
                )
            )
            if datetime_now < datetime_time_input:
                next_execution_datetime = datetime_time_input
            else:
                next_execution_datetime = datetime_time_input + timedelta(days=1)
            save_user_notification_preference(
                chat_id=update.effective_user.id,
                notification_type=NotificationType.MORNING_NOTIFICATION,
                notification_time=time_input,
                next_execution_datetime=next_execution_datetime,
                db_session=db_session,
            )

            await update.message.reply_text(
                "Супер! Налаштування завершено! Тепер очікуй від бота сповіщень у вказаний час!",
                reply_markup=main_menu_keyboard(update.effective_chat.id),
            )
            return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Невірний формат. Введіть час у форматі '08:00' в рамках від 06:00 до 12:00!"
        )
        return IntroConversation.GET_TIME


intro_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        IntroConversation.GET_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_name)
        ],
        IntroConversation.GET_TIME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, get_morning_notification_time
            )
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
