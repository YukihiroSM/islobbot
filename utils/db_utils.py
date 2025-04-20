import datetime

from sqlalchemy import select, cast, Date
from sqlalchemy.orm import Session, joinedload

from config import timezone as tz
from database import get_db
from exceptions import UserNotFoundError
from models import (
    User,
    Training,
    MorningQuiz,
    NotificationPreference,
    CustomNotification,
    NotificationType,
    UserRole,
    UserPaymentStatus,
)

import text_constants
from utils.logger import get_logger

logger = get_logger(__name__)


def add_or_update_user(chat_id: int, username: str, db: Session):
    logger.debug(f"Adding or updating user with chat_id={chat_id}, username={username}")
    user = db.query(User).filter_by(chat_id=str(chat_id)).first()
    is_created = None
    if not user:
        logger.info(f"Creating new user with chat_id={chat_id}")
        user = User(chat_id=str(chat_id), username=username)
        db.add(user)
        is_created = True
    else:
        logger.debug(f"Updating existing user with chat_id={chat_id}")
        is_created = False
        user.username = username
    db.commit()

    return is_created


def get_user_by_chat_id(chat_id, db_session):
    logger.debug(f"Getting user by chat_id={chat_id}")
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)
    return user


def update_user_full_name(chat_id: int, full_name: str, db: Session):
    logger.debug(f"Updating full name for user with chat_id={chat_id} to '{full_name}'")
    user = db.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)
    user.full_name = full_name
    db.commit()
    logger.info(f"Updated full name for user with chat_id={chat_id}")


def is_user_ready_to_use(chat_id: int, db: Session):
    logger.debug(f"Checking if user with chat_id={chat_id} is ready to use")
    user = db.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)

    if not user.full_name:
        logger.debug(f"User {chat_id} is not ready: missing full name")
        return False

    user_notifications = (
        db.query(NotificationPreference)
        .filter_by(
            user=user, notification_type=NotificationType.MORNING_NOTIFICATION
        )
        .first()
    )
    if not user_notifications:
        logger.debug(f"User {chat_id} is not ready: missing morning notifications")
        return False

    logger.debug(f"User {chat_id} is ready to use")
    return True


def is_active_user(chat_id: int, db: Session):
    logger.debug(f"Checking if user with chat_id={chat_id} is active")
    user = db.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)
    if user.payment_status == UserPaymentStatus.ACTIVE or user.role == UserRole.ADMIN:
        logger.debug(f"User {chat_id} is active (payment status: {user.payment_status}, role: {user.role})")
        return True

    logger.debug(f"User {chat_id} is not active (payment status: {user.payment_status}, role: {user.role})")
    return False


def is_admin_user(chat_id: int, db: Session):
    logger.debug(f"Checking if user with chat_id={chat_id} is admin")
    user = db.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)
    if user.role == UserRole.ADMIN:
        logger.debug(f"User {chat_id} is admin")
        return True

    logger.debug(f"User {chat_id} is not admin (role: {user.role})")
    return False


def get_all_users(db: Session):
    logger.debug("Getting all active users")
    users = db.query(User).filter_by(payment_status=UserPaymentStatus.ACTIVE).all()
    logger.debug(f"Found {len(users)} active users")
    return users


def save_user_notification_preference(
    chat_id: int,
    notification_type: NotificationType,
    notification_time: str,
    next_execution_datetime,
    db_session: Session,
    notification_name: str = None,
    notification_message: str = None,
):
    logger.debug(f"Saving notification preference for user {chat_id}, type {notification_type}, time {notification_time}")
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)
    is_created = None
    
    # For custom notifications, we always create a new one
    if notification_type == NotificationType.CUSTOM_NOTIFICATION:
        logger.debug(f"Creating new custom notification for user {chat_id}")
        # Create a new notification preference for custom notification
        notification_preference = NotificationPreference(
            user_id=user.id,
            notification_type=notification_type,
            notification_time=notification_time,
            next_execution_datetime=next_execution_datetime,
            is_active=True,
            notification_message=notification_message,
        )
        db_session.add(notification_preference)
        db_session.commit()
        db_session.refresh(notification_preference)
        
        # Create the associated CustomNotification record
        if notification_name:
            from datetime import datetime
            logger.debug(f"Creating associated CustomNotification record with name '{notification_name}'")
            custom_notification = CustomNotification(
                user_id=user.id,
                notification_preference_id=notification_preference.id,
                notification_name=notification_name,
                notification_message=notification_message or "",
                is_active=True,
                created_at=datetime.now(tz=tz),
            )
            db_session.add(custom_notification)
            db_session.commit()
        
        is_created = True
    else:
        # For other notification types, check if it already exists
        notification_preference = (
            db_session.query(NotificationPreference)
            .filter_by(user_id=user.id, notification_type=notification_type)
            .first()
        )
        
        if notification_preference:
            logger.debug(f"Updating existing notification preference (id={notification_preference.id})")
            notification_preference.notification_time = notification_time
            notification_preference.is_active = True
            if notification_message:
                notification_preference.notification_message = notification_message
            is_created = False
        else:
            logger.debug(f"Creating new notification preference for type {notification_type}")
            notification_preference = NotificationPreference(
                user_id=user.id,
                notification_type=notification_type,
                notification_time=notification_time,
                next_execution_datetime=next_execution_datetime,
                is_active=True,
                notification_message=notification_message,
            )
            db_session.add(notification_preference)
            is_created = True
        
        db_session.commit()

    logger.info(f"{'Created' if is_created else 'Updated'} notification preference for user {chat_id}, type {notification_type}")
    return is_created


def get_user_notifications(chat_id: int, db_session: Session, is_active: bool = True):
    logger.debug(f"Getting {'active' if is_active else 'inactive'} notifications for user {chat_id}")
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)

    notifications = (
        db_session.query(NotificationPreference)
        .filter_by(
            user_id=user.id,
            is_active=is_active,
            notification_type=NotificationType.MORNING_NOTIFICATION,
        )
        .all()
    )
    logger.debug(f"Found {len(notifications)} notifications for user {chat_id}")
    return notifications


def update_user_notification_time(
    notification_id: int, new_time: str, next_execution_datetime, db_session: Session
):
    logger.debug(f"Updating notification time for notification {notification_id} to {new_time}")
    notification = (
        db_session.query(NotificationPreference).filter_by(id=notification_id).first()
    )
    if not notification:
        logger.error(f"Notification not found with id={notification_id}")
        return
        
    notification.notification_time = new_time
    notification.next_execution_datetime = next_execution_datetime
    db_session.commit()
    logger.info(f"Updated notification {notification_id} time to {new_time}, next execution at {next_execution_datetime}")


def get_notifications_to_send_by_time(current_datetime, db_session: Session):
    logger.debug(f"Getting notifications to send at {current_datetime}")
    notification_preferences = db_session.scalars(
        select(NotificationPreference)
        .options(joinedload(NotificationPreference.user))
        .where(
            (NotificationPreference.next_execution_datetime <= current_datetime)
            & (NotificationPreference.is_active)
        )
        .filter(
            NotificationPreference.notification_type
            == NotificationType.MORNING_NOTIFICATION
        )
    ).all()

    logger.debug(f"Found {len(notification_preferences)} notifications to send")
    return notification_preferences


def update_user_notification_preference_next_execution(
    last_execution_datetime,
    next_execution_datetime,
    notification_id,
    db_session: Session,
):
    logger.debug(f"Updating next execution time for notification {notification_id}")
    notification = (
        db_session.query(NotificationPreference).filter_by(id=notification_id).first()
    )
    notification.last_execution_datetime = last_execution_datetime
    
    # Create a timezone-aware next execution time based on the notification time
    # This ensures DST changes are properly handled
    current_time = datetime.datetime.now(tz=tz)
    notification_time = notification.notification_time
    
    # Create a datetime with today's date and the notification time
    next_time = tz.localize(
        datetime.datetime(
            current_time.year,
            current_time.month,
            current_time.day,
            notification_time.hour,
            notification_time.minute,
            0
        )
    ) + datetime.timedelta(days=1)
    
    notification.next_execution_datetime = next_time
    db_session.commit()
    logger.info(f"Updated next execution time for notification {notification_id} to {next_time}")


def save_morning_quiz_results(
    user_id,
    quiz_datetime,
    user_feelings,
    user_sleeping_hours,
    user_weight,
    db_session,
    is_going_to_have_training,
    expected_training_datetime=None,
):
    logger.debug(f"Saving morning quiz results for user {user_id}")
    user = db_session.query(User).filter_by(chat_id=str(user_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={user_id}")
        raise UserNotFoundError(user_id)

    morning_quiz = MorningQuiz(
        user=user,
        quiz_datetime=quiz_datetime,
        user_feelings=user_feelings,
        user_sleeping_hours=user_sleeping_hours,
        user_weight=user_weight,
    )
    if is_going_to_have_training == text_constants.YES_NO_BUTTONS[0]:
        morning_quiz.is_going_to_have_training = True
    else:
        morning_quiz.is_going_to_have_training = False

    if morning_quiz.is_going_to_have_training and expected_training_datetime:
        morning_quiz.expected_training_datetime = expected_training_datetime

    db_session.add(morning_quiz)
    db_session.commit()
    logger.info(f"Saved morning quiz results for user {user_id}")


def is_user_had_morning_quiz_today(chat_id, db_session):
    logger.debug(f"Checking if user {chat_id} had morning quiz today")
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)

    today_start = datetime.datetime.combine(
        datetime.date.today(), datetime.datetime.min.time()
    )
    today_end = datetime.datetime.combine(
        datetime.date.today(), datetime.datetime.max.time()
    )
    exists = db_session.query(
        db_session.query(MorningQuiz)
        .filter(
            (MorningQuiz.user == user)
            & (MorningQuiz.quiz_datetime >= today_start)
            & (MorningQuiz.quiz_datetime <= today_end)
        )
        .exists()
    ).scalar()

    logger.debug(f"User {chat_id} had morning quiz today: {exists}")
    return exists


def get_users_with_yesterday_trainings(session):
    logger.debug("Getting users with yesterday trainings")
    yesterday_date = datetime.datetime.now() - datetime.timedelta(days=1)
    results = (
        session.query(User)
        .join(Training, User.id == Training.user_id)
        .filter(cast(Training.training_start_date, Date) == cast(yesterday_date, Date))
        .all()
    )
    logger.debug(f"Found {len(results)} users with yesterday trainings")
    return results


def update_training_after_quiz(training_id, stress_level, soreness, db_session):
    logger.debug(f"Updating training {training_id} after quiz")
    training = db_session.query(Training).filter_by(id=training_id).first()

    training.stress_on_next_day = stress_level
    training.soreness_on_next_day = (
        True if soreness == text_constants.YES_NO_BUTTONS[0] else False
    )
    db_session.commit()
    logger.info(f"Updated training {training_id} after quiz")


def update_user_notification_preference_admin_message_sent(
    db_session, sent_datetime, notification_id
):
    logger.debug(f"Updating admin message sent for notification {notification_id}")
    notification = (
        db_session.query(NotificationPreference).filter_by(id=notification_id).first()
    )
    notification.admin_warning_sent = sent_datetime
    db_session.commit()
    logger.info(f"Updated admin message sent for notification {notification_id}")


def get_notifications_by_type(notification_type, db_session):
    logger.debug(f"Getting notifications by type {notification_type}")
    if notification_type == NotificationType.CUSTOM_NOTIFICATION:
        # For custom notifications, join with CustomNotification table
        notifications = (
            db_session.query(NotificationPreference)
            .join(CustomNotification)
            .filter(
                NotificationPreference.notification_type == notification_type,
                NotificationPreference.is_active,
                CustomNotification.is_active,
                ~NotificationPreference.notification_sent,
            )
            .all()
        )
    else:
        notifications = (
            db_session.query(NotificationPreference)
            .filter(
                NotificationPreference.notification_type == notification_type,
                NotificationPreference.is_active,
                ~NotificationPreference.notification_sent,
            )
            .all()
        )
    
    logger.debug(f"Found {len(notifications)} notifications by type {notification_type}")
    return notifications


def get_user_custom_notifications(chat_id: int, db_session: Session):
    logger.debug(f"Getting custom notifications for user {chat_id}")
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)
    
    custom_notifications = (
        db_session.query(CustomNotification)
        .filter_by(user_id=user.id)
        .filter(CustomNotification.is_active)
        .all()
    )
    
    logger.debug(f"Found {len(custom_notifications)} custom notifications for user {chat_id}")
    return custom_notifications


def delete_custom_notification(notification_id: int, db_session: Session):
    logger.debug(f"Deleting custom notification {notification_id}")
    custom_notification = (
        db_session.query(CustomNotification)
        .filter_by(id=notification_id)
        .first()
    )
    if custom_notification:
        # Delete the custom notification
        db_session.delete(custom_notification)
        db_session.commit()
        logger.info(f"Deleted custom notification {notification_id}")
        return True
    logger.error(f"Custom notification not found with id={notification_id}")
    return False


def create_training_notifications(chat_id, notification_time, db_session):
    logger.debug(f"Creating training notifications for user {chat_id}")
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)

    notification_types = [
        NotificationType.PRE_TRAINING_REMINDER_NOTIFICATION,
        NotificationType.TRAINING_REMINDER_NOTIFICATION,
    ]

    for notification_type in notification_types:
        notification_preference = (
            db_session.query(NotificationPreference)
            .filter_by(user_id=user.id, notification_type=notification_type)
            .first()
        )

        hours, minutes = map(int, notification_time.split(":"))
        datetime_now = datetime.datetime.now(tz=tz)
        next_execution_datetime = datetime_now.replace(
            hour=hours, minute=minutes, second=0, microsecond=0
        )

        if notification_type == NotificationType.PRE_TRAINING_REMINDER_NOTIFICATION:
            next_execution_datetime = next_execution_datetime - datetime.timedelta(
                hours=1
            )

        if notification_preference:
            notification_preference.notification_time = notification_time
            notification_preference.is_active = True
            notification_preference.notification_sent = False
            notification_preference.next_execution_datetime = next_execution_datetime
        else:
            notification_preference = NotificationPreference(
                user_id=user.id,
                notification_type=notification_type,
                notification_time=notification_time,
                notification_sent=False,
                next_execution_datetime=next_execution_datetime,
                is_active=True,
            )
            db_session.add(notification_preference)

        db_session.commit()
        logger.info(f"Created training notification for user {chat_id}, type {notification_type}")


def update_notification_sent(notification_id, db_session):
    logger.debug(f"Updating notification sent for notification {notification_id}")
    notification = (
        db_session.query(NotificationPreference).filter_by(id=notification_id).first()
    )
    notification.notification_sent = True
    db_session.commit()
    logger.info(f"Updated notification sent for notification {notification_id}")


def update_training_stop_notification(chat_id, db_session):
    logger.debug(f"Updating training stop notification for user {chat_id}")
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    user_notification = (
        db_session.query(NotificationPreference)
        .filter(
            (NotificationPreference.user == user)
            & (
                NotificationPreference.notification_type
                == NotificationType.STOP_TRAINING_NOTIFICATION
            )
        )
        .first()
    )
    if user_notification:
        user_notification.notification_sent = True
        db_session.commit()
        logger.info(f"Updated training stop notification for user {chat_id}")


def update_training_start_notification(chat_id, db_session):
    logger.debug(f"Updating training start notification for user {chat_id}")
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    user_notification = (
        db_session.query(NotificationPreference)
        .filter(
            (NotificationPreference.user == user)
            & (
                NotificationPreference.notification_type
                == NotificationType.TRAINING_REMINDER_NOTIFICATION
            )
        )
        .first()
    )
    if user_notification:
        user_notification.notification_sent = True
        db_session.commit()
        logger.info(f"Updated training start notification for user {chat_id}")


def update_pre_training_notification(chat_id, db_session):
    logger.debug(f"Updating pre-training notification for user {chat_id}")
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    user_notification = (
        db_session.query(NotificationPreference)
        .filter(
            (NotificationPreference.user == user)
            & (
                NotificationPreference.notification_type
                == NotificationType.PRE_TRAINING_REMINDER_NOTIFICATION
            )
        )
        .first()
    )
    if user_notification:
        user_notification.notification_sent = True
        db_session.commit()
        logger.info(f"Updated pre-training notification for user {chat_id}")


def start_user_training(chat_id: int, user_state_mark: str, db_session: Session):
    logger.debug(f"Starting user training for user {chat_id}")
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)

    training = Training(
        user=user,
        mark_before_training=user_state_mark,
        training_start_date=datetime.datetime.now(),
        training_finish_date=None,
        training_duration=None,
        training_hardness=None,
        training_discomfort=None,
        stress_on_next_day=None,
        soreness_on_next_day=None,
        canceled=False,
    )

    notification_preference = (
        db_session.query(NotificationPreference)
        .filter(
            (NotificationPreference.user == user)
            & (
                NotificationPreference.notification_type
                == NotificationType.STOP_TRAINING_NOTIFICATION
            )
        )
        .first()
    )

    datetime_now = datetime.datetime.now(tz=tz)
    next_execution_datetime = datetime_now + datetime.timedelta(hours=1, minutes=15)

    if notification_preference:
        notification_preference.notification_time = "00:00"
        notification_preference.is_active = True
        notification_preference.notification_sent = False
        notification_preference.next_execution_datetime = next_execution_datetime
    else:
        notification_preference = NotificationPreference(
            user_id=user.id,
            notification_type=NotificationType.STOP_TRAINING_NOTIFICATION,
            notification_time="00:00",
            notification_sent=False,
            next_execution_datetime=next_execution_datetime,
            is_active=True,
        )
        db_session.add(notification_preference)

    db_session.add(training)
    db_session.commit()
    logger.info(f"Started user training for user {chat_id}")
    return training.id


def cancel_training(training_id: int, db_session: Session):
    logger.debug(f"Canceling training {training_id}")
    training = db_session.query(Training).filter_by(id=training_id).first()
    if training:
        training.canceled = True
        db_session.commit()
        logger.info(f"Canceled training {training_id}")


def stop_training(
    training_id: int,
    training_hardness: str,
    training_discomfort: str,
    db_session: Session,
):
    logger.debug(f"Stopping training {training_id}")
    training = (
        db_session.query(Training).filter_by(id=training_id, canceled=False).first()
    )
    if training:
        training.training_finish_date = datetime.datetime.now()
        training.training_duration = (
            training.training_finish_date - training.training_start_date
        )
        training.training_hardness = training_hardness
        training.training_discomfort = (
            True if training_discomfort == text_constants.YES_NO_BUTTONS[0] else False
        )
        db_session.commit()
        logger.info(f"Stopped training {training_id}")
        return training.training_duration


def set_training_pdf_message_id(pdf_user_id, message_id, chat_id, db_session):
    logger.debug(f"Setting training PDF message ID for user {pdf_user_id}")
    user = db_session.query(User).filter_by(chat_id=str(pdf_user_id)).first()

    training_pdf_message_str = f"{message_id};{chat_id}"
    user.training_pdf_message_id = training_pdf_message_str
    db_session.commit()
    logger.info(f"Set training PDF message ID for user {pdf_user_id}")


def get_training_pdf_message_data(user_id, db_session):
    logger.debug(f"Getting training PDF message data for user {user_id}")
    user = db_session.query(User).filter_by(chat_id=str(user_id)).first()

    if user.training_pdf_message_id:
        training_pdf_data = user.training_pdf_message_id.split(";")[:2]
        logger.debug(f"Found training PDF message data for user {user_id}")
        return training_pdf_data
    logger.debug(f"No training PDF message data found for user {user_id}")
    return None, None


def save_custom_notification(
    chat_id: int,
    notification_name: str,
    notification_message: str,
    notification_time: str,
    periodicity_type: str = "daily",
    specific_days: str = None,
    db_session: Session = None,
):
    logger.debug(f"Saving custom notification for user {chat_id}")
    if db_session is None:
        db_session = next(get_db())
        
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)
    
    # Parse time string to Time object
    hours, minutes = map(int, notification_time.split(":")[:2])
    time_obj = datetime.time(hour=hours, minute=minutes)
    
    # Create a timezone-aware next execution datetime
    current_time = datetime.datetime.now(tz=tz)
    
    # Create a datetime with today's date and the notification time
    notification_datetime = tz.localize(
        datetime.datetime(
            current_time.year,
            current_time.month,
            current_time.day,
            hours,
            minutes,
            0
        )
    )
    
    # Check if the notification should be sent today based on periodicity
    should_send_today = False
    
    if periodicity_type == "daily":
        should_send_today = True
    elif periodicity_type == "weekly":
        # For weekly, we'll set it to the next Monday
        days_until_monday = (7 - current_time.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # If today is Monday, set to next Monday
        notification_datetime += datetime.timedelta(days=days_until_monday)
        should_send_today = False
    elif periodicity_type == "monthly":
        # For monthly, we'll set it to the 1st of next month
        next_month = current_time.month + 1 if current_time.month < 12 else 1
        next_year = current_time.year if current_time.month < 12 else current_time.year + 1
        notification_datetime = tz.localize(
            datetime.datetime(
                next_year,
                next_month,
                1,
                hours,
                minutes,
                0
            )
        )
        should_send_today = False
    elif periodicity_type == "specific_days" and specific_days:
        # For specific days, check if today is one of the specified days
        day_of_week = current_time.weekday()
        specific_days_list = [int(day) for day in specific_days.split(",")]
        should_send_today = day_of_week in specific_days_list
    
    # If the time has already passed today and it should be sent today, set it for tomorrow
    if should_send_today and notification_datetime < current_time:
        notification_datetime += datetime.timedelta(days=1)
    
    # Create a new custom notification
    custom_notification = CustomNotification(
        user_id=user.id,
        notification_name=notification_name,
        notification_message=notification_message,
        notification_time=time_obj,
        next_execution_datetime=notification_datetime,
        is_active=True,
        notification_sent=False,
        created_at=datetime.datetime.now(tz=tz),
        periodicity_type=periodicity_type,
        specific_days=specific_days,
    )
    
    db_session.add(custom_notification)
    db_session.commit()
    logger.info(f"Saved custom notification for user {chat_id}")
    return custom_notification


def get_custom_notifications_to_send(db_session: Session):
    logger.debug("Getting custom notifications to send")
    current_datetime = datetime.datetime.now(tz=tz)
    
    # Get all active notifications that need to be sent
    notifications = (
        db_session.query(CustomNotification)
        .options(joinedload(CustomNotification.user))
        .filter(
            (CustomNotification.next_execution_datetime <= current_datetime) &
            (CustomNotification.is_active) &
            (~CustomNotification.notification_sent)
        )
        .all()
    )
    
    logger.debug(f"Found {len(notifications)} custom notifications to send")
    return notifications


def update_custom_notification_sent(notification_id: int, db_session: Session):
    logger.debug(f"Updating custom notification sent for notification {notification_id}")
    notification = (
        db_session.query(CustomNotification)
        .filter_by(id=notification_id)
        .first()
    )
    if notification:
        # Mark as sent
        notification.notification_sent = True
        
        # Update last execution time
        notification.last_execution_datetime = datetime.datetime.now(tz=tz)
        
        # Calculate next execution time based on periodicity
        current_time = datetime.datetime.now(tz=tz)
        notification_time = notification.notification_time
        
        if notification.periodicity_type == "daily":
            # For daily, set to tomorrow at the same time
            next_time = tz.localize(
                datetime.datetime(
                    current_time.year,
                    current_time.month,
                    current_time.day,
                    notification_time.hour,
                    notification_time.minute,
                    0
                )
            ) + datetime.timedelta(days=1)
        elif notification.periodicity_type == "weekly":
            # For weekly, set to 7 days from now
            next_time = tz.localize(
                datetime.datetime(
                    current_time.year,
                    current_time.month,
                    current_time.day,
                    notification_time.hour,
                    notification_time.minute,
                    0
                )
            ) + datetime.timedelta(days=7)
        elif notification.periodicity_type == "monthly":
            # For monthly, set to the same day next month
            month = current_time.month + 1
            year = current_time.year
            if month > 12:
                month = 1
                year += 1
            
            # Handle month length differences
            day = min(current_time.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            
            next_time = tz.localize(
                datetime.datetime(
                    year,
                    month,
                    day,
                    notification_time.hour,
                    notification_time.minute,
                    0
                )
            )
        elif notification.periodicity_type == "specific_days" and notification.specific_days:
            # For specific days, find the next day in the list
            specific_days = [int(day) for day in notification.specific_days.split(",")]
            current_day = current_time.weekday()
            
            # Find the next day in the list
            next_days = [day for day in specific_days if day > current_day]
            if next_days:
                # There's a day later this week
                days_to_add = min(next_days) - current_day
            else:
                # Wrap around to the first day next week
                days_to_add = 7 - current_day + min(specific_days)
            
            next_time = tz.localize(
                datetime.datetime(
                    current_time.year,
                    current_time.month,
                    current_time.day,
                    notification_time.hour,
                    notification_time.minute,
                    0
                )
            ) + datetime.timedelta(days=days_to_add)
        else:
            # Default to daily if something goes wrong
            next_time = tz.localize(
                datetime.datetime(
                    current_time.year,
                    current_time.month,
                    current_time.day,
                    notification_time.hour,
                    notification_time.minute,
                    0
                )
            ) + datetime.timedelta(days=1)
        
        notification.next_execution_datetime = next_time
        
        # Reset notification_sent flag for the next execution
        notification.notification_sent = False
        
        db_session.commit()
        logger.info(f"Updated custom notification sent for notification {notification_id}")
        return True
    logger.error(f"Custom notification not found with id={notification_id}")
    return False


def get_user_notification_by_time(chat_id: int, time: str, db_session: Session):
    logger.debug(f"Getting user notification by time for user {chat_id}, time {time}")
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        logger.error(f"User not found with chat_id={chat_id}")
        raise UserNotFoundError(chat_id)
    notification = (
        db_session.query(NotificationPreference)
        .filter_by(user=user, notification_time=time)
        .first()
    )
    logger.debug(f"Found notification: {notification.id if notification else 'None'}")
    return notification


def toggle_user_notification(notification_id: int, db_session: Session):
    logger.debug(f"Toggling notification {notification_id}")
    notification = (
        db_session.query(NotificationPreference).filter_by(id=notification_id).first()
    )
    if not notification:
        logger.error(f"Notification not found with id={notification_id}")
        return
        
    notification.is_active = not notification.is_active
    db_session.commit()
    logger.info(f"Toggled notification {notification_id} to {notification.is_active}")


def update_user_stats_counter(user_id: int, db_session: Session):
    """
    Update the weekly statistics counter for a user and return whether this is a monthly stats cycle.
    
    Args:
        user_id (int): The user ID
        db_session (Session): Database session
        
    Returns:
        tuple: (is_monthly, counter) - Whether this is a monthly stats cycle and the current counter value
    """
    user = db_session.query(User).filter_by(id=user_id).first()
    if not user:
        logger.error(f"User not found with id={user_id}")
        return False, 0
        
    # Increment the counter (handle case where field doesn't exist in DB yet)
    if user.weekly_stats_counter is None:
        user.weekly_stats_counter = 1
    else:
        user.weekly_stats_counter += 1
    counter = user.weekly_stats_counter
    
    # Update the last sent date
    user.last_stats_sent_date = datetime.datetime.now(tz=tz)
    
    # Determine if this is a monthly stats cycle (every 4th time)
    is_monthly = counter % 4 == 0
    
    db_session.commit()
    logger.info(f"Updated stats counter for user {user_id} to {counter}, is_monthly={is_monthly}")
    
    return is_monthly, counter
