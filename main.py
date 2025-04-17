import logging
from datetime import datetime, timedelta, time as datetime_time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    MessageHandler,
    filters,
)

import conversations
from utils import keyboards
from utils.bot_utils import (
    get_random_motivation_message,
)
from config import ADMIN_CHAT_IDS, BOT_TOKEN, timezone
from database import get_db
from utils.db_utils import (
    get_notifications_by_type,
    get_notifications_to_send_by_time,
    get_users_with_yesterday_trainings,
    update_notification_sent,
    update_user_notification_preference_admin_message_sent,
    update_user_notification_preference_next_execution,
)
from models import NotificationType
import utils.menus
import text_constants


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


async def send_morning_notification(context, user_id, admin_message_datetime):
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=text_constants.MORNING_NOTIFICATION_TEXT,
            reply_markup=keyboards.start_morning_quiz_keyboard(),
        )
        return True
    except Exception:
        today = datetime.now(tz=timezone).date()
        if not admin_message_datetime or (
            admin_message_datetime and admin_message_datetime.date() != today
        ):
            for chat_id in ADMIN_CHAT_IDS:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text_constants.BOT_UNABLE_TO_SEND_MESSAGE.format(
                        user_id=user_id
                    ),
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
        keyboard = [
            [
                InlineKeyboardButton(
                    text=text_constants.PASS_QUIZ,
                    callback_data=f"after_training_quiz:{training['training_id']}",
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id,
            text=text_constants.AFTER_TRAINING_NOTIFICATION_TEXT.format(
                training_date=str(training["training_start_date"]).split(".")[0]
            ),
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
            text=text_constants.TRAINING_REMINDER_FIRST.format(
                notification_time=notification.notification_time
            ),
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
            text=text_constants.TRAINING_REMINDER_SECOND.format(
                notification_time=notification.notification_time
            ),
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
            text=text_constants.TRAINING_MORE_THEN_HOUR,
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
    app.add_handler(
        conversations.training_start_conversation.training_start_quiz_conv_handler
    )
    app.add_handler(
        conversations.pdf_assignment_conversation.pdf_assignment_conv_handler
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, utils.menus.handle_menu)
    )

    job_queue = app.job_queue

    job_queue.run_repeating(send_scheduled_message, interval=10, first=0)
    after_training_quiz_scheduled_time = datetime_time(
        hour=15, minute=0, tzinfo=timezone
    )
    job_queue.run_daily(
        send_after_training_messages, time=after_training_quiz_scheduled_time
    )

    after_training_motivation_time = datetime_time(hour=18, minute=0, tzinfo=timezone)
    job_queue.run_daily(
        get_evening_after_training_motivation, time=after_training_motivation_time
    )

    job_queue.run_repeating(get_pre_training_notifications, interval=10, first=0)
    job_queue.run_repeating(get_training_notifications, interval=10, first=0)
    job_queue.run_repeating(stop_training_notification, interval=10, first=0)

    app.run_polling()
