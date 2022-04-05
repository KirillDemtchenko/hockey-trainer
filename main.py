import json
import random
import re
import telebot
from telebot import TeleBot
from telebot import types
import os
import datetime


def handler(event, context):
# todo: сделать возможость смотреть тренировку на завтра

    bot = TeleBot(os.getenv('TELEGRAM_TOKEN'))

    chat_id, sender, text = message_check_in(event)

    if text.lower().strip() == "/start" or text.lower().strip == "/help":
        welcome_msg = "Что бы получить тренировку отправьте команду /train"
        bot.send_message(chat_id, welcome_msg)

    elif text.lower().strip() == "/train":
        workout_msg = build_workout()
        bot.send_message(chat_id, workout_msg)
    else:
        pass

def message_check_in(event):

    # Extract the message key over payload's body
    # message = json.loads(event['body']['message'])
    body = json.loads(event['body'])
    # Split between three variables bellow
    chat_id = body['message']['chat']['id'] # Chat ID will guide your chatbot reply
    sender = body['message']['from']['first_name'] # Sender's first name, registered by user's telegram app
    text = body['message']['text'] # The message content

    return chat_id, sender, text

def build_workout():
    """
    Builds the workout for the day.
    :return: A string representation of the workout.
    """
    with open("exercise_inventory.json", "r") as f:
        exercises = json.load(f)
        f.close()

    with open("days_sets.json", "r") as f:
        sets = json.load(f)
        f.close()

    msg_intro = "👋 Тренировка на сегодня: \n"


#    today_set = sets[0]["MONDAY"]

#    println(today_set)

    if today_day() in {"MONDAY", "WEDNESDAY", "SATURDAY"}:
        workout_msg = "Сегодня на лёд! 🏒"
    else:
        workout = {k: random.choice(v) for k, v in exercises.items()}

        exercise_msg = "\n".join([k + ":\n" + v + "\n" for k, v in workout.items()])
        workout_msg = "\n".join([msg_intro, exercise_msg])

    return workout_msg

def today_day():
    weekdays = {1: "MONDAY",
                2: "TUESDAY",
                3: "WEDNESDAY",
                4: "THURSDAY",
                5: "FRIDAY",
                6: "SATURDAY",
                7: "SUNDAY"}

    return weekdays[datetime.date.today().isoweekday()]
