# ! Buttons
SETTINGS = "🛠 Налаштування"
TRAINING = "🏅 Тренування"
TRAINING_PDF = "🛠 Призначення тренування"
CONFIGURE_NOTIFICATIONS = "🔔 Налаштування сповіщень"
GO_BACK = "◀️ Назад"
CHANGE_NOTIFICATION_TIME = "🕒 Змінити час сповіщень"
TURN_ON_OFF_NOTIFICATIONS = "📢 Увімкнути/Вимкнути"
START_TRAINING = "Розпочати тренування"
END_TRAINING = "Завершити тренування"
CANCEL_TRAINING = "Відмінити тренування"
ONE_TO_TEN_MARKS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
START_MORNING_QUIZ = "Пройти ранкове опитування"
YES_NO_BUTTONS = ["Так", "Ні"]

# * After training converstation
STRESS_LEVEL_USER_MARK = "Оціни свій рівень стресу від 1 до 10 (1 - chill guy, 10 - загубив телефон який у тебе в кармані)"
DO_YOU_HAVE_SORENESS = "Кріпатуру маєщ якусь?"
THANKS_FOR_PASSING_QUIZ = "🙏 Дякую, міністер! \nУ мене поки все, а тобі гарного дня!"

# * Intro conversation
INTRO_CONVERSATION_FIRST_MEET = (
    "Дякую, {name}! Тепер налаштуємо сповіщення. "
    "Введіть бажаний час для ранкового сповіщення. Його потрібно увести в форматі '08:00'. "
    "Введіть будь-який зручний час в рамках від 06:00 до 12:00!"
)
SETTINGS_FINISHED = (
    "Супер! Налаштування завершено! Тепер очікуй від бота сповіщень у вказаний час!"
)
INVALID_TIME_FORMAT = (
    "Невірний формат. Введіть час у форматі '08:00' в рамках від 06:00 до 12:00!"
)

# * Morning quiz conversation
QUIZ_ALREADY_PASSED = "Ви вже проходили ранкове опитування сьогодні!"
HOW_DO_YOU_FEEL = "Від 0 до 10, як ти себе почуваєш?"
HOW_DO_YOU_FEEL_EXPLAINED = "Від 0 до 10, як ти себе почуваєш?"
HOW_MUCH_SLEEP = "Скільки годин поспав?\nПиши в форматі '8:00'"
USER_WEIGHT = "Скільки важиш сьогодні?\nПиши просто цифру"
IS_GOING_TO_TRAIN = "Плануєш піти в зальчик сьогодні?"
WHEN_GOING_TO_TRAIN = "А підскажи, пліз, о котрій?\nПиши так само в форматі '8:00'"
MORNING_QUIZ_FINAL = (
    "Сюда! Все записав: \n "
    "💤 Сон: {hours_amount} \n "
    "😌 Самопочуття: на {feeling_mark}! \n "
    "Вага: {user_weight} кг\n "
    "Тренування сьогодні не планується \n "
    "Так тримати! Гарного тобі дня 🚀"
)

MORNING_QUIZ_FINAL_WITH_TRAINING = (
    "Сюда! Все записав: \n "
    "💤 Сон: {hours_amount} \n "
    "😌 Самопочуття: на {feeling_mark}! \n "
    "Вага: {user_weight} кг\n "
    "Тренування сьогодні о {training_time} \n "
    "Гарного дня!"
)


# * PDF assignment conversation
CHOOSE_USER = "Оберіть користувача для призначення PDF"
UPDATING_PDF = (
    "Оновлюємо PDF для користувача {full_name} - {username}. Надішліть PDF файл сюди."
)
NEW_TRAINING_FILE = "Вам призначено новий файл тренування."
PDF_FILE_ASSIGNED = "PDF успішно призначено користувачу"


# * Training Finish Conversation
TRAINING_START_GONE_WRONG = (
    "Упс! Щось пішло не так під час старту тренування. Давай спробуємо ще раз)"
)
TRAINING_STOPPED = "💪 Ну все, топчик, ти справився!\nДавай оцінимо трешу. Від 1 до 10, наскільки важко було? "
TRAINING_HARDNESS_MARK = "Давай оцінимо трешу. Від 1 до 10, наскільки важко було? "
HAVE_PAINS = "А були якісь болі або дискомфорти?"
USER_HAVE_PAINS = (
    "Користувач {full_name}(@{username}) - {chat_id} відчуває болі після тренування!"
)
TRAINING_FINAL = (
    "Супер! Ти тренувався аж {training_duration}! \n\n"
    "{motivation_message} \n\n"
    "Тепер час відпочити)"
)

# * Training Start Conversation
TRAINING_START = (
    "🔥Уф, банька-парілка починається! \n"
    "Давай перед трешою швидке опитування. \n"
    "🤔Як самопочуття?\nОціни від 1 до 10, де 1 – гівняно, наче тебе переїхала маршрутка, а 10 – пушка, гонка, ракета!"
)
PRE_TRAINING_FEELINGS = "🤔Як самопочуття?\nОціни від 1 до 10, де 1 – гівняно, наче тебе переїхала маршрутка, а 10 – пушка, гонка, ракета!"
TRAINING_PDF_NOT_ASSIGNED = "Ваш файл тренування ще не призначено!"
TRAINING_STARTED = "Тренування почалось, давай, козаче, працюй! Успіхів!"

# * Payment and service
BOT_ACCESS_RESTRICTED_PAYMENT = (
    "Доступ до бота обмежено. Вам потрібно уточнити дані стосовно оплати!"
)
BOT_ACCESS_RESTRICTED_ADMIN = "Доступ до бота обмежено."
MOTIVATION_PREFIX = "Трішки мотивації тобі:"


BOT_DESCRIPTION = "Ласкаво прошу до бота! (Тут має бути якийсь невеличкий опис)"
NAME_REQUEST = "Для початку, введіть своє повне ім'я."
FIRST_GREETING = "Привіт, {username}!"

USER_NOT_FOUND = "Не знайдено вашого користувача в системі!"

# * Menus
SETTING_MENU_TEXT = "Меню налаштувань. Оберіть, що ви бажаєте налаштувати:"
NOTIFICATION_MENU_TEXT = "Конфігурація сповіщень. Оберіть, що бажаєте налаштувати:"
MAIN_MENU_TEXT = "Головне меню:"
CHANGE_NOTIFICATION_TIME_TEXT = (
    "Натисніть на сповіщення, щоб змінити його час спрацювання:"
)
TRAINING_MENU_TEXT = "Такс, шо я там напридумував? "
NOTIFICATION_TOGGLE_TEXT = "Натисніть на сповіщення, щоб увімкнути / вимкнути:"
SETTINGS_FINISHED = "Налаштування успішно застосовано!"
ENTER_NEW_NOTIFICATION_TIME_TEXT = "Введіть новий час для цього сповіщення у форматі '08:00'. Час має бути між 06:00 та 12:00."
NOTIFICATION_NOT_FOUND_TEXT = (
    "Сповіщення не знайдено. Спробуйте ще раз або поверніться назад."
)
WRONG_MORNING_NOTIFICATION_TIME_FORMAT = (
    "Невірний формат. Введіть час у форматі '08:00' в рамках від 06:00 до 12:00!"
)
NOTIFICATION_TIME_UPDATED = "Час сповіщення успішно оновлено!"


# ! General
SOMETHING_GONE_WRONG = "Щось пішло не так. Спробуйте знову"
UNABLE_TO_RECEIVE_USER_DATA = "Unable to retrieve user data. Please, contact developer"

MORNING_NOTIFICATION_TEXT = "🌞 Морген!\nЧас швиденько пройти ранкове опитування!\nНатискай кнопку, і погнілі 👇"
BOT_UNABLE_TO_SEND_MESSAGE = "Бот спробував надіслати користувачу {user_id} повідомлення, але користувач обмежив надсилання повідомлень!"
AFTER_TRAINING_NOTIFICATION_TEXT = (
    "🙋‍♂️Дароу!\nТреба пройти опитування по минулому тренуванню. \nНатискай на кнопку 👇"
)
PASS_QUIZ = "Пройти опитування"
TRAINING_REMINDER_FIRST = "😉 Псс, нагадую тобі про тренування о {notification_time}"
TRAINING_REMINDER_SECOND = "🚀Нумо, погнали! Час починати тренування!"
TRAINING_MORE_THEN_HOUR = "Айм соу сорі. А ти не забув, випадково, завершити тренування? Бо щось уже більше години навалюєш!"

USER_HAVE_PAINS_CLIENT = "Халепа 😰\nНе турбуйся, я вже написав Владу, скоро він відпише тобі і проконсультує як з цим справитись. Все буде добре!"
