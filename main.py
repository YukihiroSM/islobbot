import datetime
import logging
import re
import time
from datetime import datetime, timedelta, time as datetime_time
from enum import Enum, auto

import asyncio
import schedule
from sqlalchemy.exc import DataError
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackContext,
)

import keyboards
import text_constants
from config import BOT_TOKEN, ADMIN_CHAT_ID, timezone
from config import DATABASE_URL
from database import get_db
from db_utils import (
    add_or_update_user,
    save_user_notification_preference,
    update_user_notification_time,
    update_user_full_name,
    is_user_ready_to_use,
    get_user_notification_by_time,
    toggle_user_notification,
    start_user_training,
    stop_training,
    get_notifications_to_send_by_time,
    update_user_notification_preference_next_execution, save_morning_quiz_results, is_user_had_morning_quiz_today,
)
from keyboards import main_menu_keyboard
from models import NotificationType


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class IntroConversation(Enum):
    NEW_COMER = auto()
    GET_NAME = auto()
    GET_TIME = auto()


class MorningQuizConversation(Enum):
    FIRST_QUESTION_ANSWER = auto()
    SECOND_QUESTION_ANSWER = auto()


class TrainingStartQuiz(Enum):
    FIRST_QUESTION_ANSWER = auto()


class TrainingFinishQuiz(Enum):
    FIRST_QUESTION_ANSWER = auto()
    SECOND_QUESTION_ANSWER = auto()


def is_valid_time(time_str: str) -> bool:
    try:
        match = re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", time_str)
        min_time = datetime_time(hour=6)
        max_time = datetime_time(hour=12)

        time = datetime.strptime(time_str, "%H:%M").time()
        if time < min_time or time > max_time:
            return False
        return bool(match)
    except Exception as e:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_session = next(get_db())
    context.user_data["menu_state"] = "starting_using_bot"
    is_new_user = add_or_update_user(
        update.effective_user.id, update.effective_user.username, db_session
    )

    if is_new_user or not is_user_ready_to_use(update.effective_user.id, db_session):
        await update.message.reply_text(
            "Ласкаво прошу до бота! (Тут має бути якийсь невеличкий опис)"
        )
        await update.message.reply_text("Для початку, введіть своє повне ім'я.")
        return IntroConversation.GET_NAME
    else:
        await update.message.reply_text(
            f"Привіт, {update.effective_user.username}!",
            reply_markup=main_menu_keyboard(),
        )


async def get_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    db_session = next(get_db())
    update_user_full_name(
        chat_id=update.effective_chat.id, full_name=name, db=db_session
    )
    await update.message.reply_text(
        f"Дякую, {name}! Тепер налаштуємо сповіщення. Введіть бажаний час для ранкового сповіщення. "
        f"Його потрібно увести в форматі '08:00'. "
        f"Введіть будь-який зручний час в рамках від 06:00 до 12:00! ",
    )
    return IntroConversation.GET_TIME


async def get_morning_notification_time(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    time_input = update.message.text
    if is_valid_time(time_input):
        db_session = next(get_db())
        hours, minutes = map(int, time_input.split(":")[:2])

        datetime_now = datetime.now(tz=timezone)
        datetime_time_input = timezone.localize(
            datetime(
                datetime_now.year, datetime_now.month, datetime_now.day, hours, minutes
            )
        )
        if datetime_now < datetime_time_input:
            next_execution_datetime = datetime_time_input
        else:
            next_execution_datetime = datetime_time_input + timedelta(days=1)
        save_user_notification_preference(
            chat_id=update.effective_user.id,
            notification_type=NotificationType.MORNING_NOTIFICATION,
            notification_time=time_input,
            next_execution_datetime=next_execution_datetime,
            db_session=db_session,
        )

        await update.message.reply_text(
            "Супер! Налаштування завершено!", reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            f"Невірний формат. Введіть час у форматі '08:00' в рамках від 06:00 до 12:00!"
        )
        return IntroConversation.GET_TIME


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Операція зупинена.", reply_markup=main_menu_keyboard()
    )

    return ConversationHandler.END


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
        "Головне меню:", reply_markup=keyboards.main_menu_keyboard()
    )


async def switch_notifications(update, context):
    context.user_data["menu_state"] = "switch_notifications"
    await update.message.reply_text(
        "Натисніть на сповіщення, щоб увімкнути / вимкнути:",
        reply_markup=keyboards.get_notifications_keyboard(update.effective_user.id),
    )


async def handle_notification_toggle(update, context):
    user_input = update.message.text
    db_session = next(get_db())
    notification_time_string = user_input.split(" - ")[0]
    try:
        notification = get_user_notification_by_time(
            chat_id=update.effective_user.id,
            time=notification_time_string,
            db_session=db_session,
        )
    except DataError:
        return

    toggle_user_notification(notification_id=notification.id, db_session=db_session)
    await context.bot.send_message(
        chat_id=update.effective_user.id, text="Налаштування успішно застосовано!"
    )
    await switch_notifications(update, context)


async def notification_time_change_menu(update, context):
    context.user_data["menu_state"] = "change_notification_time"
    await update.message.reply_text(
        "Натисніть на сповіщення, щоб змінити його час спрацювання:",
        reply_markup=keyboards.get_notifications_keyboard(update.effective_user.id),
    )


async def handle_notification_time_change(update, context):
    user_input = update.message.text
    db_session = next(get_db())
    notification_time_string = user_input.split(" - ")[0]
    try:
        notification = get_user_notification_by_time(
            chat_id=update.effective_user.id,
            time=notification_time_string,
            db_session=db_session,
        )
    except DataError:
        return

    if notification:
        context.user_data["notification_to_change"] = notification.id
        await update.message.reply_text(
            "Введіть новий час для цього сповіщення у форматі '08:00'. Час має бути між 06:00 та 12:00."
        )
    else:
        await update.message.reply_text(
            "Сповіщення не знайдено. Спробуйте ще раз або поверніться назад."
        )


async def change_user_notification_time(update, context):
    time_input = update.message.text
    if not is_valid_time(time_input):
        await update.message.reply_text(
            f"Невірний формат. Введіть час у форматі '08:00' в рамках від 06:00 до 12:00!"
        )
        return

    db_session = next(get_db())
    notification_id = context.user_data.get("notification_to_change")
    if notification_id:
        update_user_notification_time(
            notification_id=notification_id,
            new_time=time_input,
            db_session=db_session,
        )
        await update.message.reply_text(
            "Час сповіщення успішно оновлено!",
            reply_markup=keyboards.notification_configuration_keyboard(),
        )
        del context.user_data["notification_to_change"]
    else:
        await update.message.reply_text("Помилка: не вдалось знайти сповіщення.")


async def training_menu(update, context):
    context.user_data["menu_state"] = "training_menu"
    await update.message.reply_text(
        "Час поглянути на тренування!", reply_markup=keyboards.training_menu_keyboard()
    )


async def handle_training_startup(update, context):
    context.user_data["menu_state"] = "training_start"
    await update.message.reply_text(
        "Ура ура! Розпочинаємо тренування!"
        "Почнемо з невеличкого опитування."
        "Як ти себе почуваєш? (Оціни від 1 до 10, де 1 - погано, є симптоми хвороби, 10 - чудово себе почуваєш)",
        reply_markup=keyboards.training_first_question_marks_keyboard(),
    )
    return TrainingStartQuiz.FIRST_QUESTION_ANSWER


async def handle_training_timer_start(update, context):
    user_input = update.message.text
    if user_input not in text_constants.ONE_TO_TEN_MARKS:
        await update.message.reply_text(
            "Як ти себе почуваєш? (Оціни від 1 до 10, де 1 - погано, є симптоми хвороби, 10 - чудово себе почуваєш)",
            reply_markup=keyboards.training_first_question_marks_keyboard(),
        )
        return TrainingStartQuiz.FIRST_QUESTION_ANSWER
    context.user_data["menu_state"] = "training_start_timer_start"
    db_session = next(get_db())

    training_id = start_user_training(
        chat_id=update.effective_chat.id,
        user_state_mark=user_input,
        db_session=db_session,
    )
    if not training_id:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Упс! Щось пішло не так під час старту тренування. Давай спробуємо ще раз)",
        )
        await training_menu(update, context)
    else:
        context.user_data["training_id"] = training_id
        await update.message.reply_text(
            "Го го го!! Успіхів у тренуванні, тренування розпочато!",
            reply_markup=keyboards.training_in_progress_keyboard(),
        )
    return ConversationHandler.END


async def handle_training_stop(update, context):
    if "training_id" not in context.user_data:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Упс! Щось пішло не так під час старту тренування. Давай спробуємо ще раз)",
        )
        await training_menu(update, context)
        return
    context.user_data["menu_state"] = "training_stopped"
    await update.message.reply_text(
        "Супер! Ти справився! Давай оцінимо сьогоднішнє тренування:"
        "Оціни, наскільки важке було тренування?",
        reply_markup=keyboards.training_first_question_marks_keyboard(),
    )
    return TrainingFinishQuiz.FIRST_QUESTION_ANSWER


async def handle_training_second_question(update, context):
    user_input = update.message.text
    if user_input not in text_constants.ONE_TO_TEN_MARKS:
        await update.message.reply_text(
            "Оціни, наскільки важке було тренування? (Оціни від 1 до 10, де 1 - погано, є симптоми хвороби, 10 - чудово себе почуваєш)",
            reply_markup=keyboards.training_first_question_marks_keyboard(),
        )
        return TrainingFinishQuiz.FIRST_QUESTION_ANSWER
    context.user_data["menu_state"] = "training_stopped_second_question"
    context.user_data["training_stop_first_question"] = user_input
    await update.message.reply_text(
        "Оціни, чи відчуваєш ти якийсь дискомфорт/болі?",
        reply_markup=keyboards.training_first_question_marks_keyboard(),
    )
    return TrainingFinishQuiz.SECOND_QUESTION_ANSWER


async def handle_training_finish(update, context):
    logging.info("Inside handle_training_finish")
    user_input = update.message.text
    if user_input not in text_constants.ONE_TO_TEN_MARKS:
        logging.info("Incorrect input")
        context.user_data["menu_state"] = "training_stopped_second_question"
        await update.message.reply_text(
            "Оціни, чи відчуваєш ти якийсь дискомфорт/болі?",
            reply_markup=keyboards.training_first_question_marks_keyboard(),
        )
        return TrainingFinishQuiz.SECOND_QUESTION_ANSWER
    context.user_data["menu_state"] = "training_stopped_finish"
    training_discomfort = user_input
    training_hardness = context.user_data["training_stop_first_question"]
    training_id = context.user_data["training_id"]

    db_session = next(get_db())
    training_duration = stop_training(
        training_id=training_id,
        training_hardness=training_hardness,
        training_discomfort=training_discomfort,
        db_session=db_session,
    )
    await context.bot.send_message(
        text=f"Супер! Ти тренувався аж {str(training_duration).split('.')[0]}! Тепер час відпочити)",
        chat_id=update.effective_chat.id,
    )
    await training_menu(update, context)
    return ConversationHandler.END


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    if not "menu_state" in context.user_data:
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
        await handle_training_startup(update, context)

    # handle anything else

    if context.user_data["menu_state"] == "switch_notifications":
        await handle_notification_toggle(update, context)

    if context.user_data["menu_state"] == "change_notification_time":
        if "notification_to_change" in context.user_data:
            await change_user_notification_time(update, context)
        else:
            await handle_notification_time_change(update, context)

    return


async def send_morning_notification(context, user_id):
    morning_notification_text = "Привіт! Час пройти ранкове опитування! Натисни на команду, щоб почати: /start_morning_quiz"
    await context.bot.send_message(chat_id=user_id, text=morning_notification_text)


# Function to send the scheduled message
async def send_scheduled_message(context: CallbackContext):
    datetime_now = datetime.now(tz=timezone)
    db_session = next(get_db())
    notifications = get_notifications_to_send_by_time(
        current_datetime=datetime_now, db_session=db_session
    )
    for notification in notifications:
        user_id = notification.user.chat_id
        await send_morning_notification(context, user_id)
        last_execution_datetime = datetime_now
        next_execution_datetime = notification.next_execution_datetime + timedelta(
            days=1
        )
        update_user_notification_preference_next_execution(
            last_execution_datetime=last_execution_datetime,
            next_execution_datetime=next_execution_datetime,
            notification_id=notification.id,
            db_session=db_session,
        )


async def start_morning_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_session = next(get_db())
    if is_user_had_morning_quiz_today(chat_id=update.effective_user.id, db_session=db_session):
        await update.message.reply_text(
            text=f"Ви вже проходили ранкове опитування сьогодні!",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        text="Як ви себе почуваєте?",
        reply_markup=keyboards.default_one_to_ten_keyboard(),
    )
    return MorningQuizConversation.FIRST_QUESTION_ANSWER


async def retrieve_morning_feelings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_text = update.message.text
    if not input_text.isnumeric() or not (1 <= int(input_text) <= 10):
        await update.message.reply_text(
            text="Як ви себе почуваєте? Оберіть один із варіантів нижче!",
            reply_markup=keyboards.default_one_to_ten_keyboard(),
        )
        return MorningQuizConversation.FIRST_QUESTION_ANSWER

    context.user_data["morning_feelings"] = input_text

    await update.message.reply_text(
        text="Скільки годин ви поспали? Введіть цифрою!",
    )
    return MorningQuizConversation.SECOND_QUESTION_ANSWER


async def retrieve_morning_sleep_hours(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    input_text = update.message.text

    if not input_text.isnumeric() or int(input_text) > 24 or int(input_text) < 0:
        await update.message.reply_text(
            text="Скільки годин ви поспали? Введіть цифрою! (Від 0 до 24 :) )",
        )
        return MorningQuizConversation.SECOND_QUESTION_ANSWER

    context.user_data["morning_sleep_time"] = input_text
    db_session = next(get_db())

    save_morning_quiz_results(
        user_id=update.effective_user.id,
        quiz_datetime=datetime.now(timezone),
        user_feelings=context.user_data["morning_feelings"],
        user_sleeping_hours=context.user_data["morning_sleep_time"],
        db_session=db_session
    )
    await update.message.reply_text(
        text=f"Дякую! Ваші дані збережено: \n "
             f"Ви поспали: {context.user_data['morning_sleep_time']} \n "
             f"Почуваєте себе на {context.user_data['morning_feelings']}! \n "
             f"Гарного дня!",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    intro_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            IntroConversation.GET_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_name)
            ],
            IntroConversation.GET_TIME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, get_morning_notification_time
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    morning_quiz_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start_morning_quiz", start_morning_quiz)],
        states={
            MorningQuizConversation.FIRST_QUESTION_ANSWER: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, retrieve_morning_feelings
                )
            ],
            MorningQuizConversation.SECOND_QUESTION_ANSWER: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, retrieve_morning_sleep_hours
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    training_start_quiz_conv_handler = ConversationHandler(
        entry_points = [MessageHandler(filters.TEXT & filters.Regex(f"^{text_constants.START_TRAINING}$"), handle_training_startup)],
        states = {
            TrainingStartQuiz.FIRST_QUESTION_ANSWER: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_training_timer_start
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    training_finish_quiz_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex(f"^{text_constants.END_TRAINING}$"),
                                     handle_training_stop)],
        states = {
            TrainingFinishQuiz.FIRST_QUESTION_ANSWER: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_training_second_question
                )
            ],
            TrainingFinishQuiz.SECOND_QUESTION_ANSWER: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_training_finish
                )
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(intro_conv_handler)
    app.add_handler(morning_quiz_conv_handler)
    app.add_handler(training_start_quiz_conv_handler)
    app.add_handler(training_finish_quiz_conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))

    job_queue = app.job_queue

    # Add a job that runs every 30 seconds to send the scheduled message
    job_queue.run_repeating(send_scheduled_message, interval=10, first=0)
    app.run_polling()
