#!/usr/bin/env python3
"""
Script to generate test data for the islob_bot database.
Creates realistic fitness client data for the past 3 months.
"""

import sys
import os
import random
from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import (
    User, 
    NotificationPreference, 
    NotificationType, 
    Training, 
    MorningQuiz,
    CustomNotification,
    UserPaymentStatus,
    UserRole
)
from config import timezone

# User IDs specified by the user
USER_CHAT_IDS = ["5916038251", "591812219", "379872548"]
USER_NAMES = ["Alex Fitness", "Maria Training", "Yukihiro Fitness"]
USER_USERNAMES = ["alex_fitness", "maria_training", "yukihiro_fitness"]

# Current date for reference
CURRENT_DATE = datetime.now(tz=timezone)
# Start date (3 months ago)
START_DATE = CURRENT_DATE - timedelta(days=90)

# Training patterns (days per week)
TRAINING_PATTERNS = [
    [0, 2, 4],  # Monday, Wednesday, Friday
    [1, 3, 5],  # Tuesday, Thursday, Saturday
    [0, 2, 5],  # Monday, Wednesday, Saturday
    [1, 4, 6],  # Tuesday, Friday, Sunday
]

def clear_existing_data(db: Session):
    """Clear existing data for the specified users."""
    print("Clearing existing data...")
    
    for chat_id in USER_CHAT_IDS:
        user = db.query(User).filter_by(chat_id=chat_id).first()
        if user:
            # Delete related records
            db.query(MorningQuiz).filter_by(user_id=user.id).delete()
            db.query(Training).filter_by(user_id=user.id).delete()
            db.query(CustomNotification).filter_by(user_id=user.id).delete()
            db.query(NotificationPreference).filter_by(user_id=user.id).delete()
            db.query(User).filter_by(id=user.id).delete()
            
    db.commit()
    print("Existing data cleared.")

def create_users(db: Session):
    """Create the two specified users."""
    print("Creating users...")
    users = []
    
    for i, chat_id in enumerate(USER_CHAT_IDS):
        user = User(
            chat_id=chat_id,
            username=USER_USERNAMES[i],
            full_name=USER_NAMES[i],
            payment_status=UserPaymentStatus.ACTIVE,
            role=UserRole.USER
        )
        db.add(user)
        users.append(user)
    
    db.commit()
    print(f"Created {len(users)} users.")
    return users

def create_notification_preferences(db: Session, users):
    """Create notification preferences for users."""
    print("Creating notification preferences...")
    
    for user in users:
        # Morning notification (8:00 AM)
        morning_notification = NotificationPreference(
            user_id=user.id,
            notification_type=NotificationType.MORNING_NOTIFICATION,
            notification_time=time(8, 0),
            next_execution_datetime=datetime.now(tz=timezone).replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1),
            is_active=True
        )
        db.add(morning_notification)
        db.commit()  # Commit to ensure the notification is saved
        
        # Custom notifications (different for each user)
        if user.chat_id == USER_CHAT_IDS[0]:  # First user
            # Medication reminder
            create_custom_notification(
                db, 
                user.id, 
                "Прийняти вітаміни", 
                "Час прийняти вітаміни!", 
                time(10, 0)
            )
            
        elif user.chat_id == USER_CHAT_IDS[1]:  # Second user
            # Water reminder
            create_custom_notification(
                db, 
                user.id, 
                "Пити воду", 
                "Не забудь випити воду! ", 
                time(14, 0)
            )
            
            # Stretching reminder
            create_custom_notification(
                db, 
                user.id, 
                "Вечірня розтяжка", 
                "Час для вечірньої розтяжки! ", 
                time(20, 0)
            )
        
        elif user.chat_id == USER_CHAT_IDS[2]:  # Third user
            # Breakfast reminder
            create_custom_notification(
                db, 
                user.id, 
                "Сніданок", 
                "Час для сніданку! ", 
                time(9, 0)
            )
            
            # Lunch reminder
            create_custom_notification(
                db, 
                user.id, 
                "Обід", 
                "Час для обіду! ", 
                time(13, 0)
            )
    
    print("Notification preferences created.")


def create_custom_notification(db: Session, user_id: int, name: str, message: str, notification_time: time):
    """Helper function to create a custom notification."""
    # Create a timezone-aware next execution datetime
    current_time = datetime.now(tz=timezone)
    
    # Create a datetime with today's date and the notification time
    notification_datetime = timezone.localize(
        datetime(
            current_time.year,
            current_time.month,
            current_time.day,
            notification_time.hour,
            notification_time.minute,
            0
        )
    )
    
    # If the time has already passed today, set it for tomorrow
    if notification_datetime < current_time:
        notification_datetime += timedelta(days=1)
    
    # Create a new custom notification
    custom_notification = CustomNotification(
        user_id=user_id,
        notification_name=name,
        notification_message=message,
        notification_time=notification_time,
        next_execution_datetime=notification_datetime,
        is_active=True,
        notification_sent=False,
        created_at=datetime.now(tz=timezone) - timedelta(days=random.randint(30, 60))
    )
    
    db.add(custom_notification)
    db.commit()
    
    return custom_notification


def generate_morning_quizzes(db: Session, users):
    """Generate morning quiz data for the past 3 months."""
    print("Generating morning quiz data...")
    
    # Assign a training pattern to each user
    user_patterns = {}
    for user in users:
        user_patterns[user.id] = random.choice(TRAINING_PATTERNS)
    
    # Generate data for each day in the 3-month period
    current_date = START_DATE
    while current_date <= CURRENT_DATE:
        for user in users:
            # Skip some days randomly (80% completion rate)
            if random.random() < 0.8:
                # Determine if today is a training day
                day_of_week = current_date.weekday()
                is_training_day = day_of_week in user_patterns[user.id]
                
                # Generate morning quiz
                morning_time = time(random.randint(7, 9), random.randint(0, 59))
                
                # User feelings vary but tend to be better on non-training days
                # and worse after training days
                base_feeling = 7  # Base feeling level
                
                # If yesterday was a training day, slightly worse feeling
                yesterday = current_date - timedelta(days=1)
                if yesterday.weekday() in user_patterns[user.id]:
                    base_feeling -= 1
                
                # Random variation
                feeling = max(1, min(10, base_feeling + random.randint(-2, 2)))
                
                # Sleep hours - typically 6-8 hours
                sleep_hours = time(random.randint(6, 8), random.randint(0, 59))
                
                # Weight fluctuates slightly
                base_weight = 75.0 if user.chat_id == USER_CHAT_IDS[0] else 65.0 if user.chat_id == USER_CHAT_IDS[1] else 70.0
                weight = round(base_weight + random.uniform(-1.0, 1.0), 1)
                
                # Create the quiz
                quiz = MorningQuiz(
                    user_id=user.id,
                    quiz_datetime=current_date.replace(hour=morning_time.hour, minute=morning_time.minute),
                    user_feelings=feeling,
                    user_feelings_comment=None,
                    user_sleeping_hours=sleep_hours,
                    user_weight=weight,
                    is_going_to_have_training=is_training_day,
                    expected_training_datetime=current_date.replace(hour=18, minute=0) if is_training_day else None
                )
                db.add(quiz)
        
        current_date += timedelta(days=1)
    
    db.commit()
    print("Morning quiz data generated.")

def generate_training_data(db: Session, users):
    """Generate training data for the past 3 months."""
    print("Generating training data...")
    
    # Assign a training pattern to each user
    user_patterns = {}
    for i, user in enumerate(users):
        # Assign different training patterns to each user
        pattern_index = i % len(TRAINING_PATTERNS)
        user_patterns[user.id] = TRAINING_PATTERNS[pattern_index]
    
    # Generate data for each day in the 3-month period
    current_date = START_DATE
    while current_date <= CURRENT_DATE:
        for user in users:
            # Check if today is a training day
            day_of_week = current_date.weekday()
            if day_of_week in user_patterns[user.id]:
                # Skip some training days randomly (10% skip rate)
                if random.random() < 0.9:
                    # Generate training data
                    
                    # Mark before training (1-10)
                    mark_before = random.randint(5, 9)
                    
                    # Training start time (typically evening)
                    # Different users have different preferred training times
                    if user.chat_id == USER_CHAT_IDS[0]:  # First user
                        start_hour = random.randint(17, 19)  # Earlier evening
                    elif user.chat_id == USER_CHAT_IDS[1]:  # Second user
                        start_hour = random.randint(18, 20)  # Mid evening
                    else:  # Third user
                        start_hour = random.randint(19, 21)  # Later evening
                        
                    start_minute = random.randint(0, 59)
                    training_start = current_date.replace(hour=start_hour, minute=start_minute)
                    
                    # Training duration (30-90 minutes)
                    # Different users have different training durations
                    if user.chat_id == USER_CHAT_IDS[0]:  # First user
                        duration_minutes = random.randint(45, 75)  # Longer workouts
                    elif user.chat_id == USER_CHAT_IDS[1]:  # Second user
                        duration_minutes = random.randint(30, 60)  # Medium workouts
                    else:  # Third user
                        duration_minutes = random.randint(40, 70)  # Varied workouts
                        
                    training_duration = time(0, duration_minutes)
                    
                    # Training finish time
                    training_finish = training_start + timedelta(minutes=duration_minutes)
                    
                    # Training hardness (1-10)
                    # Different users have different training intensities
                    if user.chat_id == USER_CHAT_IDS[0]:  # First user
                        training_hardness = random.randint(7, 10)  # Higher intensity
                    elif user.chat_id == USER_CHAT_IDS[1]:  # Second user
                        training_hardness = random.randint(5, 8)  # Medium intensity
                    else:  # Third user
                        training_hardness = random.randint(6, 9)  # Varied intensity
                    
                    # Training discomfort (10% chance)
                    training_discomfort = random.random() < 0.1
                    
                    # Stress on next day (1-10)
                    stress_next_day = random.randint(3, 7)
                    
                    # Soreness on next day (60% chance)
                    soreness_next_day = random.random() < 0.6
                    
                    # Create the training record
                    training = Training(
                        user_id=user.id,
                        mark_before_training=mark_before,
                        training_start_date=training_start,
                        training_finish_date=training_finish,
                        training_duration=training_duration,
                        training_hardness=training_hardness,
                        training_discomfort=training_discomfort,
                        stress_on_next_day=stress_next_day,
                        soreness_on_next_day=soreness_next_day,
                        canceled=False
                    )
                    db.add(training)
        
        current_date += timedelta(days=1)
    
    db.commit()
    print("Training data generated.")

def main():
    """Main function to generate test data."""
    print("Starting test data generation...")
    
    with next(get_db()) as db:
        # Clear existing data
        clear_existing_data(db)
        
        # Create users
        users = create_users(db)
        
        # Create notification preferences
        create_notification_preferences(db, users)
        
        # Generate morning quiz data
        generate_morning_quizzes(db, users)
        
        # Generate training data
        generate_training_data(db, users)
    
    print("Test data generation complete!")

if __name__ == "__main__":
    main()
