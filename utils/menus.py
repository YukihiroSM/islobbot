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


async def settings_menu(update, context):
    context.user_data["menu_state"] = "settings_menu"
    await update.message.reply_text(
        "Меню налаштувань. Оберіть, що ви бажаєте налаштувати:",
        reply_markup=keyboards.settings_menu_keyboard(),
    )


async def configure_notifications_menu(update, context):
    context.user_data["menu_state"] = "notifications_menu"
    await update.message.reply_text(
        "Конфігурація сповіщень. Оберіть, що бажаєте налаштувати:",
        reply_markup=keyboards.notification_configuration_keyboard(),
    )


async def main_menu(update, context):
    context.user_data["menu_state"] = "main_menu"
    await update.message.reply_text(
        "Головне меню:", reply_markup=keyboards.main_menu_keyboard(update.effective_chat.id)
    )


async def notification_time_change_menu(update, context):
    context.user_data["menu_state"] = "change_notification_time"
    await update.message.reply_text(
        "Натисніть на сповіщення, щоб змінити його час спрацювання:",
        reply_markup=keyboards.get_notifications_keyboard(update.effective_user.id),
    )


async def training_menu(update, context):
    context.user_data["menu_state"] = "training_menu"
    await update.message.reply_text(
        "Час поглянути на тренування!", reply_markup=keyboards.training_menu_keyboard()
    )


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    if "menu_state" not in context.user_data:
        await main_menu(update, context)

    # main menu handling
    if user_input == text_constants.TRAINING:
        await training_menu(update, context)

    if user_input == text_constants.SETTINGS:
        await settings_menu(update, context)

    # settings menu handling

    if user_input == text_constants.GO_BACK:
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
        await configure_notifications_menu(update, context)

    # Notifications config menu
    if user_input == text_constants.TURN_ON_OFF_NOTIFICATIONS:
        await switch_notifications(update, context)

    if user_input == text_constants.CHANGE_NOTIFICATION_TIME:
        await notification_time_change_menu(update, context)

    # training menu handling

    if (
        context.user_data["menu_state"] == "training_menu"
        and user_input == text_constants.START_TRAINING
    ):
        await conversations.training_start_conversation.handle_training_startup(
            update, context
        )

    # handle anything else

    if context.user_data["menu_state"] == "switch_notifications":
        await switch_notifications(update, context)

    if context.user_data["menu_state"] == "change_notification_time":
        if "notification_to_change" in context.user_data:
            await change_user_notification_time(update, context)
        else:
            await handle_notification_time_change(update, context)

    return
