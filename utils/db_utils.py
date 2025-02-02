import datetime

from sqlalchemy import Date, DateTime, cast, select
from sqlalchemy.orm import Session, joinedload

import text_constants
from config import timezone
from exceptions import UserNotFoundError
from models import (
    MorningQuiz,
    NotificationPreference,
    NotificationType,
    Training,
    User,
    UserPaymentStatus,
    UserRole,
)


def add_or_update_user(chat_id: int, username: str, db: Session):
    user = db.query(User).filter_by(chat_id=str(chat_id)).first()
    is_created = None
    if not user:
        user = User(chat_id=str(chat_id), username=username)
        db.add(user)
        is_created = True
    else:
        is_created = False
        user.username = username
    db.commit()

    return is_created


def get_user_by_chat_id(chat_id, db_session):
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        raise UserNotFoundError(chat_id)
    return user


def update_user_full_name(chat_id: int, full_name: str, db: Session):
    user = db.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        raise UserNotFoundError(chat_id)
    user.full_name = full_name
    db.commit()


def is_user_ready_to_use(chat_id: int, db: Session):
    user = db.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:

        raise UserNotFoundError(chat_id)

    if not user.full_name:

        return False

    user_notifications = (
        db.query(NotificationPreference)
        .filter_by(user=user, notification_type=NotificationType.MORNING_NOTIFICATION)
        .first()
    )
    if not user_notifications:

        return False

    return True


def is_active_user(chat_id: int, db: Session):
    user = db.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        raise UserNotFoundError(chat_id)
    if user.payment_status == UserPaymentStatus.ACTIVE or user.role == UserRole.ADMIN:

        return True

    return False


def is_admin_user(chat_id: int, db: Session):
    user = db.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        raise UserNotFoundError(chat_id)
    if user.role == UserRole.ADMIN:

        return True

    return False


def get_all_users(db: Session):
    users = db.query(User).filter_by(payment_status=UserPaymentStatus.ACTIVE).all()

    return users


def save_user_notification_preference(
    chat_id: int,
    notification_type: NotificationType,
    notification_time: str,
    next_execution_datetime,
    db_session: Session,
):
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        raise UserNotFoundError(chat_id)
    is_created = None
    notification_preference = (
        db_session.query(NotificationPreference)
        .filter_by(user_id=user.id, notification_type=notification_type)
        .first()
    )
    if notification_preference:
        notification_preference.notification_time = notification_time
        notification_preference.is_active = True
        is_created = False
    else:
        notification_preference = NotificationPreference(
            user_id=user.id,
            notification_type=notification_type,
            notification_time=notification_time,
            next_execution_datetime=next_execution_datetime,
            is_active=True,
        )
        db_session.add(notification_preference)
        is_created = True
    db_session.commit()

    return is_created


def get_user_notifications(chat_id: int, db_session: Session, is_active: bool = True):
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
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

    return notifications


def update_user_notification_time(
    notification_id: int, new_time: str, next_execution_datetime, db_session: Session
):
    notification = (
        db_session.query(NotificationPreference).filter_by(id=notification_id).first()
    )
    notification.notification_time = new_time
    notification.next_execution_datetime = next_execution_datetime
    db_session.commit()


def get_user_notification_by_time(chat_id: int, time: str, db_session: Session):
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        raise UserNotFoundError(chat_id)
    notification = (
        db_session.query(NotificationPreference)
        .filter_by(user=user, notification_time=time)
        .first()
    )

    return notification


def toggle_user_notification(notification_id: int, db_session: Session):
    notification = (
        db_session.query(NotificationPreference).filter_by(id=notification_id).first()
    )
    notification.is_active = not notification.is_active
    db_session.commit()


def start_user_training(chat_id: int, user_state_mark: str, db_session: Session):
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
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
        .filter_by(
            user_id=user.id,
            notification_type=NotificationType.STOP_TRAINING_NOTIFICATION,
        )
        .first()
    )

    datetime_now = datetime.datetime.now(tz=timezone)
    next_execution_datetime = datetime_now + datetime.timedelta(hours=1, minutes=15)

    if notification_preference:
        notification_preference.notification_time = "00:00"
        notification_preference.is_active = True
        notification_preference.notification_sent = False
        notification_preference.next_execution_datetime = next_execution_datetime
        is_created = False
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

    return training.id


def cancel_training(training_id: int, db_session: Session):
    training = db_session.query(Training).filter_by(id=training_id).first()
    if training:
        training.canceled = True


def stop_training(
    training_id: int,
    training_hardness: str,
    training_discomfort: str,
    db_session: Session,
):
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

        return training.training_duration


def get_notifications_to_send_by_time(current_datetime, db_session: Session):
    notification_preferences = db_session.scalars(
        select(NotificationPreference)
        .options(joinedload(NotificationPreference.user))
        .where(
            (NotificationPreference.next_execution_datetime <= current_datetime)
            & (NotificationPreference.is_active.is_(True))
        )
        .filter(
            NotificationPreference.notification_type
            == NotificationType.MORNING_NOTIFICATION
        )
    ).all()

    return notification_preferences


def update_user_notification_preference_next_execution(
    last_execution_datetime,
    next_execution_datetime,
    notification_id,
    db_session: Session,
):
    notification_preference = (
        db_session.query(NotificationPreference).filter_by(id=notification_id).first()
    )
    notification_preference.last_execution_datetime = last_execution_datetime
    notification_preference.next_execution_datetime = next_execution_datetime

    db_session.commit()


def save_morning_quiz_results(
    user_id,
    quiz_datetime,
    user_feelings,
    user_sleeping_hours,
    db_session,
    is_going_to_have_training,
    expected_training_datetime=None,
):
    user = db_session.query(User).filter_by(chat_id=str(user_id)).first()
    if not user:
        raise UserNotFoundError(user_id)

    morning_quiz = MorningQuiz(
        user=user,
        quiz_datetime=quiz_datetime,
        user_feelings=user_feelings,
        user_sleeping_hours=user_sleeping_hours,
    )
    if is_going_to_have_training == text_constants.YES_NO_BUTTONS[0]:
        morning_quiz.is_going_to_have_training = True
    else:
        morning_quiz.is_going_to_have_training = False

    if morning_quiz.is_going_to_have_training and expected_training_datetime:
        morning_quiz.expected_training_datetime = expected_training_datetime

    db_session.add(morning_quiz)
    db_session.commit()


def is_user_had_morning_quiz_today(chat_id, db_session):
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
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

    return exists


def get_users_with_yesterday_trainings(session):
    yesterday_date = datetime.datetime.now() - datetime.timedelta(days=1)
    results = (
        session.query(User)
        .join(Training, User.id == Training.user_id)
        .filter(cast(Training.training_start_date, Date) == cast(yesterday_date, Date))
        .all()
    )
    return results


def update_training_after_quiz(training_id, stress_level, soreness, db_session):
    training = db_session.query(Training).filter_by(id=training_id).first()

    training.stress_on_next_day = stress_level
    training.soreness_on_next_day = (
        True if soreness == text_constants.YES_NO_BUTTONS[0] else False
    )
    db_session.commit()


def update_user_notification_preference_admin_message_sent(
    db_session, sent_datetime, notification_id
):
    notification = (
        db_session.query(NotificationPreference).filter_by(id=notification_id).first()
    )
    notification.admin_warning_sent = sent_datetime
    db_session.commit()


def get_notifications_by_type(notification_type, db_session):
    datetime_now = datetime.datetime.now(tz=timezone)
    notifications = (
        db_session.query(NotificationPreference)
        .join(User, NotificationPreference.user_id == User.id)
        .options(joinedload(NotificationPreference.user))
        .filter(NotificationPreference.notification_type == notification_type)
        .filter(NotificationPreference.notification_sent == False)
        .filter(NotificationPreference.is_active == True)
        .filter(
            cast(NotificationPreference.next_execution_datetime, DateTime)
            <= cast(datetime_now, DateTime)
        )
        .all()
    )
    return notifications


def create_training_notifications(chat_id, notification_time, db_session):
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
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
        datetime_now = datetime.datetime.now(tz=timezone)
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
            is_created = False
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


def update_notification_sent(notification_id, db_session):
    notification = (
        db_session.query(NotificationPreference).filter_by(id=notification_id).first()
    )
    notification.notification_sent = True
    db_session.commit()


def update_training_notification(chat_id, db_session):
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
