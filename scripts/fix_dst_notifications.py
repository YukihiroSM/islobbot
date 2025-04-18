#!/usr/bin/env python3
"""
Script to fix notification times after DST (Daylight Saving Time) change.
This script adjusts all notification times to match the current timezone settings.
"""

import sys
import os
from datetime import datetime, timedelta
from loguru import logger
import pytz

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import NotificationPreference, CustomNotification
from config import timezone

def fix_notification_preferences():
    """Fix the notification times in NotificationPreference table."""
    logger.info("Fixing notification preferences for DST change")
    
    updated_count = 0
    with next(get_db()) as db_session:
        preferences = db_session.query(NotificationPreference).all()
        
        for preference in preferences:
            user = preference.user
            if not user or not user.timezone:
                logger.warning(f"User or timezone missing for preference ID {preference.id}")
                continue
                
            try:
                timezone = pytz.timezone(user.timezone)
                current_time = preference.notification_time
                
                # Get the next execution datetime
                next_exec = preference.next_execution_datetime
                
                if next_exec:
                    now = datetime.now(tz=timezone)
                    notification_datetime = timezone.localize(
                        datetime(
                            now.year, 
                            now.month, 
                            now.day, 
                            current_time.hour, 
                            current_time.minute
                        )
                    )
                    
                    if notification_datetime < now:
                        notification_datetime += timedelta(days=1)
                    
                    preference.next_execution_datetime = notification_datetime
                    updated_count += 1
                    logger.debug(f"Updated notification time for user {user.id} to {notification_datetime}")
                
            except Exception as e:
                logger.error(f"Error updating preference ID {preference.id}: {e}")
        
        db_session.commit()
        logger.success(f"Updated {updated_count} notification preferences")

def fix_custom_notifications():
    """Fix the notification times in CustomNotification table."""
    logger.info("Fixing custom notifications for DST change")
    
    updated_count = 0
    with next(get_db()) as db_session:
        notifications = db_session.query(CustomNotification).filter_by(is_active=True).all()
        
        for notification in notifications:
            # Get the current notification time
            current_time = notification.notification_time
            
            # Get the next execution datetime
            next_exec = notification.next_execution_datetime
            
            if next_exec:
                # Create a new next_execution_datetime based on the current timezone
                now = datetime.now(tz=timezone)
                
                # Create a datetime with today's date and the notification time
                notification_datetime = timezone.localize(
                    datetime(
                        now.year, 
                        now.month, 
                        now.day, 
                        current_time.hour, 
                        current_time.minute
                    )
                )
                
                # If the time has already passed today, set it for tomorrow
                if notification_datetime < now:
                    notification_datetime += timedelta(days=1)
                
                # Update the next_execution_datetime
                notification.next_execution_datetime = notification_datetime
                updated_count += 1
        
        db_session.commit()
        logger.success(f"Updated {updated_count} custom notifications")

def main():
    """Main function to fix notification times."""
    logger.info("Starting notification time fix for DST change...")
    
    # Fix notification preferences
    fix_notification_preferences()
    
    # Fix custom notifications
    # fix_custom_notifications()
    
    logger.success("Notification time fix complete!")

if __name__ == "__main__":
    main()
