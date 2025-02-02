from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


class UserRole(PyEnum):
    ADMIN = "admin"
    USER = "user"


class UserPaymentStatus(PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class NotificationType(PyEnum):
    MORNING_NOTIFICATION = "morning_notification"
    CUSTOM_NOTIFICATION = "custom_notification"
    PRE_TRAINING_REMINDER_NOTIFICATION = "pre_training_reminder_notification"
    TRAINING_REMINDER_NOTIFICATION = "training_reminder_notification"
    STOP_TRAINING_NOTIFICATION = "stop_training_notification"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    notification_time = Column(Time, nullable=False)
    last_execution_datetime = Column(DateTime, nullable=True)
    next_execution_datetime = Column(DateTime, nullable=True)
    notification_message = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    admin_warning_sent = Column(DateTime, nullable=True)
    notification_sent = Column(Boolean, default=False)
    __table_args__ = (
        UniqueConstraint(
            "user_id", "notification_type", name="uq_user_notification_type"
        ),
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
        "NotificationPreference",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=True,
    )

    trainings = relationship(
        "Training", back_populates="user", cascade="all, delete-orphan", uselist=True
    )

    morning_quizzes = relationship(
        "MorningQuiz", back_populates="user", cascade="all, delete-orphan", uselist=True
    )


class Training(Base):
    __tablename__ = "user_training"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mark_before_training = Column(Integer, nullable=False)
    training_start_date = Column(DateTime, nullable=True)
    training_finish_date = Column(DateTime, nullable=True)
    training_duration = Column(Time, nullable=True)
    training_hardness = Column(Integer, nullable=True)
    training_discomfort = Column(Boolean, nullable=True)
    stress_on_next_day = Column(Integer, nullable=True)
    soreness_on_next_day = Column(Boolean, nullable=True)
    canceled = Column(Boolean, default=False)

    user = relationship("User", back_populates="trainings")


class MorningQuiz(Base):
    __tablename__ = "user_morning_quiz"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_datetime = Column(DateTime, nullable=False)
    user_feelings = Column(Integer, nullable=False)
    user_feelings_comment = Column(String, nullable=True)
    user_sleeping_hours = Column(Time, nullable=False)
    is_going_to_have_training = Column(Boolean, nullable=False, default=False)
    expected_training_datetime = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="morning_quizzes")
