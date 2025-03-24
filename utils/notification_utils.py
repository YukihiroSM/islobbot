from datetime import datetime, timedelta

from psycopg2 import DataError

from config import timezone
from database import get_db
from utils import keyboards
from utils.bot_utils import is_valid_morning_time
from utils.db_utils import (
    get_user_notification_by_time,
    toggle_user_notification,
    update_user_notification_time,
)
import text_constants


async def switch_notifications(update, context):
    context.user_data["menu_state"] = "switch_notifications"
    await update.message.reply_text(
        text=text_constants.NOTIFICATION_TOGGLE_TEXT,
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
            chat_id=update.effective_user.id, text=text_constants.SETTINGS_FINISHED
        )
        await switch_notifications(update, context)


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
                text=text_constants.ENTER_NEW_NOTIFICATION_TIME_TEXT
            )
        else:
            await update.message.reply_text(text=text_constants.NOTIFICATION_NOT_FOUND)


async def change_user_notification_time(update, context):
    time_input = update.message.text
    if not is_valid_morning_time(time_input):
        await update.message.reply_text(
            text=text_constants.WRONG_MORNING_NOTIFICATION_TIME_FORMAT
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
                text=text_constants.NOTIFICATION_TIME_UPDATED,
                reply_markup=keyboards.notification_configuration_keyboard(),
            )
            del context.user_data["notification_to_change"]
        else:
            await update.message.reply_text(
                text=text_constants.NOTIFICATION_NOT_FOUND_TEXT
            )
