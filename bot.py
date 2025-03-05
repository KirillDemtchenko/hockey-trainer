import logging
import os
import json
import datetime
import calendar
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.contrib.middlewares.logging import LoggingMiddleware

# Логгер
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# FSM состояния
class TrainingStates(StatesGroup):
    choosing_day_hockey = State()
    choosing_day_running = State()

# Загрузка данных
def load_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Ошибка загрузки {filename}: {e}")
        return {}

link_map = load_json("data/link_map.json")
exercise_inventory = load_json("data/exercise_inventory.json")
workout_sets = load_json("data/workout_sets.json")
run_plan = load_json("data/run.json")

# Клавиатуры
def create_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = ["Хоккейную!", "Беговую!"]
    keyboard.add(*buttons)
    return keyboard

def create_day_keyboard():
    days = ["Понедельник", "Вторник", "Среда",
            "Четверг", "Пятница", "Суббота", "Воскресенье"]
    keyboard = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    keyboard.add(*(types.KeyboardButton(day) for day in days))
    return keyboard

# Вспомогательные функции
def format_exercises(exercises):
    formatted = []
    for ex, reps in exercises.items():
        ex_with_link = link_map.get(ex, ex)
        formatted.append(f"{ex_with_link} — {reps}")
    return formatted

def translate_day(day_ru):
    translation = {
        "Понедельник": "MONDAY",
        "Вторник": "TUESDAY",
        "Среда": "WEDNESDAY",
        "Четверг": "THURSDAY",
        "Пятница": "FRIDAY",
        "Суббота": "SATURDAY",
        "Воскресенье": "SUNDAY"
    }
    return translation.get(day_ru, "MONDAY")

def today_day():
    return calendar.day_name[datetime.date.today().weekday()].upper()

# Формирование тренировок
def build_workout(selected_day=None):
    selected_day = selected_day or today_day()
    msg_intro = f"💪 Тренировка на {selected_day}:\n"

    special_days = {
        "TUESDAY": "Сегодня лёд в Арене 8:00! 🏒",
        "THURSDAY": "Сегодня лёд в Арене 8:00! 🏒"
    }

    if selected_day in special_days:
        return special_days[selected_day]

    today_set = workout_sets.get(selected_day, {})
    exercise_msg = "\n".join([
        f"{k}:\n" + "\n".join(f"  ▪️ {l}" for l in format_exercises(v))
        for k, v in today_set.items()
    ])

    return f"{msg_intro}\n{exercise_msg}"

def build_running(selected_day=None):
    selected_day = selected_day or today_day()
    week_runs = run_plan.get("1-я неделя", {})
    daily_run = week_runs.get(selected_day, "Тренировка не запланирована")
    return f"*Бег {selected_day}:*\n{daily_run}"

# Обработчики
async def start(message: types.Message):
    await message.answer(f'Привет, {message.from_user.first_name}!', reply_markup=create_main_keyboard())

async def hockey_train(message: types.Message, state: FSMContext):
    await TrainingStates.choosing_day_hockey.set()
    await message.reply("Выберите день недели:", reply_markup=create_day_keyboard())

async def running_train(message: types.Message, state: FSMContext):
    await TrainingStates.choosing_day_running.set()
    await message.reply("Выберите день недели:", reply_markup=create_day_keyboard())

async def process_hockey_day(message: types.Message, state: FSMContext):
    await state.finish()
    day_en = translate_day(message.text)
    await message.reply(build_workout(day_en), parse_mode="Markdown")

async def process_running_day(message: types.Message, state: FSMContext):
    await state.finish()
    day_en = translate_day(message.text)
    await message.reply(build_running(day_en), parse_mode="Markdown")

async def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=['start'])
    dp.register_message_handler(hockey_train, text='Хоккейную!', state="*")
    dp.register_message_handler(running_train, text='Беговую!', state="*")
    dp.register_message_handler(process_hockey_day, state=TrainingStates.choosing_day_hockey)
    dp.register_message_handler(process_running_day, state=TrainingStates.choosing_day_running)

async def process_event(event, dp: Dispatcher):
    update = json.loads(event['body'])
    log.debug('Update: %s', update)
    Bot.set_current(dp.bot)
    await dp.process_update(types.Update.to_object(update))

async def handler(event, context):
    if event.get('httpMethod') == 'POST':
        token = os.environ.get('TELEGRAM_TOKEN')
        if not token:
            log.error("TELEGRAM_TOKEN is not set")
            return {'statusCode': 500, 'body': 'Internal Server Error'}

        bot = Bot(token)
        dp = Dispatcher(bot)
        dp.middleware.setup(LoggingMiddleware())

        await register_handlers(dp)
        await process_event(event, dp)

        return {'statusCode': 200, 'body': 'ok'}

    return {'statusCode': 405, 'body': 'Method Not Allowed'}
