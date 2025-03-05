import logging
import os
import json
import datetime
import calendar
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния FSM
class TrainingStates(StatesGroup):
    choosing_day_hockey = State()
    choosing_day_running = State()

# Загрузка данных
def load_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки {filename}: {e}")
        return {}

link_map = load_json("data/link_map.json")
workout_sets = load_json("data/workout_sets.json")
run_plan = load_json("data/run.json")

# Клавиатуры
def create_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Хоккейную!"))
    builder.add(KeyboardButton(text="Беговую!"))
    return builder.as_markup(resize_keyboard=True)

def create_day_keyboard():
    days = ["Понедельник", "Вторник", "Среда",
            "Четверг", "Пятница", "Суббота", "Воскресенье"]
    builder = ReplyKeyboardBuilder()
    for day in days:
        builder.add(KeyboardButton(text=day))
    builder.adjust(3)
    return builder.as_markup(resize_keyboard=True)

# Вспомогательные функции
def format_exercises(exercises):
    return [f"{link_map.get(ex, ex)} — {reps}" for ex, reps in exercises.items()]

def translate_day(ru_day):
    days = {
        "Понедельник": "MONDAY",
        "Вторник": "TUESDAY",
        "Среда": "WEDNESDAY",
        "Четверг": "THURSDAY",
        "Пятница": "FRIDAY",
        "Суббота": "SATURDAY",
        "Воскресенье": "SUNDAY"
    }
    return days.get(ru_day, "MONDAY")

def today_day():
    return datetime.datetime.now().strftime("%A").upper()

# Формирование тренировок
def build_workout(selected_day=None):
    selected_day = selected_day or today_day()
    special_days = {
        "TUESDAY": "Сегодня лёд в Арене 8:00! 🏒",
        "THURSDAY": "Сегодня лёд в Арене 8:00! 🏒"
    }

    if selected_day in special_days:
        return special_days[selected_day]

    workout = workout_sets.get(selected_day, {})
    msg = [f"💪 Тренировка на {selected_day}:\n"]
    for category, exercises in workout.items():
        msg.append(f"{category}:")
        msg.extend([f"  ▪️ {ex}" for ex in format_exercises(exercises)])
    return "\n".join(msg)

def build_running(selected_day=None):
    selected_day = selected_day or today_day()
    week_runs = run_plan.get("1-я неделя", {})
    return f"*Бег {selected_day}:*\n{week_runs.get(selected_day, 'Нет данных')}"

# Инициализация бота
dp = Dispatcher()
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))

# Обработчики
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}!",
        reply_markup=create_main_keyboard()
    )

@dp.message(F.text == "Хоккейную!")
async def hockey_selected(message: types.Message, state: FSMContext):
    await state.set_state(TrainingStates.choosing_day_hockey)
    await message.answer("Выберите день:", reply_markup=create_day_keyboard())

@dp.message(F.text == "Беговую!")
async def running_selected(message: types.Message, state: FSMContext):
    await state.set_state(TrainingStates.choosing_day_running)
    await message.answer("Выберите день:", reply_markup=create_day_keyboard())

@dp.message(TrainingStates.choosing_day_hockey)
async def process_hockey_day(message: types.Message, state: FSMContext):
    await state.clear()
    day_en = translate_day(message.text)
    await message.answer(build_workout(day_en), parse_mode="Markdown")

@dp.message(TrainingStates.choosing_day_running)
async def process_running_day(message: types.Message, state: FSMContext):
    await state.clear()
    day_en = translate_day(message.text)
    await message.answer(build_running(day_en), parse_mode="Markdown")

# Обработчик для Yandex Cloud
async def handler(event, context):
    if not os.getenv("TELEGRAM_TOKEN"):
        return {"statusCode": 500, "body": "TELEGRAM_TOKEN not set"}

    try:
        update = types.Update.model_validate(json.loads(event['body']))
        await dp.feed_update(bot, update)
        return {"statusCode": 200}
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}")
        return {"statusCode": 500, "body": str(e)}
