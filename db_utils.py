from sqlalchemy.orm import Session
from models import UserPaymentStatus, UserRole, User, NotificationPreference, NotificationType
from exceptions import UserNotFoundError


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


def save_user_notification_preference(chat_id:int, notification_type: NotificationType, notification_time: str, db_session: Session):
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        raise UserNotFoundError(chat_id)
    is_created = None
    notification_preference = db_session.query(NotificationPreference).filter_by(user_id=user.id, notification_type=notification_type).first()
    if notification_preference:
        notification_preference.notification_time = notification_time
        is_created = False
    else:
        notification_preference = NotificationPreference(
            user_id = user.id,
            notification_type = notification_type,
            notification_time = notification_time,
        )
        db_session.add(notification_preference)
        is_created = True
    db_session.commit()
    return is_created


def get_user_notifications(chat_id: int, db_session: Session):
    user = db_session.query(User).filter_by(chat_id=str(chat_id)).first()
    if not user:
        raise UserNotFoundError(chat_id)

    notifications = db_session.query(NotificationPreference).filter_by(user_id=user.id).all()
    return notifications


def update_user_notification_time(notification_id: int, new_time: str, db_session: Session):
    notification = db_session.query(NotificationPreference).filter_by(id=notification_id).first()
    notification.notification_time = new_time
    db_session.commit()
