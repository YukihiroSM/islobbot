from enum import Enum, auto
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
import re
import logging

import text_constants
from utils.bot_utils import is_valid_time
from database import get_db
from utils.db_utils import (
    save_custom_notification,
    get_user_custom_notifications,
    delete_custom_notification,
)
from utils.keyboards import main_menu_keyboard
from utils.commands import cancel


class CustomNotificationConversation(Enum):
    GET_NAME = auto()
    GET_MESSAGE = auto()
    GET_TIME = auto()
    GET_PERIODICITY = auto()
    SELECT_DAYS = auto()
    SELECT_WEEK_DAY = auto()
    SELECT_MONTH_DAY = auto()
    CONFIRM_DELETE = auto()
    MANAGE = auto()


async def start_custom_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the custom notification creation process."""
    logging.info("start_custom_notification triggered")
    await update.message.reply_text(text=text_constants.CUSTOM_NOTIFICATION_NAME_PROMPT)
    return CustomNotificationConversation.GET_NAME


async def get_notification_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the name for the custom notification."""
    notification_name = update.message.text
    context.user_data["custom_notification_name"] = notification_name
    
    await update.message.reply_text(
        text=text_constants.CUSTOM_NOTIFICATION_MESSAGE_PROMPT
    )
    return CustomNotificationConversation.GET_MESSAGE


async def get_notification_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the message for the custom notification."""
    notification_message = update.message.text
    context.user_data["custom_notification_message"] = notification_message
    
    await update.message.reply_text(
        text=text_constants.CUSTOM_NOTIFICATION_TIME_PROMPT
    )
    return CustomNotificationConversation.GET_TIME


async def get_notification_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the notification time from the user."""
    notification_time = update.message.text.strip()
    
    # Validate the time format
    if not is_valid_time(notification_time):
        await update.message.reply_text(
            text=text_constants.INVALID_TIME_FORMAT,
        )
        return CustomNotificationConversation.GET_TIME
    
    # Store the notification time
    context.user_data["notification_time"] = notification_time
    
    # Show periodicity selection keyboard
    keyboard = [
        [text_constants.DAILY_DESC],
        [text_constants.WEEKLY_DESC.format(day="")],
        [text_constants.MONTHLY_DESC.format(day="")],
        [text_constants.SPECIFIC_DAYS_DESC],
        [text_constants.GO_BACK]
    ]
    
    await update.message.reply_text(
        text=text_constants.CUSTOM_NOTIFICATION_PERIODICITY_PROMPT,
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        ),
    )
    
    return CustomNotificationConversation.GET_PERIODICITY


async def handle_periodicity_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle periodicity selection."""
    user_input = update.message.text
    
    if user_input == text_constants.GO_BACK:
        # Go back to the previous step
        await update.message.reply_text(
            text=text_constants.CUSTOM_NOTIFICATION_TIME_PROMPT,
        )
        return CustomNotificationConversation.GET_TIME
    
    # Determine the selected periodicity
    if user_input == text_constants.DAILY_DESC:
        periodicity = text_constants.DAILY
    elif user_input == text_constants.WEEKLY_DESC.format(day=""):
        periodicity = text_constants.WEEKLY
    elif user_input == text_constants.MONTHLY_DESC.format(day=""):
        periodicity = text_constants.MONTHLY
    elif user_input == text_constants.SPECIFIC_DAYS_DESC:
        periodicity = text_constants.SPECIFIC_DAYS
    else:
        # Invalid input, ask again
        keyboard = [
            [text_constants.DAILY_DESC],
            [text_constants.WEEKLY_DESC.format(day="")],
            [text_constants.MONTHLY_DESC.format(day="")],
            [text_constants.SPECIFIC_DAYS_DESC],
            [text_constants.GO_BACK]
        ]
        
        await update.message.reply_text(
            text=text_constants.CUSTOM_NOTIFICATION_PERIODICITY_PROMPT,
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            ),
        )
        return CustomNotificationConversation.GET_PERIODICITY
    
    context.user_data["periodicity_type"] = periodicity
    
    if periodicity == text_constants.SPECIFIC_DAYS:
        # Show day selection keyboard
        days = [
            {"text": text_constants.MONDAY, "value": "0"},
            {"text": text_constants.TUESDAY, "value": "1"},
            {"text": text_constants.WEDNESDAY, "value": "2"},
            {"text": text_constants.THURSDAY, "value": "3"},
            {"text": text_constants.FRIDAY, "value": "4"},
            {"text": text_constants.SATURDAY, "value": "5"},
            {"text": text_constants.SUNDAY, "value": "6"},
        ]
        
        # Initialize selected_days if it doesn't exist
        if "selected_days" not in context.user_data:
            context.user_data["selected_days"] = []
        
        # Create keyboard with days of the week
        keyboard = []
        row = []
        
        for day in days:
            # Add a checkmark if the day is selected
            display_text = f"✅ {day['text']}" if day["value"] in context.user_data["selected_days"] else day["text"]
            row.append(display_text)
            
            # Create rows with 3 buttons each
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        # Add any remaining buttons
        if row:
            keyboard.append(row)
        
        # Add a "Done" button
        keyboard.append([text_constants.DONE])
        keyboard.append([text_constants.GO_BACK])
        
        await update.message.reply_text(
            text=text_constants.CUSTOM_NOTIFICATION_DAYS_PROMPT,
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            ),
        )
        return CustomNotificationConversation.SELECT_DAYS
    elif periodicity == text_constants.WEEKLY:
        # Show day of week selection keyboard
        days = [
            {"text": text_constants.MONDAY, "value": "0"},
            {"text": text_constants.TUESDAY, "value": "1"},
            {"text": text_constants.WEDNESDAY, "value": "2"},
            {"text": text_constants.THURSDAY, "value": "3"},
            {"text": text_constants.FRIDAY, "value": "4"},
            {"text": text_constants.SATURDAY, "value": "5"},
            {"text": text_constants.SUNDAY, "value": "6"},
        ]
        
        # Create keyboard with days of the week
        keyboard = []
        row = []
        
        for day in days:
            row.append(day["text"])
            
            # Create rows with 3 buttons each
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        # Add any remaining buttons
        if row:
            keyboard.append(row)
        
        # Add a "Back" button
        keyboard.append([text_constants.GO_BACK])
        
        await update.message.reply_text(
            text=text_constants.CUSTOM_NOTIFICATION_WEEK_DAY_PROMPT,
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            ),
        )
        return CustomNotificationConversation.SELECT_WEEK_DAY
    elif periodicity == text_constants.MONTHLY:
        # Show day of month selection keyboard
        keyboard = []
        row = []
        
        # Create buttons for days 1-31
        for day in range(1, 32):
            row.append(str(day))
            
            # Create rows with 7 buttons each
            if len(row) == 7:
                keyboard.append(row)
                row = []
        
        # Add any remaining buttons
        if row:
            keyboard.append(row)
        
        # Add a "Back" button
        keyboard.append([text_constants.GO_BACK])
        
        await update.message.reply_text(
            text=text_constants.CUSTOM_NOTIFICATION_MONTH_DAY_PROMPT,
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            ),
        )
        return CustomNotificationConversation.SELECT_MONTH_DAY
    else:
        # Save the notification with the selected periodicity
        return await save_notification_with_periodicity(update, context)


async def handle_day_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle day selection for specific days periodicity."""
    user_input = update.message.text
    
    if user_input == text_constants.GO_BACK:
        # Go back to the previous step
        keyboard = [
            [text_constants.DAILY_DESC],
            [text_constants.WEEKLY_DESC.format(day="")],
            [text_constants.MONTHLY_DESC.format(day="")],
            [text_constants.SPECIFIC_DAYS_DESC],
            [text_constants.GO_BACK]
        ]
        
        await update.message.reply_text(
            text=text_constants.CUSTOM_NOTIFICATION_PERIODICITY_PROMPT,
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            ),
        )
        return CustomNotificationConversation.GET_PERIODICITY
    
    # Handle day selection/deselection
    day = user_input
    
    # Extract day value from the text (removing checkmark if present)
    day_value = None
    for day_info in [
        {"text": text_constants.MONDAY, "value": "0"},
        {"text": text_constants.TUESDAY, "value": "1"},
        {"text": text_constants.WEDNESDAY, "value": "2"},
        {"text": text_constants.THURSDAY, "value": "3"},
        {"text": text_constants.FRIDAY, "value": "4"},
        {"text": text_constants.SATURDAY, "value": "5"},
        {"text": text_constants.SUNDAY, "value": "6"},
    ]:
        if day.replace("✅ ", "") == day_info["text"]:
            day_value = day_info["value"]
            break
    
    # If it's not a valid day or it's the "Done" button
    if day_value is None:
        if user_input == text_constants.DONE:
            # Check if at least one day is selected
            if "selected_days" not in context.user_data or not context.user_data["selected_days"]:
                # Ask again if no days selected
                await update.message.reply_text(
                    text="Оберіть хоча б один день!",
                )
                return CustomNotificationConversation.SELECT_DAYS
            
            # Save the notification with the selected days
            return await save_notification_with_periodicity(update, context)
        
        # Invalid input, show the keyboard again
        days = [
            {"text": text_constants.MONDAY, "value": "0"},
            {"text": text_constants.TUESDAY, "value": "1"},
            {"text": text_constants.WEDNESDAY, "value": "2"},
            {"text": text_constants.THURSDAY, "value": "3"},
            {"text": text_constants.FRIDAY, "value": "4"},
            {"text": text_constants.SATURDAY, "value": "5"},
            {"text": text_constants.SUNDAY, "value": "6"},
        ]
        
        # Initialize selected_days if it doesn't exist
        if "selected_days" not in context.user_data:
            context.user_data["selected_days"] = []
        
        # Create keyboard with days of the week
        keyboard = []
        row = []
        
        for day in days:
            # Add a checkmark if the day is selected
            display_text = f"✅ {day['text']}" if day["value"] in context.user_data["selected_days"] else day["text"]
            row.append(display_text)
            
            # Create rows with 3 buttons each
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        # Add any remaining buttons
        if row:
            keyboard.append(row)
        
        # Add a "Done" button
        keyboard.append([text_constants.DONE])
        keyboard.append([text_constants.GO_BACK])
        
        await update.message.reply_text(
            text=text_constants.CUSTOM_NOTIFICATION_DAYS_PROMPT,
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            ),
        )
        return CustomNotificationConversation.SELECT_DAYS
    
    # Initialize selected_days if it doesn't exist
    if "selected_days" not in context.user_data:
        context.user_data["selected_days"] = []
    
    # Toggle the day selection
    if day_value in context.user_data["selected_days"]:
        context.user_data["selected_days"].remove(day_value)
    else:
        context.user_data["selected_days"].append(day_value)
    
    # Create keyboard with days of the week
    days = [
        {"text": text_constants.MONDAY, "value": "0"},
        {"text": text_constants.TUESDAY, "value": "1"},
        {"text": text_constants.WEDNESDAY, "value": "2"},
        {"text": text_constants.THURSDAY, "value": "3"},
        {"text": text_constants.FRIDAY, "value": "4"},
        {"text": text_constants.SATURDAY, "value": "5"},
        {"text": text_constants.SUNDAY, "value": "6"},
    ]
    
    keyboard = []
    row = []
    
    for day in days:
        # Add a checkmark if the day is selected
        display_text = f"✅ {day['text']}" if day["value"] in context.user_data["selected_days"] else day["text"]
        row.append(display_text)
        
        # Create rows with 3 buttons each
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    # Add any remaining buttons
    if row:
        keyboard.append(row)
    
    # Add a "Done" button
    keyboard.append([text_constants.DONE])
    keyboard.append([text_constants.GO_BACK])
    
    await update.message.reply_text(
        text=text_constants.CUSTOM_NOTIFICATION_DAYS_PROMPT,
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        ),
    )
    
    return CustomNotificationConversation.SELECT_DAYS


async def handle_week_day_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle day selection for weekly periodicity."""
    user_input = update.message.text
    
    if user_input == text_constants.GO_BACK:
        # Go back to the previous step
        keyboard = [
            [text_constants.DAILY_DESC],
            [text_constants.WEEKLY_DESC.format(day="")],
            [text_constants.MONTHLY_DESC.format(day="")],
            [text_constants.SPECIFIC_DAYS_DESC],
            [text_constants.GO_BACK]
        ]
        
        await update.message.reply_text(
            text=text_constants.CUSTOM_NOTIFICATION_PERIODICITY_PROMPT,
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            ),
        )
        return CustomNotificationConversation.GET_PERIODICITY
    
    # Get the selected day
    day_value = None
    for day_info in [
        {"text": text_constants.MONDAY, "value": "0"},
        {"text": text_constants.TUESDAY, "value": "1"},
        {"text": text_constants.WEDNESDAY, "value": "2"},
        {"text": text_constants.THURSDAY, "value": "3"},
        {"text": text_constants.FRIDAY, "value": "4"},
        {"text": text_constants.SATURDAY, "value": "5"},
        {"text": text_constants.SUNDAY, "value": "6"},
    ]:
        if user_input == day_info["text"]:
            day_value = day_info["value"]
            break
    
    if day_value is None:
        # Invalid input, show the keyboard again
        days = [
            {"text": text_constants.MONDAY, "value": "0"},
            {"text": text_constants.TUESDAY, "value": "1"},
            {"text": text_constants.WEDNESDAY, "value": "2"},
            {"text": text_constants.THURSDAY, "value": "3"},
            {"text": text_constants.FRIDAY, "value": "4"},
            {"text": text_constants.SATURDAY, "value": "5"},
            {"text": text_constants.SUNDAY, "value": "6"},
        ]
        
        # Create keyboard with days of the week
        keyboard = []
        row = []
        
        for day in days:
            row.append(day["text"])
            
            # Create rows with 3 buttons each
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        # Add any remaining buttons
        if row:
            keyboard.append(row)
        
        # Add a "Back" button
        keyboard.append([text_constants.GO_BACK])
        
        await update.message.reply_text(
            text=text_constants.CUSTOM_NOTIFICATION_WEEK_DAY_PROMPT,
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            ),
        )
        return CustomNotificationConversation.SELECT_WEEK_DAY
    
    context.user_data["specific_days"] = day_value
    
    # Save the notification with the selected day
    return await save_notification_with_periodicity(update, context)


async def handle_month_day_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle day selection for monthly periodicity."""
    user_input = update.message.text
    
    if user_input == text_constants.GO_BACK:
        # Go back to the previous step
        keyboard = [
            [text_constants.DAILY_DESC],
            [text_constants.WEEKLY_DESC.format(day="")],
            [text_constants.MONTHLY_DESC.format(day="")],
            [text_constants.SPECIFIC_DAYS_DESC],
            [text_constants.GO_BACK]
        ]
        
        await update.message.reply_text(
            text=text_constants.CUSTOM_NOTIFICATION_PERIODICITY_PROMPT,
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            ),
        )
        return CustomNotificationConversation.GET_PERIODICITY
    
    # Get the selected day
    try:
        day = int(user_input)
        if day < 1 or day > 31:
            raise ValueError("Day out of range")
    except ValueError:
        # Invalid input, show the keyboard again
        keyboard = []
        row = []
        
        # Create buttons for days 1-31
        for day in range(1, 32):
            row.append(str(day))
            
            # Create rows with 7 buttons each
            if len(row) == 7:
                keyboard.append(row)
                row = []
        
        # Add any remaining buttons
        if row:
            keyboard.append(row)
        
        # Add a "Back" button
        keyboard.append([text_constants.GO_BACK])
        
        await update.message.reply_text(
            text=text_constants.CUSTOM_NOTIFICATION_MONTH_DAY_PROMPT,
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            ),
        )
        return CustomNotificationConversation.SELECT_MONTH_DAY
    
    context.user_data["specific_days"] = str(day)
    
    # Save the notification with the selected day
    return await save_notification_with_periodicity(update, context)


async def save_notification_with_periodicity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save the notification with the selected periodicity."""
    chat_id = update.effective_chat.id
    notification_name = context.user_data.get("custom_notification_name")
    notification_message = context.user_data.get("custom_notification_message")
    notification_time = context.user_data.get("notification_time")
    periodicity_type = context.user_data.get("periodicity_type")
    
    # For specific days, join the selected days with commas
    specific_days = None
    if periodicity_type == text_constants.SPECIFIC_DAYS and "selected_days" in context.user_data:
        specific_days = ",".join(context.user_data["selected_days"])
    elif (periodicity_type == text_constants.WEEKLY or periodicity_type == text_constants.MONTHLY) and "specific_days" in context.user_data:
        specific_days = context.user_data["specific_days"]
    
    # Get the periodicity description for the message
    periodicity_desc = text_constants.DAILY_DESC
    if periodicity_type == text_constants.WEEKLY:
        # Get the day name for weekly notifications
        day_value = int(specific_days) if specific_days else 0
        day_names = [
            text_constants.MONDAY,
            text_constants.TUESDAY,
            text_constants.WEDNESDAY,
            text_constants.THURSDAY,
            text_constants.FRIDAY,
            text_constants.SATURDAY,
            text_constants.SUNDAY,
        ]
        day_name = day_names[day_value]
        periodicity_desc = text_constants.WEEKLY_DESC.format(day=day_name)
    elif periodicity_type == text_constants.MONTHLY:
        # Get the day number for monthly notifications
        day_num = specific_days if specific_days else "1"
        periodicity_desc = text_constants.MONTHLY_DESC.format(day=day_num)
    elif periodicity_type == text_constants.SPECIFIC_DAYS:
        periodicity_desc = text_constants.SPECIFIC_DAYS_DESC
    
    # Save the notification
    with next(get_db()) as db_session:
        try:
            save_custom_notification(
                chat_id=chat_id,
                notification_name=notification_name,
                notification_message=notification_message,
                notification_time=notification_time,
                periodicity_type=periodicity_type,
                specific_days=specific_days,
                db_session=db_session,
            )
            
            # Clear user data
            context.user_data.clear()
            
            # Send confirmation message
            await update.message.reply_text(
                text=text_constants.CUSTOM_NOTIFICATION_CREATED.format(
                    name=notification_name,
                    time=notification_time,
                    periodicity=periodicity_desc,
                ),
                reply_markup=main_menu_keyboard(chat_id),
            )
            
            return ConversationHandler.END
        except Exception as e:
            print(f"Error saving notification: {e}")
            error_message = f"Помилка при збереженні сповіщення: {str(e)}"
            
            await update.message.reply_text(
                text=error_message,
                reply_markup=main_menu_keyboard(chat_id),
            )
            
            return ConversationHandler.END


async def manage_custom_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a list of custom notifications for management."""
    with next(get_db()) as db_session:
        chat_id = update.effective_chat.id
        notifications = get_user_custom_notifications(chat_id, db_session)
        
    if not notifications:
        # Create keyboard with button to create new notification
        keyboard = [
            [
                text_constants.ADD_CUSTOM_NOTIFICATION
            ],
            [
                text_constants.BACK_TO_MAIN_MENU
            ]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(
            text=text_constants.NO_CUSTOM_NOTIFICATIONS,
            reply_markup=reply_markup,
        )
        return CustomNotificationConversation.MANAGE
    
    keyboard = []
    for notification in notifications:
        # Build a details string to show the execution schedule
        details = f"{notification.notification_time}"
        
        if notification.periodicity_type and notification.periodicity_type.lower() != "daily":
            if notification.periodicity_type.lower() == "specific_days":
                # Convert day numbers to weekday names
                day_map = {
                    "0": "Пн",
                    "1": "Вт",
                    "2": "Ср",
                    "3": "Чт",
                    "4": "Пт",
                    "5": "Сб",
                    "6": "Нд"
                }
                if notification.specific_days:
                    days = [d.strip() for d in notification.specific_days.split(",")]
                    day_names = [day_map.get(day, day) for day in days]
                    details += f" (дні: {', '.join(day_names)})"
                else:
                    details += " (дні: не вказано)"
            elif notification.periodicity_type.lower() == "monthly":
                # Calculate next month name
                from datetime import datetime
                now = datetime.now()
                next_month = now.month % 12 + 1
                month_map = {
                    1: "Січень",
                    2: "Лютий",
                    3: "Березень",
                    4: "Квітень",
                    5: "Травень",
                    6: "Червень",
                    7: "Липень",
                    8: "Серпень",
                    9: "Вересень",
                    10: "Жовтень",
                    11: "Листопад",
                    12: "Грудень"
                }
                month_name = month_map.get(next_month, str(next_month))
                if notification.specific_days:
                    details += f" (в {month_name} {notification.specific_days} числа)"
                else:
                    details += f" (щомісячно, {month_name})"
            else:
                details += f" ({notification.periodicity_type})"
        else:
            details += " (щодня)"
        
        keyboard.append([
            f"{notification.notification_name} - {details}"
        ])
    
    # Add button to create new notification
    keyboard.append([
        text_constants.ADD_CUSTOM_NOTIFICATION
    ])
    
    # Add button to return to main menu
    keyboard.append([
        text_constants.BACK_TO_MAIN_MENU
    ])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        text=text_constants.CUSTOM_NOTIFICATION_MANAGE_PROMPT,
        reply_markup=reply_markup,
    )
    return CustomNotificationConversation.MANAGE


async def handle_manage_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle selection from the manage notifications menu."""
    user_input = update.message.text
    logging.info(f"handle_manage_selection received user input: {user_input}")
    
    if user_input == text_constants.ADD_CUSTOM_NOTIFICATION:
        await update.message.reply_text(text=text_constants.CUSTOM_NOTIFICATION_NAME_PROMPT)
        return CustomNotificationConversation.GET_NAME
    
    if user_input == text_constants.BACK_TO_MAIN_MENU:
        await update.message.reply_text(text=text_constants.BACK_TO_MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(update.effective_chat.id))
        return ConversationHandler.END
    
    # Find the notification ID from the user input
    notification_id = None
    for notification in get_user_custom_notifications(update.effective_chat.id, next(get_db())):
        if f"{notification.notification_name} - {notification.notification_time}" == user_input:
            notification_id = notification.id
            break
    
    if notification_id:
        context.user_data["notification_to_delete"] = notification_id
        
        # Create confirmation keyboard
        keyboard = [
            [
                text_constants.YES,
                text_constants.NO
            ]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(
            text=text_constants.CONFIRM_DELETE_NOTIFICATION,
            reply_markup=reply_markup,
        )
        return CustomNotificationConversation.CONFIRM_DELETE


async def handle_delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation of notification deletion."""
    user_input = update.message.text
    
    if user_input == text_constants.YES:
        notification_id = context.user_data.get("notification_to_delete")
        if notification_id:
            with next(get_db()) as db_session:
                delete_custom_notification(notification_id, db_session)
            
            await update.message.reply_text(
                text=text_constants.NOTIFICATION_DELETED,
            )
            
            # Clear user data
            if "notification_to_delete" in context.user_data:
                del context.user_data["notification_to_delete"]
    elif user_input == text_constants.NO:
        await update.message.reply_text(
            text=text_constants.DELETION_CANCELED,
        )
    
    return ConversationHandler.END


custom_notification_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("custom_notification", start_custom_notification),
        MessageHandler(
            filters.Regex("^{0}$".format(re.escape(text_constants.ADD_CUSTOM_NOTIFICATION))), 
            start_custom_notification
        ),
        MessageHandler(
            filters.Regex(f"^{text_constants.MANAGE_CUSTOM_NOTIFICATIONS}$"), 
            manage_custom_notifications
        ),
        MessageHandler(
            filters.Regex(f"^{text_constants.CUSTOM_NOTIFICATIONS}$"), 
            manage_custom_notifications
        ),
    ],
    states={
        CustomNotificationConversation.GET_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_notification_name)
        ],
        CustomNotificationConversation.GET_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_notification_message)
        ],
        CustomNotificationConversation.GET_TIME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_notification_time)
        ],
        CustomNotificationConversation.GET_PERIODICITY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_periodicity_selection)
        ],
        CustomNotificationConversation.SELECT_DAYS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_day_selection)
        ],
        CustomNotificationConversation.SELECT_WEEK_DAY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_week_day_selection)
        ],
        CustomNotificationConversation.SELECT_MONTH_DAY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_month_day_selection)
        ],
        CustomNotificationConversation.CONFIRM_DELETE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_delete_confirmation)
        ],
        CustomNotificationConversation.MANAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manage_selection)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="custom_notification_conversation",
)
