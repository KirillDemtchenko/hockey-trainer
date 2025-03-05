import logging
import os
import json
import datetime
import calendar

from aiogram import Bot, Dispatcher, types

# Логгер
log = logging.getLogger(__name__)
log.setLevel(os.environ.get('LOGGING_LEVEL', 'INFO').upper())

# Функция загрузки JSON
def load_json(filename):
    """Загружает JSON-файл и возвращает его содержимое."""
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

# Загружаем link_map из JSON-файла
link_map = load_json("data/link_map.json")

# Словари для преобразования дней недели
day_mapping = {
    "Понедельник": "MONDAY",
    "Вторник": "TUESDAY",
    "Среда": "WEDNESDAY",
    "Четверг": "THURSDAY",
    "Пятница": "FRIDAY",
    "Суббота": "SATURDAY",
    "Воскресенье": "SUNDAY"
}

day_ru = {
    "MONDAY": "понедельник",
    "TUESDAY": "вторник",
    "WEDNESDAY": "среду",
    "THURSDAY": "четверг",
    "FRIDAY": "пятницу",
    "SATURDAY": "субботу",
    "SUNDAY": "воскресенье"
}

# Функция добавления ссылок и повторений к упражнениям
def format_exercises(exercises):
    formatted_exercises = []
    for ex, reps in exercises.items():
        ex_with_link = link_map.get(ex, ex)  # Получаем ссылку, если есть
        formatted_exercises.append(f"{ex_with_link} — {reps}")
    return formatted_exercises

# Обработчики сообщений
async def start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(f'Привет, {message.from_user.first_name}!')

    keyboard_markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    btns_text = ('Получить тренировку!',)
    keyboard_markup.row(*(types.KeyboardButton(text) for text in btns_text))

    await message.reply("Какую тренировку показать?", reply_markup=keyboard_markup)

async def hockey_train(message: types.Message):
    """Отправляет сообщение с выбором дня для хоккейной тренировки"""
    keyboard_markup = types.ReplyKeyboardMarkup(
        row_width=3, 
        resize_keyboard=True, 
        one_time_keyboard=True  # Клавиатура скроется после выбора
    )
    days_ru = list(day_mapping.keys())
    buttons = [types.KeyboardButton(day) for day in days_ru]
    keyboard_markup.add(*buttons)
    await message.reply("Выберите день недели:", reply_markup=keyboard_markup)

async def handle_day_selection(message: types.Message):
    """Обрабатывает выбор дня недели для тренировки"""
    selected_day_ru = message.text
    selected_day_en = day_mapping.get(selected_day_ru)
    
    if not selected_day_en:
        await message.reply(
            "Неизвестный день недели. Попробуйте снова.",
            reply_markup=types.ReplyKeyboardRemove(),
            disable_web_page_preview=True
        )
        return
    
    workout = build_workout(selected_day_en)
    await message.reply(
        workout, 
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove(),
        disable_web_page_preview=True
    )

# Регистрация обработчиков
async def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=['start'])
    dp.register_message_handler(hockey_train, text='Получить тренировку!')
    dp.register_message_handler(handle_day_selection, text=list(day_mapping.keys()))
    log.debug('Handlers are registered.')

async def process_event(event, dp: Dispatcher):
    """Обрабатывает событие из Yandex.Cloud"""
    update = json.loads(event['body'])
    log.debug('Update: %s', update)

    Bot.set_current(dp.bot)
    await dp.process_update(types.Update.to_object(update))

async def handler(event, context):
    """Обработчик событий Yandex.Cloud"""
    if event.get('httpMethod') == 'POST':
        token = os.environ.get('TELEGRAM_TOKEN')
        if not token:
            log.error("TELEGRAM_TOKEN is not set")
            return {'statusCode': 500, 'body': 'Internal Server Error'}

        bot = Bot(token)
        dp = Dispatcher(bot)

        await register_handlers(dp)
        await process_event(event, dp)

        return {'statusCode': 200, 'body': 'ok'}

    return {'statusCode': 405, 'body': 'Method Not Allowed'}

# Функции формирования тренировок
def build_workout(day=None):
    """Формирует тренировку на день"""
    if day is None:
        day = today_day()
    exercises_set = load_json("data/exercise_inventory.json")
    workout_sets = load_json("data/workout_sets.json")

    msg_intro = f"💪 Тренировка на {day_ru.get(day, day.lower())}: \n"

    special_days = {
        "TUESDAY": "В этот день лёд в Арене 8:00! 🏒",
        "THURSDAY": "В этот день лёд в Арене 8:00! 🏒"
    }

    if day in special_days:
        return special_days[day]

    today_set = workout_sets.get(day, {})
    exercise_msg = "\n".join([
        f"{k}:\n" + "\n".join(f"  ▪️ {l}" for l in format_exercises(v))
        for k, v in today_set.items()
    ])

    return f"{msg_intro}\n{exercise_msg}"

def today_day():
    """Возвращает сегодняшний день недели в формате строки"""
    return calendar.day_name[datetime.date.today().weekday()].upper()

def dict_intersection(d1, d2):
    """Находит пересечение двух словарей"""
    return {key: d2.get(key, d1[key]) for key in d1.keys() & d2.keys()}