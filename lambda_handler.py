import json
import random
import re
import datetime
import boto3
import yandexcloud
from flask import Flask, request, session
from yandex.cloud.resourcemanager.v1.cloud_service_pb2 import ListCloudsRequest
from yandex.cloud.resourcemanager.v1.cloud_service_pb2_grpc import CloudServiceStub

SECRET_KEY = 'a secret key'
app = Flask(__name__)
app.config.from_object(__name__)

def write_workout_to_dynamo(user_name, workout_obj):
    """
    Writes the workout object to the DynamoDB workout log.
    :param phone_num: Phone number to use as the partition key.
    :param workout_obj: Workout object to be written.
    :return:
    """
    dynamo = boto3.resource("dynamodb")

    tbl = dynamo.Table("hockey-trainer-log")

    tbl.put_item(
        Item={
            'workout_user': str(user_name),
            'exercise_time': str(datetime.datetime.now()),
            'workout': workout_obj
        }
    )

def build_workout():
    """
    Builds the workout for the day.
    :return: A workout dictionary with the workout details and a string representation of the workout.
    """
    with open("exercise_inventory.json", "r") as f:
        exercises = json.load(f)
        f.close()

    msg_intro = "Привет! Твоя тренировка на сегодня: \n"

# Берем тренировки в зависимости от дня недели
# Учитываем была ли выполнена предыдущая тренировка
# Важен алгорит выбора подходящих к друг другу упражнений
# Тренировки в хоккей сезон и межсезонье могут отличаться

#    if datetime.weekday() == 0: # where 0 - monday
#        Ice day
#    elif datetime.weekday() == 1:
#        Сила верх(2) + "10х3", Мощность(2) + "10x3", Скорость(2) + "20-30сек", Ловкость(2) + "20-30сек", Мобильность(8)
#    elif datetime.weekday() == 2:
#        Ice day
#    elif datetime.weekday() == 3:
#    elif datetime.weekday() == 4:
#    elif datetime.weekday() == 5:
#    elif datetime.weekday() == 6:

    workout = {k: random.choice(v) for k, v in exercises.items()}
    exercise_msg = "\n".join([k + ": " + v for k, v in workout.items()])
    workout_msg = "\n".join([msg_intro, exercise_msg])

    return workout, workout_msg

@app.route("/", methods=["POST"])
def main():
    # Set message to lowercase and remove punctuation.
    msg = re.sub(r'[^\w\s]', '', request.values.get("Body").lower())

    # Check if there is an ongoing conversation or not.
    context = session.get("context", "hello")

    # If this is the first entry test for the wake phrase.
    if context == "hello":
        if msg == "whats todays workout":
            # Build workout here.
            workout_obj, workout_msg = build_workout()
            session["context"] = "build_workout"
            session["response"] = workout_msg
            session["workout_obj"] = workout_obj
        else:
            session["response"] = "I don't understand what you're asking."

    # Acknowledge the workout.
    elif context == "build_workout":
        if msg == "lets get after it":
            session["response"] = "GOOD."
            session["cleanup"] = True

            # Log the workout in the log.
            write_workout_to_dynamo(“tutorial”, session["workout_obj"])
        elif msg == "lets do something else":
            # Build workout here.
            workout_obj, workout_msg = build_workout()
            session["response"] = workout_msg
            session["workout_obj"] = workout_obj
        else:
            session["response"] = "I don't understand..."

    # Cleanup the session.
    if session.get("cleanup", False):
        session.pop("context")
        session.pop("cleanup")

    resp = MessagingResponse()
    resp.message(session.get("response"))

    return str(resp)


if __name__ == "__main__":
    app.run(debug=True)

