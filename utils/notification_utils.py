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
from utils.logger import get_logger

logger = get_logger(__name__)


async def switch_notifications(update, context):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} is switching notifications")
    context.user_data["menu_state"] = "switch_notifications"
    await update.message.reply_text(
        text=text_constants.NOTIFICATION_TOGGLE_TEXT,
        reply_markup=keyboards.get_notifications_keyboard(user_id),
    )


async def handle_notification_toggle(update, context):
    user_id = update.effective_user.id
    user_input = update.message.text
    logger.info(f"User {user_id} toggling notification: {user_input}")
    
    with next(get_db()) as db_session:
        notification_time_string = user_input.split(" - ")[0]
        try:
            notification = get_user_notification_by_time(
                chat_id=user_id,
                time=notification_time_string,
                db_session=db_session,
            )
            logger.debug(f"Found notification with ID {notification.id} for time {notification_time_string}")
        except DataError as e:
            logger.error(f"Database error when getting notification for user {user_id}: {e}")
            return

        toggle_user_notification(notification_id=notification.id, db_session=db_session)
        logger.info(f"Toggled notification {notification.id} for user {user_id}")
        await context.bot.send_message(
            chat_id=user_id, text=text_constants.SETTINGS_FINISHED
        )
        await switch_notifications(update, context)


async def handle_notification_time_change(update, context):
    user_id = update.effective_user.id
    user_input = update.message.text
    logger.info(f"User {user_id} changing notification time: {user_input}")
    
    with next(get_db()) as db_session:
        notification_time_string = user_input.split(" - ")[0]
        try:
            notification = get_user_notification_by_time(
                chat_id=user_id,
                time=notification_time_string,
                db_session=db_session,
            )
            logger.debug(f"Found notification with ID {notification.id if notification else 'None'} for time {notification_time_string}")
        except DataError as e:
            logger.error(f"Database error when getting notification for user {user_id}: {e}")
            return

        if notification:
            context.user_data["notification_to_change"] = notification.id
            logger.debug(f"Stored notification ID {notification.id} in user_data for changing")
            await update.message.reply_text(
                text=text_constants.ENTER_NEW_NOTIFICATION_TIME_TEXT
            )
        else:
            logger.warning(f"Notification not found for user {user_id} with time {notification_time_string}")
            await update.message.reply_text(text=text_constants.NOTIFICATION_NOT_FOUND)


async def change_user_notification_time(update, context):
    user_id = update.effective_user.id
    time_input = update.message.text
    logger.info(f"User {user_id} entered new notification time: {time_input}")
    
    if not is_valid_morning_time(time_input):
        logger.warning(f"Invalid morning time format entered by user {user_id}: {time_input}")
        await update.message.reply_text(
            text=text_constants.WRONG_MORNING_NOTIFICATION_TIME_FORMAT
        )
        return

    with next(get_db()) as db_session:
        notification_id = context.user_data.get("notification_to_change")
        if notification_id:
            logger.debug(f"Changing time for notification {notification_id} to {time_input}")
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

            logger.debug(f"Next execution datetime for notification {notification_id}: {next_execution_datetime}")
            update_user_notification_time(
                notification_id=notification_id,
                new_time=time_input,
                next_execution_datetime=next_execution_datetime,
                db_session=db_session,
            )
            logger.info(f"Successfully updated notification {notification_id} time to {time_input}")
            await update.message.reply_text(
                text=text_constants.NOTIFICATION_TIME_UPDATED,
                reply_markup=keyboards.notification_configuration_keyboard(),
            )
            del context.user_data["notification_to_change"]
        else:
            logger.warning(f"No notification to change found in user_data for user {user_id}")
            await update.message.reply_text(
                text=text_constants.NOTIFICATION_NOT_FOUND_TEXT
            )
