from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

import text_constants
from database import get_db
from utils.db_utils import get_user_notifications
from utils.bot_utils import get_user_list_as_buttons
from config import ADMIN_CHAT_IDS


def main_menu_keyboard(chat_id):
    keyboard = [[text_constants.TRAINING]]
    if str(chat_id) in ADMIN_CHAT_IDS:
        keyboard.append(
            [text_constants.TRAINING_PDF]
        )
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def settings_menu_keyboard():
    return ReplyKeyboardMarkup(
        [[text_constants.CONFIGURE_NOTIFICATIONS], [text_constants.GO_BACK]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def notification_configuration_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                text_constants.CHANGE_NOTIFICATION_TIME,
                text_constants.TURN_ON_OFF_NOTIFICATIONS,
            ],
            [text_constants.GO_BACK],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_notifications_keyboard(chat_id: int):
    db_session = next(get_db())
    active_notifications = get_user_notifications(
        chat_id=chat_id, db_session=db_session, is_active=True
    )
    inactive_notifications = get_user_notifications(
        chat_id=chat_id, db_session=db_session, is_active=False
    )
    buttons = []
    for notification in active_notifications:
        buttons.append(f"{notification.notification_time} - ✅ Увімкнено")

    for notification in inactive_notifications:
        buttons.append(f"{notification.notification_time} - ❌ Вимкнено")

    buttons.append(text_constants.GO_BACK)

    return ReplyKeyboardMarkup([buttons], resize_keyboard=True, one_time_keyboard=True)


def training_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                text_constants.START_TRAINING,
            ],
            [text_constants.GO_BACK],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def training_first_question_marks_keyboard():
    return ReplyKeyboardMarkup(
        [
            [str(i) for i in range(1, 6)],
            [str(i) for i in range(6, 11)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def default_one_to_ten_keyboard():
    return ReplyKeyboardMarkup(
        [
            [str(i) for i in range(1, 6)],
            [str(i) for i in range(6, 11)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def training_in_progress_keyboard():
    return ReplyKeyboardMarkup(
        [
            [text_constants.END_TRAINING],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def start_morning_quiz_keyboard():
    keyboard = [
        [InlineKeyboardButton("Пройти опитування", callback_data="morning_quiz")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def yes_no_keyboard():
    return ReplyKeyboardMarkup(
        [
            text_constants.YES_NO_BUTTONS,
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def pdf_user_list_keyboard():
    buttons = get_user_list_as_buttons("pdf_assignment")
    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )