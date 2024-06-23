import base64
import datetime
import hashlib
import json
import os
import threading
import time
from typing import List

import alibabacloud_facebody20191230.models
import holidays
from communication import ZmqComm
from info_db import InfoDb, InfoDbEntry
from llm import LLM
from schemas import ActuatorCommand, ActuatorRegistration, SensorReport
from vlm import VLM

COMM_BROKER_HOST = "10.8.0.5"
COMM_BROKER_BACKEND_PORT = 5556
COMM_BROKER_FRONTEND_PORT = 5555

DEFAULT_INFO: List[InfoDbEntry] = []

info_db = InfoDb()
actuator_db = InfoDb()
comm = ZmqComm(
    broker_host=COMM_BROKER_HOST,
    broker_backend_port=COMM_BROKER_BACKEND_PORT,
    broker_frontend_port=COMM_BROKER_FRONTEND_PORT,
)


def main() -> None:
    comm.connect()
    comm.register_receive_callback("sensor", sensor_comm_callback)
    comm.register_receive_callback("actuator", actuator_registration_callback)

    for entry in DEFAULT_INFO:
        info_db.insert(entry)

    thread_list: List[threading.Thread] = [
        threading.Thread(target=calendar_thread),
        threading.Thread(target=llm_thread),
        threading.Thread(target=vlm_thread),
    ]
    for thread in thread_list:
        thread.start()

def actuator_registration_callback(msg_str: str) -> None:
    msg = json.loads(msg_str)
    if msg["messageId"] != "ActuatorRegistration":
        return

    msg: ActuatorRegistration

    actuator_db.insert({
        "endpoint": msg["endpoint"],
        "description": msg["actuatorDescription"],
        "data": msg["commandFormatDescription"],
    })

def sensor_comm_callback(msg_str: str) -> None:
    msg = json.loads(msg_str)
    if msg["messageId"] != "SensorReport":
        return

    msg: SensorReport

    match msg["sensorType"]:
        case "camera":
            base64_img = str(msg["data"]).encode()
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


def calendar_thread() -> None:
    while True:
        time.sleep(1)

        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        holidays_cn = holidays.country_holidays("CN")
        holiday_name = holidays_cn.get(date_str)
        info_db.insert(
            {
                "endpoint": "calendar",
                "description": "本系统用于获取当前时间和日期信息",
                "data": {
                    "date_time": now.strftime("%Y-%m-%d %I%p %A"),
                    "holiday": holiday_name or "无节日",
                },
            }
        )

def llm_thread() -> None:
    llm = LLM()

    last_info_hash: int = 0

    while True:
        time.sleep(5)

        info = json.dumps(info_db.get(), sort_keys=True)
        info_hash = hash(info)
        if info_hash == last_info_hash:
            print("No new info")
            continue
        last_info_hash = info_hash

        actuator_commands = actuator_db.get()

        llm_response = llm.generate(str(actuator_commands), info, "refresh")

        print(llm_response)

        for actuator_command in llm_response["actuator_commands"]:
            comm.send("actuator", json.dumps(actuator_command))

def vlm_thread() -> None:
    vlm = VLM()

    last_img_sha256: str = ""

    while True:
        time.sleep(5)

        if not os.path.exists("img.jpg"):
            info_db.insert(
                {
                    "endpoint": "vlm",
                    "description": "本系统用于分析图片中的场景，以便进行环境分析",
                    "data": "缺失",
                }
            )
            continue

        img_hash = hash_with_sha256(open("img.jpg", "rb").read())
        if img_hash == last_img_sha256:
            print("No new image")
            continue
        last_img_sha256 = img_hash

        vlm_response = vlm.generate("img.jpg")

        print(vlm_response)

        info_db.insert(
            {
                "endpoint": "vlm",
                "description": "本系统用于分析图片中的场景，以便进行环境分析",
                "data": vlm_response,
            }
        )


def hash_with_sha256(data: bytes):
    sha256 = hashlib.sha256()

    sha256.update(data)

    return sha256.hexdigest()


if __name__ == "__main__":
    main()
