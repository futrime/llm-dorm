import base64
import json
import random
import threading
import time
from typing import List

import geocoder
from comm import ZmqComm
from info_db import InfoDb, InfoDbEntry
from llm import LLM
from schemas import SensorReport
from vlm import VLM

COMM_BROKER_HOST = "10.8.0.5"
COMM_BROKER_BACKEND_PORT = 5556
COMM_BROKER_FRONTEND_PORT = 5555

QUESTION_LIST: List[str] = [
    "你住在哪里？",
    "你怎么来的？",
    "你的名字是什么？",
    "你之前来过这里吗？",
    "你今天来访的目的为何？",
]

DEFAULT_INFO: List[InfoDbEntry] = [
    {
        "endpoint": "face",
        "description": "本系统用于识别访客的人脸信息，以便进行访客管理",
        "data": "匹配",
    },
    {
        "endpoint": "fingerprint",
        "description": "本系统用于验证访客的身份，以便进行访客管理",
        "data": "缺失",
    },
    {
        "endpoint": "calendar",
        "description": "本系统用于获取当前时间和日期信息",
        "data": {
            "time": "2024-6-10 9:10PM",
            "date": "Monday",
            "holiday": "端午节",
            "weekend": "否",
        },
    },
]

info_db = InfoDb()
sensor_comm = ZmqComm(
    broker_host=COMM_BROKER_HOST,
    broker_backend_port=COMM_BROKER_BACKEND_PORT,
    broker_frontend_port=COMM_BROKER_FRONTEND_PORT,
    channel="sensor",
)


def main() -> None:
    sensor_comm.connect()
    sensor_comm.register_receive_callback(sensor_comm_callback)

    for entry in DEFAULT_INFO:
        info_db.insert(entry)

    questions = random.sample(QUESTION_LIST, 3)
    answers = [input(f"{question}\n") for question in questions]
    info_db.insert(
        {
            "endpoint": "questions",
            "description": "用户回答了随机抽取的问题",
            "data": dict(zip(questions, answers)),
        }
    )

    llm = LLM()
    llm_response = llm.generate(json.dumps(info_db.get()))

    print(llm_response)

    thread_list: List[threading.Thread] = [
        threading.Thread(target=qa_thread),
        threading.Thread(target=vlm_thread),
    ]
    for thread in thread_list:
        thread.start()


def sensor_comm_callback(msg_str: str) -> None:
    msg = json.loads(msg_str)
    if msg["messageId"] != "SensorReport":
        return
    msg: SensorReport

    match msg["sensorType"]:
        case "camera":
            base64_img = bytes(msg["data"])
            with open("img.jpg", "wb") as f:
                f.write(base64.decodebytes(base64_img))

        case _:
            info_db.insert(
                {
                    "endpoint": msg["sensorType"],
                    "description": msg["sensorDescription"],
                    "data": msg["data"],
                }
            )


def llm_thread() -> None:
    llm = LLM()

    while True:
        time.sleep(10)
        llm_response = llm.generate(json.dumps(info_db.get()))
        print(llm_response)


def qa_thread() -> None:
    pass


def vlm_thread() -> None:
    vlm = VLM()

    while True:
        time.sleep(10)

        vlm_response = vlm.generate("img.jpg")
        info_db.insert(
            {
                "endpoint": "vlm",
                "description": "本系统用于分析图片中的场景，以便进行安防推理",
                "data": vlm_response,
            }
        )


if __name__ == "__main__":
    main()
