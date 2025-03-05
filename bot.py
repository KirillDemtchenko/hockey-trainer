import logging
import os
import json
import datetime
import calendar

from aiogram import Bot, Dispatcher, types

# Логгер
log = logging.getLogger(__name__)
log.setLevel(os.environ.get('LOGGING_LEVEL', 'INFO').upper())

# Функция загрузки JSON с обработкой ошибок
def load_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log.error(f"Ошибка загрузки {filename}: {e}")
        return {}

# Загружаем данные
link_map = load_json("data/link_map.json")
workout_sets = load_json("data/workout_sets.json")

# Словарь с информацией о днях недели
day_info = {
    "MONDAY": {"ru": "понедельник", "eng": "Monday"},
    "TUESDAY": {"ru": "вторник", "eng": "Tuesday"},
    "WEDNESDAY": {"ru": "среду", "eng": "Wednesday"},
    "THURSDAY": {"ru": "четверг", "eng": "Thursday"},
    "FRIDAY": {"ru": "пятницу", "eng": "Friday"},
    "SATURDAY": {"ru": "субботу", "eng": "Saturday"},
    "SUNDAY": {"ru": "воскресенье", "eng": "Sunday"}
}

# Обратный словарь для преобразования русских названий в коды
ru_to_code = {v["ru"].capitalize(): k for k, v in day_info.items()}

# Функция добавления ссылок и повторений к упражнениям
def format_exercises(exercises):
    formatted = []
    for ex, reps in exercises.items():
        if ex not in link_map:
            log.warning(f"Ссылка для упражнения '{ex}' не найдена")
        formatted.append(f"{link_map.get(ex, ex)} — {reps}")
    return formatted

# Обработчики сообщений
async def start(message: types.Message):
    await message.answer(f'Привет, {message.from_user.first_name}!')

    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Получить тренировку!"))
    await message.reply("Какую тренировку показать?", reply_markup=keyboard)

async def hockey_train(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=True)
    days = [types.KeyboardButton(day) for day in ru_to_code.keys()]
    keyboard.add(*days)
    await message.reply("Выберите день недели:", reply_markup=keyboard)

async def handle_day_selection(message: types.Message):
    selected_day_ru = message.text.capitalize()
    selected_day_code = ru_to_code.get(selected_day_ru)

    if not selected_day_code:
        await message.reply(
            "Неизвестный день недели. Попробуйте снова.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    workout = build_workout(selected_day_code)

    # Клавиатура с возвратом
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Вернуться в меню"))

    await message.reply(
        workout,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# Регистрация обработчиков
async def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=['start'])
    dp.register_message_handler(hockey_train, text=['Получить тренировку!', 'Вернуться в меню'])
    dp.register_message_handler(handle_day_selection, text=list(ru_to_code.keys()))
    log.debug('Handlers зарегистрированы')

async def process_event(event, dp: Dispatcher):
    update = json.loads(event['body'])
    log.debug('Update: %s', update)
    Bot.set_current(dp.bot)
    await dp.process_update(types.Update.to_object(update))

async def handler(event, context):
    if event.get('httpMethod') == 'POST':
        token = os.environ.get('TELEGRAM_TOKEN')
        if not token:
            log.error("TELEGRAM_TOKEN не установлен")
            return {'statusCode': 500, 'body': 'Internal Server Error'}

        bot = Bot(token)
        dp = Dispatcher(bot)
        await register_handlers(dp)
        await process_event(event, dp)
        return {'statusCode': 200, 'body': 'ok'}

    return {'statusCode': 405, 'body': 'Method Not Allowed'}

# Функции формирования тренировок
def build_workout(day=None):
    if day is None:
        day = today_day()

    day_data = day_info.get(day, {})
    msg_intro = f"💪 *Тренировка на {day_data.get('ru', day.lower())}:*\n\n"

    special_days = {
        "TUESDAY": "В этот день лёд в Арене 7:30! 🏒",
        "FRIDAY": "В этот день лёд в Арене 7:30! 🏒"
    }

    if day in special_days:
        return special_days[day]

    today_set = workout_sets.get(day, {})

    if not today_set:
        return f"{msg_intro}На этот день тренировок пока нет 🙅♂️"

    exercise_msg = "\n".join([
        f"*{k}:*\n" + "\n".join(f"  ▪️ {l}" for l in format_exercises(v))
        for k, v in today_set.items()
    ])

    return f"{msg_intro}{exercise_msg}"

def today_day():
    return datetime.date.today().strftime("%A").upper()

def dict_intersection(d1, d2):
    return {key: d2.get(key, d1[key]) for key in d1.keys() & d2.keys()}
