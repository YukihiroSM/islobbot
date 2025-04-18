from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

import text_constants
from database import get_db
from utils.db_utils import get_user_notifications
from utils.bot_utils import get_user_list_as_buttons
from config import ADMIN_CHAT_IDS
from utils.logger import get_logger

logger = get_logger(__name__)


def main_menu_keyboard(chat_id):
    logger.debug(f"Creating main menu keyboard for user {chat_id}")
    keyboard = [[text_constants.TRAINING]]
    if str(chat_id) in ADMIN_CHAT_IDS:
        logger.debug(f"User {chat_id} is admin, adding admin options")
        keyboard.append([text_constants.TRAINING_PDF])
    keyboard.append([text_constants.CUSTOM_NOTIFICATIONS])
    keyboard.append([text_constants.STATISTICS])
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def settings_menu_keyboard():
    logger.debug("Creating settings menu keyboard")
    return ReplyKeyboardMarkup(
        [[text_constants.CONFIGURE_NOTIFICATIONS], [text_constants.GO_BACK]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def notification_configuration_keyboard():
    logger.debug("Creating notification configuration keyboard")
    return ReplyKeyboardMarkup(
        [
            [
                text_constants.CHANGE_NOTIFICATION_TIME,
                text_constants.TURN_ON_OFF_NOTIFICATIONS,
            ],
            [text_constants.ADD_CUSTOM_NOTIFICATION],
            [text_constants.MANAGE_CUSTOM_NOTIFICATIONS],
            [text_constants.GO_BACK],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_notifications_keyboard(chat_id: int):
    logger.debug(f"Creating notifications keyboard for user {chat_id}")
    db_session = next(get_db())
    active_notifications = get_user_notifications(
        chat_id=chat_id, db_session=db_session, is_active=True
    )
    inactive_notifications = get_user_notifications(
        chat_id=chat_id, db_session=db_session, is_active=False
    )
    logger.debug(f"Found {len(active_notifications)} active and {len(inactive_notifications)} inactive notifications")
    
    buttons = []
    for notification in active_notifications:
        buttons.append(f"{notification.notification_time} - ✅ Увімкнено")

    for notification in inactive_notifications:
        buttons.append(f"{notification.notification_time} - ❌ Вимкнено")

    buttons.append(text_constants.GO_BACK)

    return ReplyKeyboardMarkup([buttons], resize_keyboard=True, one_time_keyboard=True)


def training_menu_keyboard():
    logger.debug("Creating training menu keyboard")
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
    logger.debug("Creating training first question marks keyboard")
    return ReplyKeyboardMarkup(
        [
            [str(i) for i in range(1, 6)],
            [str(i) for i in range(6, 11)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def default_one_to_ten_keyboard():
    logger.debug("Creating default one to ten keyboard")
    return ReplyKeyboardMarkup(
        [
            [str(i) for i in range(1, 6)],
            [str(i) for i in range(6, 11)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def training_in_progress_keyboard():
    logger.debug("Creating training in progress keyboard")
    return ReplyKeyboardMarkup(
        [
            [text_constants.END_TRAINING],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def start_morning_quiz_keyboard():
    logger.debug("Creating start morning quiz keyboard")
    keyboard = [
        [InlineKeyboardButton("Пройти опитування", callback_data="morning_quiz")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def yes_no_keyboard():
    logger.debug("Creating yes/no keyboard")
    return ReplyKeyboardMarkup(
        [
            text_constants.YES_NO_BUTTONS,
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def pdf_user_list_keyboard():
    logger.debug("Creating PDF user list keyboard")
    buttons = get_user_list_as_buttons("pdf_assignment")
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)


def custom_notification_keyboard():
    """Keyboard for custom notification settings."""
    logger.debug("Creating custom notification keyboard")
    return ReplyKeyboardMarkup(
        [
            [text_constants.ADD_CUSTOM_NOTIFICATION],
            [text_constants.MANAGE_CUSTOM_NOTIFICATIONS],
            [text_constants.GO_BACK],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
