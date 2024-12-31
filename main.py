from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot_utils import payment_restricted
from config import BOT_TOKEN
from database import get_db
from db_utils import (
    add_or_update_user,
    get_user_notifications,
    save_user_notification_preference,
    update_user_notification_time,
    update_user_full_name,
    is_user_ready_to_use,
    get_user_notification_by_time,
    toggle_user_notification,
)
from keyboards import main_menu_keyboard
from models import NotificationType
import text_constants
from enum import Enum, auto
import re
import logging
import datetime
import keyboards
from sqlalchemy.exc import DataError


class IntroConversation(Enum):
    NEW_COMER = auto()
    GET_NAME = auto()
    GET_TIME = auto()


def is_valid_time(time_str: str) -> bool:
    try:
        match = re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", time_str)
        min_time = datetime.time(hour=6)
        max_time = datetime.time(hour=12)

        time = datetime.datetime.strptime(time_str, "%H:%M").time()
        if time < min_time or time > max_time:
            return False
        return bool(match)
    except:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_session = next(get_db())
    is_new_user = add_or_update_user(
        update.effective_user.id, update.effective_user.username, db_session
    )

    if is_new_user or not is_user_ready_to_use(update.effective_user.id, db_session):
        await update.message.reply_text(
            "Ласкаво прошу до бота! (Тут має бути якийсь невеличкий опис)"
        )
        await update.message.reply_text("Для початку, введіть своє повне ім'я.")
        return IntroConversation.GET_NAME
    else:
        await update.message.reply_text(
            f"Привіт, {update.effective_user.username}!",
            reply_markup=main_menu_keyboard(),
        )


async def get_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    db_session = next(get_db())
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
    if is_valid_time(time_input):
        db_session = next(get_db())
        save_user_notification_preference(
            chat_id=update.effective_user.id,
            notification_type=NotificationType.MORNING_NOTIFICATION,
            notification_time=time_input,
            db_session=db_session,
        )
        await update.message.reply_text(
            "Супер! Налаштування завершено!", reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            f"Невірний формат. Введіть час у форматі '08:00' в рамках від 06:00 до 12:00!"
        )
        return IntroConversation.GET_TIME


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Операція зупинена.", reply_markup=main_menu_keyboard()
    )

    return ConversationHandler.END


async def settings_menu(update, context):
    context.user_data["menu_state"] = "settings_menu"
    await update.message.reply_text(
        "Меню налаштувань. Оберіть, що ви бажаєте налаштувати:",
        reply_markup=keyboards.settings_menu_keyboard(),
    )


async def configure_notifications_menu(update, context):
    context.user_data["menu_state"] = "notifications_menu"
    await update.message.reply_text(
        "Конфігурація сповіщень. Оберіть, що бажаєте налаштувати:",
        reply_markup=keyboards.notification_configuration_keyboard(),
    )


async def main_menu(update, context):
    context.user_data["menu_state"] = "main_menu"
    await update.message.reply_text(
        "Головне меню:", reply_markup=keyboards.main_menu_keyboard()
    )


async def switch_notifications(update, context):
    context.user_data["menu_state"] = "switch_notifications"
    await update.message.reply_text(
        "Натисніть на сповіщення, щоб увімкнути / вимкнути:",
        reply_markup=keyboards.get_notifications_keyboard(update.effective_user.id),
    )


async def handle_notification_toggle(update, context):
    user_input = update.message.text
    db_session = next(get_db())
    notification_time_string = user_input.split(" - ")[0]
    try:
        notification = get_user_notification_by_time(
            chat_id=update.effective_user.id,
            time=notification_time_string,
            db_session=db_session,
        )
    except DataError:
        return

    toggle_user_notification(notification_id=notification.id, db_session=db_session)
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Налаштування успішно застосовано!"
    )
    await switch_notifications(update, context)


async def notification_time_change_menu(update, context):
    context.user_data["menu_state"] = "change_notification_time"
    await update.message.reply_text(
        "Натисніть на сповіщення, щоб змінити його час спрацювання:",
        reply_markup=keyboards.get_notifications_keyboard(update.effective_user.id)
    )


async def handle_notification_time_change(update, context):
    user_input = update.message.text
    db_session = next(get_db())
    notification_time_string = user_input.split(" - ")[0]
    try:
        notification = get_user_notification_by_time(
            chat_id=update.effective_user.id,
            time=notification_time_string,
            db_session=db_session,
        )
    except DataError:
        return

    if notification:
        context.user_data["notification_to_change"] = notification.id
        await update.message.reply_text(
            "Введіть новий час для цього сповіщення у форматі '08:00'. Час має бути між 06:00 та 12:00."
        )
    else:
        await update.message.reply_text(
            "Сповіщення не знайдено. Спробуйте ще раз або поверніться назад."
        )


async def change_user_notification_time(update, context):
    time_input = update.message.text
    if not is_valid_time(time_input):
        await update.message.reply_text(
            f"Невірний формат. Введіть час у форматі '08:00' в рамках від 06:00 до 12:00!"
        )
        return

    db_session = next(get_db())
    notification_id = context.user_data.get("notification_to_change")
    if notification_id:
        update_user_notification_time(
            notification_id=notification_id,
            new_time=time_input,
            db_session=db_session,
        )
        await update.message.reply_text(
            "Час сповіщення успішно оновлено!", reply_markup=keyboards.notification_configuration_keyboard()
        )
        del context.user_data["notification_to_change"]
    else:
        await update.message.reply_text("Помилка: не вдалось знайти сповіщення.")


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    if not "menu_state" in context.user_data:
        await main_menu(update, context)

    # main menu handling
    if user_input == text_constants.START_TRAINING:
        context.user_data["menu_state"] = "start_training"
        await update.message.reply_text("Starting training")

    if user_input == text_constants.SETTINGS:
        await settings_menu(update, context)

    # settings menu handling

    if user_input == text_constants.GO_BACK:
        if context.user_data["menu_state"] == "settings_menu":
            await main_menu(update, context)
        if context.user_data["menu_state"] == "notifications_menu":
            await settings_menu(update, context)
        if context.user_data["menu_state"] == "switch_notifications":
            await configure_notifications_menu(update, context)
        if context.user_data["menu_state"] == "change_notification_time":
            await configure_notifications_menu(update, context)

    if user_input == text_constants.CONFIGURE_NOTIFICATIONS:
        await configure_notifications_menu(update, context)

    # Notifications config menu
    if user_input == text_constants.TURN_ON_OFF_NOTIFICATIONS:
        await switch_notifications(update, context)

    if user_input == text_constants.CHANGE_NOTIFICATION_TIME:
        await notification_time_change_menu(update, context)

    # handle anything else
    if context.user_data["menu_state"] == "switch_notifications":
        await handle_notification_toggle(update, context)

    if context.user_data["menu_state"] == "change_notification_time":
        if "notification_to_change" in context.user_data:
            await change_user_notification_time(update, context)
        else:
            await handle_notification_time_change(update, context)


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    app.add_handler(intro_conv_handler)

    app.run_polling()
