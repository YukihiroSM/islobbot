from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from bot_utils import payment_restricted
from config import BOT_TOKEN
from database import get_db
from db_utils import (
    add_or_update_user,
    get_user_notifications,
    save_user_notification_preference, update_user_notification_time,
)
from models import NotificationType
import text_constants


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_session = next(get_db())
    is_new_user = add_or_update_user(update.effective_user.id, update.effective_user.username, db_session)
    if is_new_user:
        await new_comer(update, context)
    else:
        keyboard = [
            [InlineKeyboardButton(text_constants.START_TRAINING, callback_data="start_training")],
            [InlineKeyboardButton(text_constants.SETTINGS, callback_data="settings_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Привіт, {update.effective_user.username}!",
            reply_markup=reply_markup,
        )
    context.user_data["current_menu"] = "main_menu"


async def new_comer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Ласкаво прошу до бота! (Тут має бути якийсь невеличкий опис)"
    )

    keyboard = [
        [InlineKeyboardButton(f"{hour:02d}:{minute:02d}", callback_data=f"new_time_{hour:02d}:{minute:02d}")]
        for hour in range(8, 13) for minute in (0, 30)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Налаштуємо сповіщення. Оберіть бажаний час для ранкового повідомлення: ",
        reply_markup=reply_markup,
    )


@payment_restricted
async def save_new_notification_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save the updated notification time."""
    query = update.callback_query
    await query.answer()

    new_time = query.data.split("_")[2]

    db_session = next(get_db())
    save_user_notification_preference(
        chat_id=update.effective_user.id,
        notification_type=NotificationType.MORNING_NOTIFICATION,
        notification_time=new_time,
        db_session=db_session
    )
    await main_menu(update, context)


@payment_restricted
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the main menu."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(text_constants.START_TRAINING, callback_data="start_training")],
        [InlineKeyboardButton(text_constants.SETTINGS, callback_data="settings_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Головне меню:", reply_markup=reply_markup)


@payment_restricted
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the settings menu."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(text_constants.CONFIGURE_NOTIFICATIONS, callback_data="configure_notifications")],
        [InlineKeyboardButton(text_constants.GO_BACK, callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Меню налаштувань:", reply_markup=reply_markup)


@payment_restricted
async def view_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user's notifications."""
    query = update.callback_query
    await query.answer()

    db_session = next(get_db())
    user_id = update.effective_user.id

    notifications = get_user_notifications(user_id, db_session)

    if not notifications:
        await query.edit_message_text("У вас ще немає налаштованих сповіщень!")
        return

    keyboard = [
        [InlineKeyboardButton(f"{n.notification_type.value}: {n.notification_time}", callback_data=f"edit_{n.id}")]
        for n in notifications
    ]
    keyboard.append([InlineKeyboardButton(text_constants.GO_BACK, callback_data="settings_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Ваші сповіщення:", reply_markup=reply_markup)


@payment_restricted
async def update_notification_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Allow the user to update the time of a selected notification."""
    query = update.callback_query
    await query.answer()

    notification_id = query.data.split("_")[1]
    context.user_data["notification_id"] = notification_id

    keyboard = [
        [InlineKeyboardButton(f"{hour:02d}:{minute:02d}", callback_data=f"time_{hour:02d}:{minute:02d}")]
        for hour in range(8, 13) for minute in (0, 30)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Оберіть новий час:", reply_markup=reply_markup)


@payment_restricted
async def save_notification_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save the updated notification time."""
    query = update.callback_query
    await query.answer()

    new_time = query.data.split("_")[1]
    notification_id = context.user_data.get("notification_id")

    db_session = next(get_db())
    update_user_notification_time(
        notification_id=notification_id,
        new_time=new_time,
        db_session=db_session
    )
    await view_notifications(update, context)


@payment_restricted
async def start_training(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the training process by asking initial questions."""
    query = update.callback_query
    await query.answer()

    # Initialize training state
    context.user_data["training_state"] = "asking_questions"
    context.user_data["training_data"] = {}
    await query.edit_message_text("Питання 1: Яка ваша головна мета для цього тренування?")


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(settings_menu, pattern="^settings_menu$"))
    app.add_handler(CallbackQueryHandler(view_notifications, pattern="^configure_notifications$"))
    app.add_handler(CallbackQueryHandler(update_notification_time, pattern="^edit_.*$"))
    app.add_handler(CallbackQueryHandler(save_notification_time, pattern="^time_.*$"))
    app.add_handler(CallbackQueryHandler(save_new_notification_time, pattern="^new_time_.*$"))
    app.add_handler(CallbackQueryHandler(start_training, pattern="^start_training$"))

    app.run_polling()
