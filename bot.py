import logging
import os
import json
import calendar
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Логгер
log = logging.getLogger(__name__)
log.setLevel(os.environ.get('LOGGING_LEVEL', 'INFO').upper())

# Инициализация бота
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = Bot(TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

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
train_keyboard = ReplyKeyboardBuilder()
train_keyboard.button(text="Хоккейную")
train_keyboard.button(text="Беговую")
train_keyboard.adjust(2)

# Кнопки выбора дня недели
days_keyboard = ReplyKeyboardBuilder()
for day in calendar.day_name:
    days_keyboard.button(text=day)
days_keyboard.adjust(3)

# Обработчик команды /start
@dp.message(F.text == "/start")
async def start(message: types.Message, state: FSMContext):
    await state.set_state(TrainingState.choosing_training)
    await message.answer("Выберите тип тренировки:", reply_markup=train_keyboard.as_markup(resize_keyboard=True))

# Обработчик выбора тренировки
@dp.message(TrainingState.choosing_training, F.text.in_(["Хоккейную", "Беговую"]))
async def choose_training(message: types.Message, state: FSMContext):
    await state.update_data(training_type=message.text)
    await state.set_state(TrainingState.choosing_day)
    await message.answer("Теперь выберите день недели:", reply_markup=days_keyboard.as_markup(resize_keyboard=True))

# Обработчик выбора дня недели
@dp.message(TrainingState.choosing_day, F.text.in_(calendar.day_name))
async def choose_day(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    training_type = user_data.get("training_type")

    response = build_workout(message.text) if training_type == "Хоккейную" else build_running(message.text)

    await message.answer(response, parse_mode="Markdown")
    await state.clear()

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
