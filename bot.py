import logging
import os
import json
import datetime
from aiogram import Bot, Dispatcher, types

# Логгер
log = logging.getLogger(__name__)
log.setLevel(os.environ.get('LOGGING_LEVEL', 'INFO').upper())

# Функция загрузки JSON с обработкой ошибок
def load_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            log.debug(f"Успешно загружен файл: {filename}")
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log.error(f"Ошибка загрузки {filename}: {e}")
        return {}

# Загружаем данные
link_map = load_json("data/link_map.json")
workout_sets = load_json("data/workout_sets.json")
day_info = load_json("data/day_info.json")

# Формируем обратный словарь русских названий
ru_to_code = {}
if day_info:
    ru_to_code = {v["ru"].capitalize(): k for k, v in day_info.items()}
    log.debug(f"Создан словарь ru_to_code: {ru_to_code}")
else:
    log.warning("Файл day_info.json пуст или не загружен")

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

    keyboard = types.ReplyKeyboardMarkup(
        row_width=1,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    keyboard.add(types.KeyboardButton("Тренировка на сегодня"))
    keyboard.add(types.KeyboardButton("Выбор дня"))
    await message.reply("Показать тренировку?", reply_markup=keyboard)

async def hockey_train(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        row_width=3,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    days = [types.KeyboardButton(day) for day in ru_to_code.keys()]
    keyboard.add(*days)
    keyboard.add(types.KeyboardButton("Вернуться в меню"))
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
    keyboard = types.ReplyKeyboardMarkup(
        row_width=1,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    # Исправлен текст кнопки для соответствия обработчику
    keyboard.add(types.KeyboardButton("Вернуться в меню"))

    await message.reply(
        workout,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# === Тренировка на сегодня ===
async def today_workout(message: types.Message):
    week_num = get_week_index() + current_week_offset
    week_data = get_workout_for_week(week_num)
    if not week_data:
        await message.reply("Нет данных для текущей недели.")
        return

    today = datetime.date.today()
    days_ru = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье"
    }
    today_ru = days_ru[today.weekday()]

    for day in week_data.get("days", []):
        if day["day"] == today_ru:
            msg = f"*Тренировка на сегодня ({today_ru}):*\n"
            for ex in day.get("exercises", []):
                msg += f"  ▪️ {ex}\n"
            await message.reply(msg, parse_mode="Markdown")
            return

    await message.reply(f"На сегодня ({today_ru}) тренировки нет 🌿")

# Регистрация обработчиков
async def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=['start'])
    # Теперь обрабатываем оба варианта текста
    dp.register_message_handler(
        hockey_train,
        text=['Получить тренировку!', 'Вернуться в меню']
    )
    dp.register_message_handler(
        handle_day_selection,
        text=list(ru_to_code.keys())
    )
    dp.register_message_handler(show_current_week, commands=['week'])
    dp.register_message_handler(show_next_week, commands=['next'])
    dp.register_message_handler(show_prev_week, commands=['prev'])
    dp.register_message_handler(goto_week, commands=['goto'])
    dp.register_message_handler(today_workout, commands=['today'])
    dp.register_message_handler(today_workout, text=["Тренировка на сегодня"])
    dp.register_message_handler(return_to_menu, text="Вернуться в меню")
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
        "THURSDAY": "В этот день лёд в Арене 7:30! 🏒"
    }

    if day in special_days:
        # Добавлено форматирование Markdown для единообразия
        return f"*{special_days[day]}*"

    today_set = workout_sets.get(day, {})

    if not today_set:
        return f"{msg_intro}На этот день тренировок пока нет 🌿"

    exercise_msg = "\n".join([
        f"*{k}:*\n" + "\n".join(f"  ▪️ {l}" for l in format_exercises(v))
        for k, v in today_set.items()
    ])

    return f"{msg_intro}{exercise_msg}"

def today_day():
    return datetime.date.today().strftime("%A").upper()

def dict_intersection(d1, d2):
    return {key: d2.get(key, d1[key]) for key in d1.keys() & d2.keys()}

# === Работа с неделями и индексом ===
WORKOUTS_DIR = os.path.join("data", "workouts")
INDEX_FILE = os.path.join(WORKOUTS_DIR, "weeks_index.json")
START_DATE = datetime.date(2024, 1, 1)  # Можно вынести в env или конфиг

def get_week_index(today=None):
    if today is None:
        today = datetime.date.today()
    delta = today - START_DATE
    week_num = delta.days // 7  # 0 — первая неделя
    return week_num

def get_weeks_list():
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Ошибка загрузки weeks_index.json: {e}")
        return []

def get_week_filename(week_num):
    weeks = get_weeks_list()
    if not weeks:
        return None
    week_num = week_num % len(weeks)  # Зацикливаем
    return weeks[week_num]

def get_workout_for_week(week_num):
    week_filename = get_week_filename(week_num)
    if not week_filename:
        return None
    filepath = os.path.join(WORKOUTS_DIR, week_filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Ошибка загрузки {filepath}: {e}")
        return None

def format_week_workout(week_num):
    week_data = get_workout_for_week(week_num)
    if not week_data:
        return f"Нет данных для недели {week_num + 1}"
    msg = f"*Тренировки на неделю {week_num + 1}:*\n\n"
    for day in week_data.get("days", []):
        msg += f"*{day['day']}:*\n"
        for ex in day.get("exercises", []):
            msg += f"  ▪️ {ex}\n"
        msg += "\n"
    return msg

# === Команда /week ===
async def show_current_week(message: types.Message):
    week_num = get_week_index()
    msg = format_week_workout(week_num)
    await message.reply(msg, parse_mode="Markdown")

# === Глобальная переменная для смещения недели (только для одного пользователя/serverless) ===
current_week_offset = 0

async def show_next_week(message: types.Message):
    global current_week_offset
    current_week_offset += 1
    week_num = get_week_index() + current_week_offset
    msg = format_week_workout(week_num)
    await message.reply(msg, parse_mode="Markdown")

async def show_prev_week(message: types.Message):
    global current_week_offset
    current_week_offset -= 1
    week_num = get_week_index() + current_week_offset
    msg = format_week_workout(week_num)
    await message.reply(msg, parse_mode="Markdown")

async def goto_week(message: types.Message):
    global current_week_offset
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.reply("Используй: /goto <номер недели>")
            return
        goto_num = int(parts[1]) - 1
        weeks = get_weeks_list()
        await message.reply(f"weeks: {weeks}")  # временно для отладки
        if not (0 <= goto_num < len(weeks)):
            await message.reply(f"Неделя должна быть от 1 до {len(weeks)}")
            return
        # Считаем смещение относительно текущей недели
        current_week_offset = goto_num - get_week_index()
        msg = format_week_workout(goto_num)
        await message.reply(msg, parse_mode="Markdown")
    except Exception as e:
        await message.reply(f"Ошибка: {e}\nИспользуй: /goto <номер недели>")

async def return_to_menu(message: types.Message):
    await start(message)
