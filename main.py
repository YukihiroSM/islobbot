import datetime
import logging
from datetime import datetime
from datetime import time as datetime_time
from datetime import timedelta
from enum import Enum, auto

from sqlalchemy.exc import DataError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import conversations
import keyboards
import text_constants
from bot_utils import (
    get_random_motivation_message,
    is_valid_morning_time,
    is_valid_time,
)
from config import ADMIN_CHAT_IDS, BOT_TOKEN, timezone
from conversations.training_start_conversation import handle_training_startup
from database import get_db
from db_utils import (
    add_or_update_user,
    create_training_notifications,
    get_notifications_by_type,
    get_notifications_to_send_by_time,
    get_user_by_chat_id,
    get_user_notification_by_time,
    get_users_with_yesterday_trainings,
    is_user_had_morning_quiz_today,
    is_user_ready_to_use,
    save_morning_quiz_results,
    save_user_notification_preference,
    start_user_training,
    stop_training,
    toggle_user_notification,
    update_notification_sent,
    update_training_after_quiz,
    update_training_notification,
    update_user_full_name,
    update_user_notification_preference_admin_message_sent,
    update_user_notification_preference_next_execution,
    update_user_notification_time,
)
from keyboards import default_one_to_ten_keyboard, main_menu_keyboard, yes_no_keyboard
from models import NotificationType

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


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
                reply_markup=main_menu_keyboard(),
            )


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
    with next(get_db()) as db_session:
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
            chat_id=update.effective_user.id, text="Налаштування успішно застосовано!"
        )
        await switch_notifications(update, context)


async def notification_time_change_menu(update, context):
    context.user_data["menu_state"] = "change_notification_time"
    await update.message.reply_text(
        "Натисніть на сповіщення, щоб змінити його час спрацювання:",
        reply_markup=keyboards.get_notifications_keyboard(update.effective_user.id),
    )


async def handle_notification_time_change(update, context):
    user_input = update.message.text
    with next(get_db()) as db_session:
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
    if not is_valid_morning_time(time_input):
        await update.message.reply_text(
            f"Невірний формат. Введіть час у форматі '08:00' в рамках від 06:00 до 12:00!"
        )
        return

    with next(get_db()) as db_session:
        notification_id = context.user_data.get("notification_to_change")
        if notification_id:

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

            update_user_notification_time(
                notification_id=notification_id,
                new_time=time_input,
                next_execution_datetime=next_execution_datetime,
                db_session=db_session,
            )
            await update.message.reply_text(
                "Час сповіщення успішно оновлено!",
                reply_markup=keyboards.notification_configuration_keyboard(),
            )
            del context.user_data["notification_to_change"]
        else:
            await update.message.reply_text("Помилка: не вдалось знайти сповіщення.")


async def training_menu(update, context):
    context.user_data["menu_state"] = "training_menu"
    await update.message.reply_text(
        "Час поглянути на тренування!", reply_markup=keyboards.training_menu_keyboard()
    )


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    if not "menu_state" in context.user_data:
        await main_menu(update, context)

    # main menu handling
    if user_input == text_constants.TRAINING:
        await training_menu(update, context)

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
        if context.user_data["menu_state"] == "training_menu":
            await main_menu(update, context)

    if user_input == text_constants.CONFIGURE_NOTIFICATIONS:
        await configure_notifications_menu(update, context)

    # Notifications config menu
    if user_input == text_constants.TURN_ON_OFF_NOTIFICATIONS:
        await switch_notifications(update, context)

    if user_input == text_constants.CHANGE_NOTIFICATION_TIME:
        await notification_time_change_menu(update, context)

    # training menu handling

    if (
        context.user_data["menu_state"] == "training_menu"
        and user_input == text_constants.START_TRAINING
    ):
        await handle_training_startup(update, context)

    # handle anything else

    if context.user_data["menu_state"] == "switch_notifications":
        await handle_notification_toggle(update, context)

    if context.user_data["menu_state"] == "change_notification_time":
        if "notification_to_change" in context.user_data:
            await change_user_notification_time(update, context)
        else:
            await handle_notification_time_change(update, context)

    return


async def send_morning_notification(context, user_id, admin_message_datetime):
    morning_notification_text = (
        "Привіт! Час пройти ранкове опитування! Натисни на кнопку, щоб почати"
    )
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=morning_notification_text,
            reply_markup=keyboards.start_morning_quiz_keyboard(),
        )
        return True
    except:
        today = datetime.now(tz=timezone).date()
        if not admin_message_datetime or (
            admin_message_datetime and admin_message_datetime.date() != today
        ):
            for chat_id in ADMIN_CHAT_IDS:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Бот спробував надіслати користувачу {user_id} повідомлення, але користувач обмежив надсилання повідомлень!",
                )
            return False
        return None


async def send_scheduled_message(context: CallbackContext):
    datetime_now = datetime.now(tz=timezone)
    with next(get_db()) as db_session:
        notifications = get_notifications_to_send_by_time(
            current_datetime=datetime_now, db_session=db_session
        )
        for notification in notifications:
            user_id = notification.user.chat_id
            morning_notification_sent = await send_morning_notification(
                context, user_id, notification.admin_warning_sent
            )
            if morning_notification_sent is True:

                last_execution_datetime = datetime_now
                next_execution_datetime = (
                    notification.next_execution_datetime + timedelta(days=1)
                )
                update_user_notification_preference_next_execution(
                    last_execution_datetime=last_execution_datetime,
                    next_execution_datetime=next_execution_datetime,
                    notification_id=notification.id,
                    db_session=db_session,
                )
            elif morning_notification_sent is False:
                update_user_notification_preference_admin_message_sent(
                    db_session=db_session,
                    sent_datetime=datetime_now,
                    notification_id=notification.id,
                )


async def send_after_training_messages(context: CallbackContext):
    datetime_now = datetime.now(tz=timezone)
    yesterday_date = (datetime_now - timedelta(days=1)).date()
    with next(get_db()) as db_session:
        results = get_users_with_yesterday_trainings(db_session)
        users_trainings_to_process = dict()
        for user in results:
            for training in user.trainings:
                if training.training_start_date.date() == yesterday_date:
                    users_trainings_to_process[user.chat_id] = {
                        "training_id": training.id,
                        "training_duration": training.training_duration,
                        "training_start_date": training.training_start_date,
                    }
        await send_after_training_quiz_notifications(
            context, users_trainings_to_process
        )


async def send_after_training_quiz_notifications(context, users_data):
    for user_id, training in users_data.items():
        after_training_notification_text = f"Обєд! Час пройти опитування після тренування {str(training['training_start_date']).split('.')[0]}! Натисни на кнопку, аби розпочати"
        keyboard = [
            [
                InlineKeyboardButton(
                    "Пройти опитування",
                    callback_data=f"after_training_quiz:{training['training_id']}",
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id,
            text=after_training_notification_text,
            reply_markup=reply_markup,
        )


async def send_evening_after_training_motivation_message(context, user_ids):
    for user_id in user_ids:
        message = get_random_motivation_message()
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
        )


async def get_evening_after_training_motivation(context):
    with next(get_db()) as db_session:
        results = get_users_with_yesterday_trainings(db_session)
        user_ids = [user.chat_id for user in results]
        await send_evening_after_training_motivation_message(context, user_ids)


async def send_pre_training_notifications(context, notification):
    try:
        await context.bot.send_message(
            chat_id=notification.user.chat_id,
            text=f"Нагадування про тренування о {notification.notification_time}",
        )
        with next(get_db()) as db_session:
            update_notification_sent(notification.id, db_session)
    except Exception as e:
        print(f"UNABLE TO SEND MESSAGE TO {notification.user.chat_id}, {e}")


async def get_pre_training_notifications(context):
    with next(get_db()) as db_session:
        notifications = get_notifications_by_type(
            notification_type=NotificationType.PRE_TRAINING_REMINDER_NOTIFICATION,
            db_session=db_session,
        )
    for notification in notifications:
        await send_pre_training_notifications(context, notification)


async def send_training_notifications(context, notification):
    try:
        await context.bot.send_message(
            chat_id=notification.user.chat_id,
            text=f"Привіт! Саме час розпочати тренування о {notification.notification_time}",
        )
        with next(get_db()) as db_session:
            update_notification_sent(notification.id, db_session)
    except Exception as e:
        print(f"UNABLE TO SEND MESSAGE TO {notification.user.chat_id}, {e}")


async def get_training_notifications(context):
    with next(get_db()) as db_session:
        notifications = get_notifications_by_type(
            notification_type=NotificationType.TRAINING_REMINDER_NOTIFICATION,
            db_session=db_session,
        )
    for notification in notifications:
        await send_training_notifications(context, notification)


async def send_stop_training_notifications(context, notification):
    try:
        await context.bot.send_message(
            chat_id=notification.user.chat_id,
            text=f"Привіт! Твоє тренування триває вже більше години. Не забув завершити?",
        )
        with next(get_db()) as db_session:
            update_notification_sent(notification.id, db_session)
    except Exception as e:
        print(f"UNABLE TO SEND MESSAGE TO {notification.user.chat_id}, {e}")


async def stop_training_notification(context):
    with next(get_db()) as db_session:
        notifications = get_notifications_by_type(
            notification_type=NotificationType.STOP_TRAINING_NOTIFICATION,
            db_session=db_session,
        )
    for notification in notifications:
        await send_stop_training_notifications(context, notification)


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(conversations.intro_conversation.intro_conv_handler)
    app.add_handler(conversations.morning_quiz_conversation.morning_quiz_conv_handler)
    app.add_handler(
        conversations.training_finish_conversation.training_finish_quiz_conv_handler
    )
    app.add_handler(
        conversations.after_training_conversation.after_training_quiz_conv_handler
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    job_queue = app.job_queue

    # job_queue.run_repeating(send_scheduled_message, interval=10, first=0)
    # after_training_quiz_scheduled_time = datetime_time(
    #     hour=15, minute=0, tzinfo=timezone
    # )
    # job_queue.run_daily(
    #     send_after_training_messages, time=after_training_quiz_scheduled_time
    # )
    #
    # after_training_motivation_time = datetime_time(hour=18, minute=0, tzinfo=timezone)
    # job_queue.run_daily(
    #     get_evening_after_training_motivation, time=after_training_motivation_time
    # )
    #
    # job_queue.run_repeating(get_pre_training_notifications, interval=10, first=0)
    # job_queue.run_repeating(get_training_notifications, interval=10, first=0)
    # job_queue.run_repeating(stop_training_notification, interval=10, first=0)

    app.run_polling()
