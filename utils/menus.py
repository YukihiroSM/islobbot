from telegram import Update
from telegram.ext import ContextTypes

import text_constants
import conversations
from utils import keyboards
from utils.notification_utils import (
    switch_notifications,
    change_user_notification_time,
    handle_notification_time_change,
)
from utils.logger import get_logger

logger = get_logger(__name__)


async def settings_menu(update, context):
    logger.debug(f"User {update.effective_user.id} opened settings menu")
    context.user_data["menu_state"] = "settings_menu"
    await update.message.reply_text(
        text=text_constants.SETTING_MENU_TEXT,
        reply_markup=keyboards.settings_menu_keyboard(),
    )


async def configure_notifications_menu(update, context):
    logger.debug(f"User {update.effective_user.id} opened notifications menu")
    context.user_data["menu_state"] = "notifications_menu"
    await update.message.reply_text(
        text=text_constants.NOTIFICATION_MENU_TEXT,
        reply_markup=keyboards.notification_configuration_keyboard(),
    )


async def main_menu(update, context):
    logger.debug(f"User {update.effective_user.id} opened main menu")
    context.user_data["menu_state"] = "main_menu"
    await update.message.reply_text(
        text=text_constants.MAIN_MENU_TEXT,
        reply_markup=keyboards.main_menu_keyboard(update.effective_chat.id),
    )


async def notification_time_change_menu(update, context):
    logger.debug(f"User {update.effective_user.id} opened notification time change menu")
    context.user_data["menu_state"] = "change_notification_time"
    await update.message.reply_text(
        text=text_constants.CHANGE_NOTIFICATION_TIME_TEXT,
        reply_markup=keyboards.get_notifications_keyboard(update.effective_user.id),
    )


async def training_menu(update, context):
    logger.debug(f"User {update.effective_user.id} opened training menu")
    context.user_data["menu_state"] = "training_menu"
    await update.message.reply_text(
        text=text_constants.TRAINING_MENU_TEXT,
        reply_markup=keyboards.training_menu_keyboard(),
    )


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    user_id = update.effective_user.id
    logger.info(f"User {user_id} menu input: '{user_input}'")

    if "menu_state" not in context.user_data:
        logger.debug(f"No menu state for user {user_id}, showing main menu")
        await main_menu(update, context)

    # main menu handling
    if user_input == text_constants.TRAINING:
        logger.debug(f"User {user_id} selected training option")
        await training_menu(update, context)

    if user_input == text_constants.SETTINGS:
        logger.debug(f"User {user_id} selected settings option")
        await settings_menu(update, context)
        
    if user_input == text_constants.CUSTOM_NOTIFICATIONS:
        logger.debug(f"User {user_id} selected custom notifications option")
        await conversations.custom_notification_conversation.manage_custom_notifications(update, context)
        
    if user_input == text_constants.STATISTICS:
        logger.debug(f"User {user_id} selected statistics option")
        await conversations.statistics_conversation.start_statistics(update, context)

    # settings menu handling

    if user_input == text_constants.GO_BACK:
        current_state = context.user_data.get("menu_state", "unknown")
        logger.debug(f"User {user_id} selected go back from {current_state}")
        if context.user_data["menu_state"] == "settings_menu":
            await main_menu(update, context)
        if context.user_data["menu_state"] == "notifications_menu":
            await settings_menu(update, context)
        if context.user_data["menu_state"] == "switch_notifications":
            await configure_notifications_menu(update, context)
        if context.user_data["menu_state"] == "change_notification_time":
            await configure_notifications_menu(update, context)
        if context.user_data["menu_state"] == "training_menu":
            await main_menu(update, context)

    if user_input == text_constants.CONFIGURE_NOTIFICATIONS:
        logger.debug(f"User {user_id} selected configure notifications")
        await configure_notifications_menu(update, context)

    # Notifications config menu
    if user_input == text_constants.TURN_ON_OFF_NOTIFICATIONS:
        logger.debug(f"User {user_id} selected turn on/off notifications")
        await switch_notifications(update, context)

    if user_input == text_constants.CHANGE_NOTIFICATION_TIME:
        logger.debug(f"User {user_id} selected change notification time")
        await notification_time_change_menu(update, context)

    # training menu handling

    if (
        context.user_data["menu_state"] == "training_menu"
        and user_input == text_constants.START_TRAINING
    ):
        logger.debug(f"User {user_id} selected start training")
        await conversations.training_start_conversation.handle_training_startup(
            update, context
        )

    # handle anything else

    if context.user_data["menu_state"] == "switch_notifications":
        logger.debug(f"User {user_id} in switch notifications state")
        await switch_notifications(update, context)

    if context.user_data["menu_state"] == "change_notification_time":
        logger.debug(f"User {user_id} in change notification time state")
        if "notification_to_change" in context.user_data:
            await change_user_notification_time(update, context)
        else:
            await handle_notification_time_change(update, context)

    return
