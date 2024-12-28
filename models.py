from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Time, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base
from datetime import datetime
from enum import Enum as PyEnum


class UserRole(PyEnum):
    ADMIN = "admin"
    USER = "user"


class UserPaymentStatus(PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class NotificationType(PyEnum):
    MORNING_NOTIFICATION = "morning_notification"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(
        Enum(NotificationType), nullable=False
    )
    notification_time = Column(Time, nullable=False)
    __table_args__ = (
        UniqueConstraint("user_id", "notification_type", name="uq_user_notification_type"),
    )
    user = relationship("User", back_populates="notification_preferences")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=True)
    username = Column(String, unique=True, index=True)
    chat_id = Column(String, unique=True, index=True)
    payment_status = Column(
        Enum(UserPaymentStatus), nullable=False, default=UserPaymentStatus.ACTIVE
    )
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)

    notification_preferences = relationship(
        "NotificationPreference", back_populates="user", cascade="all, delete-orphan", uselist=True
    )