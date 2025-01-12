from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from models import (
    UserPaymentStatus,
    UserRole,
    User,
    NotificationPreference,
    NotificationType,
    Training, MorningQuiz,
)
from exceptions import UserNotFoundError
import datetime
from config import timezone


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

    user_notifications = db.query(NotificationPreference).filter_by(user=user).first()
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
        .filter_by(user_id=user.id, is_active=is_active)
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
        training.training_discomfort = training_discomfort
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


def save_morning_quiz_results(user_id, quiz_datetime, user_feelings, user_sleeping_hours, db_session):
    user = db_session.query(User).filter_by(chat_id=str(user_id)).first()
    if not user:
        raise UserNotFoundError(user_id)

    morning_quiz = MorningQuiz(
        user=user,
        quiz_datetime=quiz_datetime,
        user_feelings=user_feelings,
        user_sleeping_hours=user_sleeping_hours,
    )
    db_session.add(morning_quiz)
    db_session.commit()


def is_user_had_morning_quiz_today(chat_id, db_session):
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        raise UserNotFoundError(chat_id)

    today_start = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
    today_end = datetime.datetime.combine(datetime.date.today(), datetime.datetime.max.time())
    print(today_start, today_end)
    exists = db_session.query(
        db_session.query(MorningQuiz)
        .filter(
            (MorningQuiz.user == user) &
            (MorningQuiz.quiz_datetime >= today_start) &
            (MorningQuiz.quiz_datetime <= today_end)
        )
        .exists()
    ).scalar()
    print(exists)

    return exists