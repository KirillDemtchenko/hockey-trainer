import logging
import os
import json
import random
import datetime

from aiogram import Bot, Dispatcher, types

# Logger initialization and logging level setting
log = logging.getLogger(__name__)
log.setLevel(os.environ.get('LOGGING_LEVEL', 'INFO').upper())


# Handlers
async def start(message: types.Message):
    await message.answer('Привет, {}!'.format(message.from_user.first_name))

    keyboard_markup = types.ReplyKeyboardMarkup(row_width=3)

    btns_text = ('Хоккейную!', 'Беговую!')
    keyboard_markup.row(*(types.KeyboardButton(text) for text in btns_text))

    await message.reply("Какую тренировку показать?", reply_markup=keyboard_markup)


async def hockey_train(message: types.Message):
    workout_msg = build_workout()
    await message.reply(workout_msg)


async def running_train(message: types.Message):
    running_msg = build_running()
    await message.reply(running_msg)


#    keyboard_markup = types.InlineKeyboardMarkup(row_width=3)

#    text_and_data = (
#        ('1-ю!', 'first'),
#        ('2-ю!', 'second'),
#    )
# in real life for the callback_data the callback data factory should be used
# here the raw string is used for the simplicity
#    row_btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in text_and_data)

#    keyboard_markup.row(*row_btns)

#    await message.reply("Какую неделю из 12 недельного плана подготовки вывести?", reply_markup=keyboard_markup)

# Functions for Yandex.Cloud
async def register_handlers(dp: Dispatcher):
    """Registration all handlers before processing update."""

    dp.register_message_handler(start, commands=['start'])
    dp.register_message_handler(hockey_train, text='Хоккейную!')
    dp.register_message_handler(running_train, text='Беговую!')

    log.debug('Handlers are registered.')


async def process_event(event, dp: Dispatcher):
    """
    Converting an Yandex.Cloud functions event to an update and
    handling tha update.
    """

    update = json.loads(event['body'])
    log.debug('Update: ' + str(update))

    Bot.set_current(dp.bot)
    update = types.Update.to_object(update)
    await dp.process_update(update)


async def handler(event, context):
    """Yandex.Cloud functions handler."""

    if event['httpMethod'] == 'POST':
        # Bot and dispatcher initialization
        bot = Bot(os.environ.get('TELEGRAM_TOKEN'))
        dp = Dispatcher(bot)

        await register_handlers(dp)
        await process_event(event, dp)

        return {'statusCode': 200, 'body': 'ok'}
    return {'statusCode': 405}


# Hockey functions
def build_workout():
    """
    Builds the workout for the day.
    :return: A string representation of the workout.
    """
    """
    TO DO:
    Change exercises for format{"value": "Разминка в стиле мистера Бина", "link": "https://ya.ru", "set": "10x3"},
    """

    with open("data/exercise_inventory.json", "r") as f:
        exercises_set = json.load(f)
        f.close()

    with open("data/days_sets.json", "r") as f:
        sets = json.load(f)
        f.close()


    msg_intro = "Тренировка на сегодня: \n"

    if today_day() in {"MONDAY", "WEDNESDAY"}:
        workout_msg = "Сегодня лёд в Ак Буре 20:45! 🏒"
    elif today_day() in {"SATURDAY"}:
        workout_msg = "Сегодня лёд в Форварде в 20:30! 🏒"
    elif today_day() in {"SUNDAY"}:
        workout_msg = "Сегодня отдых"
    else:
        today_set = sets[today_day()]
        workout_dict = dict_intersection(today_set, exercises_set)
        workout = {k: random.choice(v) for k, v in workout_dict.items()}

        exercise_msg = "\n".join([k + ":\n" + v + "\n" for k, v in workout.items()])
        workout_msg = "\n".join([msg_intro, exercise_msg])

    return workout_msg


def today_day():
    """Return today in text format"""
    weekdays = {1: "MONDAY",
                2: "TUESDAY",
                3: "WEDNESDAY",
                4: "THURSDAY",
                5: "FRIDAY",
                6: "SATURDAY",
                7: "SUNDAY"}
    return weekdays[datetime.date.today().isoweekday()]


def dict_intersection(d1, d2):
    """Math intersection for Python dictionary"""
    return dict((key, d2[key] or d1[key]) for key in set(d1) & set(d2))


# Running functions
def build_running():
    """
    Builds the workout for the week.
    :return: A string representation of the workout.
    """
    with open("data/run.json", "r") as f:
        week_runs = json.load(f)
        f.close()

        run = week_runs["1-я неделя"]

        run_msg = "\n".join([k + ":\n" + v + "\n" for k, v in run.items()])

    return run_msg
