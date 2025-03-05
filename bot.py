import logging
import os
import json
import calendar
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import Dispatcher

# Логгер
log = logging.getLogger(__name__)
log.setLevel(os.environ.get('LOGGING_LEVEL', 'INFO').upper())

# Инициализация бота
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = Bot(TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния
class TrainingState(StatesGroup):
    choosing_training = State()
    choosing_day = State()

# Загрузка JSON

def load_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log.error(f"Ошибка загрузки {filename}: {e}")
        return {}

link_map = load_json("data/link_map.json")
workout_sets = load_json("data/workout_sets.json")
week_runs = load_json("data/run.json")

# Кнопки выбора тренировки
train_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
train_keyboard.row(KeyboardButton("Хоккейную"), KeyboardButton("Беговую"))

# Кнопки выбора дня недели
days_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
days_keyboard.row(*[KeyboardButton(day) for day in calendar.day_name])

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await TrainingState.choosing_training.set()
    await message.answer("Выберите тип тренировки:", reply_markup=train_keyboard)

# Обработчик выбора тренировки
@dp.message_handler(state=TrainingState.choosing_training)
async def choose_training(message: types.Message, state: FSMContext):
    training_type = message.text
    if training_type not in ["Хоккейную", "Беговую"]:
        await message.answer("Пожалуйста, выберите тренировку с кнопки!")
        return

    await state.update_data(training_type=training_type)
    await TrainingState.choosing_day.set()
    await message.answer("Теперь выберите день недели:", reply_markup=days_keyboard)

# Обработчик выбора дня недели
@dp.message_handler(state=TrainingState.choosing_day)
async def choose_day(message: types.Message, state: FSMContext):
    day = message.text.upper()
    if day not in map(str.upper, calendar.day_name):
        await message.answer("Пожалуйста, выберите день с кнопки!")
        return

    user_data = await state.get_data()
    training_type = user_data.get("training_type")

    if training_type == "Хоккейную":
        response = build_workout(day)
    else:
        response = build_running(day)

    await message.answer(response, parse_mode="Markdown")
    await state.finish()

# Функции формирования тренировок
def build_workout(day):
    today_set = workout_sets.get(day.upper(), {})
    exercise_msg = "\n".join(
        [f"{k}:\n" + "\n".join(f"  ▪️ {l}" for l in format_exercises(v)) for k, v in today_set.items()]
    )
    return f"💪 Тренировка на {day}:\n\n{exercise_msg}"

def build_running(day):
    run = week_runs.get("1-я неделя", {}).get(day.upper(), "Нет данных")
    return f"🏃 Беговая тренировка на {day}:\n{run}"

def format_exercises(exercises):
    return [f"{link_map.get(ex, ex)} — {reps}" for ex, reps in exercises.items()]

# Запуск бота
if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
