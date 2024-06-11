import base64
import hashlib
import json
import os
import random
from typing import List, TypedDict
import playsound
from schemas import SensorReport

from comm import ZmqComm
from schemas import ActuatorCommand

COMM_BROKER_HOST = "home.server.futrime.com"
COMM_BROKER_BACKEND_PORT = 5556
COMM_BROKER_FRONTEND_PORT = 5555

QUESTION_LIST: List[str] = [
    "你住在哪里？",
    "你怎么来的？",
    "你的名字是什么？",
    "你之前来过这里吗？",
    "你今天来访的目的为何？",
]

QUESTION_ORDER_PREFIX_LIST: List[str] = [
    "Hello，欢迎你的到来。在进入之前，还请麻烦您回答几个问题。请问，",
    "好的，请问，",
    "最后一个问题了，请问，",
]

comm = ZmqComm(
    broker_host=COMM_BROKER_HOST,
    broker_backend_port=COMM_BROKER_BACKEND_PORT,
    broker_frontend_port=COMM_BROKER_FRONTEND_PORT,
)

class Explanation(TypedDict):
    sound: str

class Question(TypedDict):
    order: int
    question: str
    sound: str

asking_question = False

def main() -> None:
    global asking_question

    comm.connect()
    comm.register_receive_callback("actuator", actuator_comm_callback)

    while True:
        input("Enter to start asking question")

        asking_question = True

        qa_dict = {}
        questions = random.sample(QUESTION_LIST, k = 3)

        for order in range(3):
            question = questions[order]

            file_name = hash_with_sha256(
                (QUESTION_ORDER_PREFIX_LIST[order] + question).encode("utf-8")
            ) + ".mp3"

            playsound.playsound(file_name)

            ans = input()

            qa_dict[question] = ans

        message: SensorReport = {
            "endpoint": "question_answer",
            "messageId": "SensorReport",
            "sensorType": "question_answer",
            "sensorDescription": "询问访客一些问题，获取答案，用于判断是否允许访问",
            "data": qa_dict,
        }

        comm.send("sensor", json.dumps(message))

        asking_question = False


def actuator_comm_callback(msg_str: str) -> None:
    global asking_question

    msg = json.loads(msg_str)
    if msg["messageId"] != "ActuatorCommand":
        return

    if msg["endpoint"] != "question" and msg["endpoint"] != "explanation":
        return

    if msg["endpoint"] == "explanation":
        data_explanation: Explanation = msg["data"]
        sound = data_explanation["sound"].encode("utf-8")
        with open("sound.mp3", "wb") as f:
            f.write(base64.decodebytes(sound))

        if asking_question:
            return

        playsound.playsound("sound.mp3")

        return

    if msg["endpoint"] == "question":
        data_question: Question = msg["data"]
        order = data_question["order"]
        question = data_question["question"]
        sound = data_question["sound"].encode("utf-8")

        file_name = hash_with_sha256(
            (QUESTION_ORDER_PREFIX_LIST[order] + question).encode("utf-8")
        ) + ".mp3"

        if os.path.exists(file_name):
            return

        with open(file_name, "wb") as f:
            f.write(base64.decodebytes(sound))

        return

def hash_with_sha256(data: bytes):
    sha256 = hashlib.sha256()

    sha256.update(data)

    return sha256.hexdigest()

if __name__ == "__main__":
    main()
