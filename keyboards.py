import text_constants
from telegram import ReplyKeyboardMarkup
from database import get_db
from db_utils import get_user_notifications


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [[text_constants.TRAINING, text_constants.SETTINGS]],
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
