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

# Функция добавления ссылок и повторений к упражнениям
def format_exercises(exercises):
    link_map = {
        "Болгарские выпады": "[Болгарские выпады](https://ya.ru)",
        "Жим гантелей лежа под углом вверх": "[Жим гантелей лежа под углом вверх](https://www.youtube.com/watch?v=86HgEDCwgok)"
    }
    formatted_exercises = []
    for ex, reps in exercises.items():
        ex_with_link = link_map.get(ex, ex)
        formatted_exercises.append(f"{ex_with_link} — {reps} повторений")
    return formatted_exercises

# Обработчики сообщений
async def start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(f'Привет, {message.from_user.first_name}!')

    keyboard_markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    btns_text = ('Хоккейную!', 'Беговую!')
    keyboard_markup.row(*(types.KeyboardButton(text) for text in btns_text))

    await message.reply("Какую тренировку показать?", reply_markup=keyboard_markup)

async def hockey_train(message: types.Message):
    """Отправляет сообщение с хоккейной тренировкой"""
    await message.reply(build_workout(), parse_mode="Markdown")

async def running_train(message: types.Message):
    """Отправляет сообщение с беговой тренировкой"""
    await message.reply(build_running(), parse_mode="Markdown")

# Регистрация обработчиков
async def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=['start'])
    dp.register_message_handler(hockey_train, text='Хоккейную!')
    dp.register_message_handler(running_train, text='Беговую!')
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
def build_workout():
    """Формирует тренировку на день"""
    exercises_set = load_json("data/exercise_inventory.json")
    workout_sets = load_json("data/workout_sets.json")

    msg_intro = "Тренировка на сегодня: \n"
    today = today_day()

    special_days = {
        "TUESDAY": "Сегодня лёд в Арене 8:00! 🏒",
        "THURSDAY": "Сегодня лёд в Арене 8:00! 🏒"
    }

    if today in special_days:
        return special_days[today]
    
    today_set = workout_sets.get(today, {})
    exercise_msg = "\n".join([
        f"{k}:\n" + "\n".join(f"  ▪️ {l}" for l in format_exercises(v))
        for k, v in today_set.items()
    ])

    return f"{msg_intro}\n{exercise_msg}"

def build_running():
    """Формирует беговую тренировку на неделю"""
    week_runs = load_json("data/run.json")
    run = week_runs.get("1-я неделя", {})

    return "\n".join([f"{k}:\n{v}\n" for k, v in run.items()])

def today_day():
    """Возвращает сегодняшний день недели в формате строки"""
    return calendar.day_name[datetime.date.today().weekday()].upper()

def dict_intersection(d1, d2):
    """Находит пересечение двух словарей"""
    return {key: d2.get(key, d1[key]) for key in d1.keys() & d2.keys()}
