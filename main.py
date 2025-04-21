import datetime
from datetime import timedelta, time as datetime_time

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
    get_custom_notifications_to_send,
    update_custom_notification_sent,
    update_user_stats_counter,
)
from models import NotificationType, CustomNotification, User
import utils.menus
import text_constants
from utils.logger import get_logger
from capture_statistics_image import generate_statistics_image

logger = get_logger(__name__)

async def send_morning_notification(context, user_id, admin_message_datetime):
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=text_constants.MORNING_NOTIFICATION_TEXT,
            reply_markup=keyboards.start_morning_quiz_keyboard(),
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send morning notification to user {user_id}: {e}")
        today = datetime.datetime.now(tz=timezone).date()
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
    datetime_now = datetime.datetime.now(tz=timezone)
    logger.info(f"Running scheduled message job at {datetime_now}")
    with next(get_db()) as db_session:
        notifications = get_notifications_to_send_by_time(
            current_datetime=datetime_now, db_session=db_session
        )
        logger.debug(f"Found {len(notifications)} notifications to send")
        for notification in notifications:
            user_id = notification.user.chat_id
            logger.info(f"Sending morning notification to user {user_id}")
            morning_notification_sent = await send_morning_notification(
                context, user_id, notification.admin_warning_sent
            )
            if morning_notification_sent is True:
                last_execution_datetime = datetime_now
                next_execution_datetime = (
                    notification.next_execution_datetime + timedelta(days=1)
                )
                logger.debug(f"Updating notification {notification.id} next execution to {next_execution_datetime}")
                update_user_notification_preference_next_execution(
                    last_execution_datetime=last_execution_datetime,
                    next_execution_datetime=next_execution_datetime,
                    notification_id=notification.id,
                    db_session=db_session,
                )
            elif morning_notification_sent is False:
                logger.warning(f"Failed to send notification to user {user_id}, updating admin message sent")
                update_user_notification_preference_admin_message_sent(
                    db_session=db_session,
                    sent_datetime=datetime_now,
                    notification_id=notification.id,
                )

async def send_after_training_messages(context: CallbackContext):
    datetime_now = datetime.datetime.now(tz=timezone)
    yesterday_date = (datetime_now - timedelta(days=1)).date()
    logger.info(f"Sending after training messages for {yesterday_date}")
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
        logger.info(f"Found {len(users_trainings_to_process)} users with trainings to process")
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
        logger.info(f"Sending pre-training notification to user {notification.user.chat_id}")
        await context.bot.send_message(
            chat_id=notification.user.chat_id,
            text=text_constants.TRAINING_REMINDER_FIRST.format(
                notification_time=notification.notification_time
            ),
        )
        with next(get_db()) as db_session:
            update_notification_sent(notification.id, db_session)
    except Exception as e:
        logger.error(f"Unable to send message to {notification.user.chat_id}: {e}")

async def send_training_notifications(context, notification):
    try:
        logger.info(f"Sending training notification to user {notification.user.chat_id}")
        await context.bot.send_message(
            chat_id=notification.user.chat_id,
            text=text_constants.TRAINING_REMINDER_SECOND.format(
                notification_time=notification.notification_time
            ),
        )
        with next(get_db()) as db_session:
            update_notification_sent(notification.id, db_session)
    except Exception as e:
        logger.error(f"Unable to send message to {notification.user.chat_id}: {e}")

async def send_stop_training_notifications(context, notification):
    try:
        logger.info(f"Sending stop training notification to user {notification.user.chat_id}")
        await context.bot.send_message(
            chat_id=notification.user.chat_id,
            text=text_constants.TRAINING_MORE_THEN_HOUR,
        )
        with next(get_db()) as db_session:
            update_notification_sent(notification.id, db_session)
    except Exception as e:
        logger.error(f"Unable to send message to {notification.user.chat_id}: {e}")

async def send_custom_notification(context, notification):
    try:
        logger.info(f"Sending custom notification {notification.id} to user {notification.user.chat_id}")
        # Get the associated custom notification
        with next(get_db()) as db_session:
            custom_notification = (
                db_session.query(CustomNotification)
                .filter_by(notification_preference_id=notification.id, is_active=True)
                .first()
            )
            
            if not custom_notification:
                return
                
            message = custom_notification.notification_message or text_constants.DEFAULT_CUSTOM_NOTIFICATION_MESSAGE
            
            # Include the notification name in the message
            full_message = f"{custom_notification.notification_name}\n\n{message}"
            
            await context.bot.send_message(
                chat_id=notification.user.chat_id,
                text=full_message,
            )
            
            # Mark as sent but don't deactivate - it will be sent again tomorrow
            update_notification_sent(notification.id, db_session)
    except Exception as e:
        logger.error(f"Unable to send custom notification to {notification.user.chat_id}: {e}")
        for chat_id in ADMIN_CHAT_IDS:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text_constants.BOT_UNABLE_TO_SEND_MESSAGE.format(
                    user_id=notification.user.chat_id
                ),
            )

async def get_custom_notifications(context):
    with next(get_db()) as db_session:
        notifications = get_notifications_by_type(
            notification_type=NotificationType.CUSTOM_NOTIFICATION,
            db_session=db_session,
        )
    for notification in notifications:
        await send_custom_notification(context, notification)

async def send_custom_notifications(context: CallbackContext):
    """Send custom notifications to users."""
    with next(get_db()) as db_session:
        notifications = get_custom_notifications_to_send(db_session=db_session)
        for notification in notifications:
            try:
                # Include the notification name in the message
                full_message = f"{notification.notification_name}\n\n{notification.notification_message or text_constants.DEFAULT_CUSTOM_NOTIFICATION_MESSAGE}"
                
                await context.bot.send_message(
                    chat_id=notification.user.chat_id,
                    text=full_message,
                )
                
                # Mark as sent and update next execution time
                update_custom_notification_sent(notification.id, db_session)
            except Exception as e:
                logger.error(f"Unable to send custom notification to {notification.user.chat_id}: {e}")

async def get_pre_training_notifications(context):
    logger.info("Getting pre-training notifications")
    with next(get_db()) as db_session:
        notifications = get_notifications_by_type(
            notification_type=NotificationType.PRE_TRAINING_REMINDER_NOTIFICATION,
            db_session=db_session,
        )
    logger.debug(f"Found {len(notifications)} pre-training notifications to send")
    for notification in notifications:
        await send_pre_training_notifications(context, notification)


async def get_training_notifications(context):
    logger.info("Getting training notifications")
    with next(get_db()) as db_session:
        notifications = get_notifications_by_type(
            notification_type=NotificationType.TRAINING_REMINDER_NOTIFICATION,
            db_session=db_session,
        )
    logger.debug(f"Found {len(notifications)} training notifications to send")
    for notification in notifications:
        await send_training_notifications(context, notification)


async def stop_training_notification(context):
    logger.info("Getting stop training notifications")
    with next(get_db()) as db_session:
        notifications = get_notifications_by_type(
            notification_type=NotificationType.STOP_TRAINING_NOTIFICATION,
            db_session=db_session,
        )
    logger.debug(f"Found {len(notifications)} stop training notifications to send")
    for notification in notifications:
        await send_stop_training_notifications(context, notification)

async def send_weekly_statistics(context: CallbackContext):
    """
    Schedule individual jobs for each user to generate and send statistics.
    Every 4th time (4, 8, 12, 16...), send monthly statistics instead.
    
    Runs every Monday at 12:00 Kyiv time.
    """
    current_date = datetime.datetime.now(tz=timezone)
    
    # Since we're using run_daily with days=[0], this check is redundant
    # but keeping it as an extra safeguard
    if current_date.weekday() != 0:  # 0 is Monday
        logger.warning(f"Weekly statistics job ran on non-Monday: {current_date}")
        return
    
    logger.info(f"Running scheduled statistics job at {current_date}")
    
    # Get all active users
    with next(get_db()) as db_session:
        users = db_session.query(User).filter(User.is_active).all()
        
        if not users:
            logger.warning("No active users found for sending statistics")
            return
            
        logger.info(f"Found {len(users)} active users for sending statistics")
        
        # Schedule individual jobs for each user with a small delay between them
        delay = 0
        for user in users:
            # Schedule a job to process this user's statistics
            # Use a small delay between users to avoid overloading the system
            context.job_queue.run_once(
                process_user_statistics,
                delay,
                data={"user_id": user.id, "chat_id": user.chat_id}
            )
            # Increment delay for the next user (2 seconds between users)
            delay += 2
            
        logger.info(f"Scheduled statistics generation for {len(users)} users")


async def process_user_statistics(context: CallbackContext):
    """Process statistics for a single user"""
    job_data = context.job.data
    user_id = job_data["user_id"]
    chat_id = job_data["chat_id"]
    
    try:
        chat_id = int(chat_id)
        logger.info(f"Processing statistics for user {chat_id}")
        
        # Use a new database session
        with next(get_db()) as db_session:
            # Update the user's stats counter and determine if this is a monthly cycle
            is_monthly, counter = update_user_stats_counter(user_id, db_session)
            
            # Set period and date range based on counter
            period = "monthly" if is_monthly else "weekly"
            end_date = datetime.datetime.now(tz=timezone)
            
            # For weekly stats, use last 7 days; for monthly stats, use last 28 days
            if is_monthly:
                start_date = end_date - datetime.timedelta(days=28)
            else:
                start_date = end_date - datetime.timedelta(days=7)
            
            logger.info(f"Generating {period} statistics for user {chat_id} (counter: {counter})")
            
            # Generate statistics image and analysis
            image_path, analysis = await generate_statistics_image(
                chat_id=user_id,
                period=period,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
            
            if not image_path:
                logger.error(f"Failed to generate statistics image for user {chat_id}")
                return
            
            # Determine the period text for the caption
            period_text = text_constants.LAST_MONTH if is_monthly else text_constants.LAST_WEEK
            
            # Send image to user
            with open(image_path, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text_constants.WEEKLY_STATISTICS_CAPTION.format(period=period_text)
                )
            
            # Send AI analysis as a separate message if available
            if analysis:
                logger.info(f"Sending AI analysis to user {chat_id}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"📊 *Аналіз ваших тренувань*\n\n{analysis}",
                    parse_mode="Markdown"
                )
            
            logger.info(f"Statistics sent successfully to user {chat_id}")
            
            # Clean up the image file
            try:
                import os
                os.remove(image_path)
            except Exception as e:
                logger.error(f"Error removing temporary file: {e}")
                
    except Exception as e:
        logger.error(f"Error sending statistics to user {chat_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Starting ISLOB Bot")
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
        conversations.custom_notification_conversation.custom_notification_conv_handler
    )
    app.add_handler(
        conversations.statistics_conversation.statistics_conv_handler
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, utils.menus.handle_menu)
    )

    # Configure scheduler logging
    import logging
    
    # Create a custom handler that redirects APScheduler logs to loguru
    class LoguruHandler(logging.Handler):
        def emit(self, record):
            # Get corresponding loguru level
            level = record.levelname.lower()
            # Get the loguru logger method corresponding to the level
            log_method = getattr(logger, level, None)
            if log_method:
                # Format the message
                msg = self.format(record)
                # Log with loguru
                log_method(f"[APScheduler] {msg}")
    
    # Configure APScheduler to use our custom handler
    logging.getLogger('apscheduler').setLevel(logging.INFO)
    apscheduler_logger = logging.getLogger('apscheduler')
    apscheduler_logger.handlers = []
    apscheduler_logger.addHandler(LoguruHandler())
    apscheduler_logger.propagate = False
    
    # Configure httpx logging
    httpx_logger = logging.getLogger('httpx')
    httpx_logger.handlers = []
    httpx_logger.addHandler(LoguruHandler())
    httpx_logger.propagate = False
    
    # Configure telegram.ext logging
    telegram_logger = logging.getLogger('telegram.ext')
    telegram_logger.handlers = []
    telegram_logger.addHandler(LoguruHandler())
    telegram_logger.propagate = False

    job_queue = app.job_queue
    logger.info("Configuring job queue")

    logger.info("Adding scheduled message job (interval: 10s)")
    job_queue.run_repeating(send_scheduled_message, interval=10, first=0)
    
    after_training_quiz_scheduled_time = datetime_time(
        hour=15, minute=0, tzinfo=timezone
    )
    logger.info(f"Adding daily after training messages job at {after_training_quiz_scheduled_time}")
    job_queue.run_daily(
        send_after_training_messages, time=after_training_quiz_scheduled_time
    )

    after_training_motivation_time = datetime_time(hour=18, minute=0, tzinfo=timezone)
    logger.info(f"Adding daily after training motivation job at {after_training_motivation_time}")
    job_queue.run_daily(
        get_evening_after_training_motivation, time=after_training_motivation_time
    )

    logger.info("Adding pre-training notifications job (interval: 10s)")
    job_queue.run_repeating(get_pre_training_notifications, interval=10, first=0)
    
    logger.info("Adding training notifications job (interval: 10s)")
    job_queue.run_repeating(get_training_notifications, interval=10, first=0)
    
    logger.info("Adding stop training notification job (interval: 10s)")
    job_queue.run_repeating(stop_training_notification, interval=10, first=0)
    
    logger.info("Adding custom notifications job (interval: 10s)")
    job_queue.run_repeating(send_custom_notifications, interval=10, first=0)
    
    # Schedule weekly statistics job to run every Monday at 12:00 Kyiv time
    kyiv_time = datetime_time(hour=18, minute=0, tzinfo=timezone)
    logger.info(f"Adding weekly statistics job (every Monday at {kyiv_time})")
    job_queue.run_daily(send_weekly_statistics, time=kyiv_time, days=[0])  # 0 is Monday

    # Configure error handler
    from utils.error_handler import error_handler
    app.add_error_handler(error_handler)
    logger.info("Error handler configured")

    logger.info("Starting the bot")
    app.run_polling()
    logger.info("Bot stopped")
