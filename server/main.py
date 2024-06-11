import base64
import datetime
import hashlib
import json
import os
import threading
import time
import urllib.parse
from typing import List

import alibabacloud_facebody20191230.client
import alibabacloud_facebody20191230.models
import alibabacloud_tea_openapi.models
import alibabacloud_tea_util.models
import holidays
from comm import ZmqComm
from info_db import InfoDb, InfoDbEntry
from llm import LLM
from schemas import ActuatorCommand, SensorReport
from tts import TTS
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

QUESTION_ORDER_PREFIX_LIST: List[str] = [
    "Hello，欢迎你的到来。在进入之前，还请麻烦您回答几个问题。请问，",
    "好的，请问，",
    "最后一个问题了，请问，",
]

DEFAULT_INFO: List[InfoDbEntry] = []

info_db = InfoDb()
comm = ZmqComm(
    broker_host=COMM_BROKER_HOST,
    broker_backend_port=COMM_BROKER_BACKEND_PORT,
    broker_frontend_port=COMM_BROKER_FRONTEND_PORT,
)


def main() -> None:
    comm.connect()
    comm.register_receive_callback("sensor", sensor_comm_callback)

    for entry in DEFAULT_INFO:
        info_db.insert(entry)

    thread_list: List[threading.Thread] = [
        threading.Thread(target=calendar_thread),
        threading.Thread(target=face_thread),
        threading.Thread(target=llm_thread),
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
                    "date_time": now.strftime("%Y-%m-%d %I:%M%p %A"),
                    "holiday": holiday_name or "无节日",
                },
            }
        )


def face_thread() -> None:
    config = alibabacloud_tea_openapi.models.Config(
        access_key_id=os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID") or "",
        access_key_secret=os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET") or "",
        endpoint="facebody.cn-shanghai.aliyuncs.com",
        region_id="cn-shanghai",
    )
    runtime_options = alibabacloud_tea_util.models.RuntimeOptions()

    while True:
        time.sleep(5)

        if not os.path.exists("img.jpg"):
            info_db.insert(
                {
                    "endpoint": "face",
                    "description": "本系统用于识别访客的人脸信息，以便进行访客管理",
                    "data": "缺失",
                }
            )
            continue

        stream_a = open("img.jpg", "rb")
        stream_b = open("face_ref.jpg", "rb")
        compare_face_request = (
            alibabacloud_facebody20191230.models.CompareFaceAdvanceRequest(
                image_urlaobject=stream_a,
                image_urlbobject=stream_b,
            )
        )

        client = alibabacloud_facebody20191230.client.Client(config)
        try:
            response = client.compare_face_advance(
                compare_face_request, runtime_options
            )
            confidence = response.body.data.confidence
            assert isinstance(confidence, float)

            print(response.body.data)

            if confidence > 61:
                info_db.insert(
                    {
                        "endpoint": "face",
                        "description": "本系统用于识别访客的人脸信息，以便进行访客管理",
                        "data": "匹配",
                    }
                )

            else:
                info_db.insert(
                    {
                        "endpoint": "face",
                        "description": "本系统用于识别访客的人脸信息，以便进行访客管理",
                        "data": "不匹配",
                    }
                )

        except Exception:
            info_db.insert(
                {
                    "endpoint": "face",
                    "description": "本系统用于识别访客的人脸信息，以便进行访客管理",
                    "data": "缺失",
                }
            )


def llm_thread() -> None:
    llm = LLM()
    tts = TTS()

    while True:
        time.sleep(5)

        llm_response = llm.generate(json.dumps(info_db.get()))

        print(llm_response)

        if llm_response["decision"] == "准入":
            gate_command: ActuatorCommand = {
                "endpoint": "gate",
                "messageId": "ActuatorCommand",
                "data": {
                    "command": "unlock",
                },
            }

        else:
            gate_command = {
                "endpoint": "gate",
                "messageId": "ActuatorCommand",
                "data": {
                    "command": "lock",
                },
            }

        comm.send("actuator", json.dumps(gate_command))

        if os.path.exists("llm.mp3"):
            os.remove("llm.mp3")

        tts.generate(llm_response["explanation"], "llm.mp3")

        with open("llm.mp3", "rb") as f:
            sound_data = f.read()

        sound_command: ActuatorCommand = {
            "endpoint": "explanation",
            "messageId": "ActuatorCommand",
            "data": {
                "sound": base64.encodebytes(sound_data).decode(),
            },
        }

        comm.send("actuator", json.dumps(sound_command))


def qa_thread() -> None:
    tts = TTS()

    while True:
        # time.sleep(5)

        # Generate sound files for each question
        for question in QUESTION_LIST:
            for order in range(3):
                order_prefix = QUESTION_ORDER_PREFIX_LIST[order]
                text = order_prefix + question
                file_name = (
                    hash_with_sha256(urllib.parse.quote(text).encode())[:32] + ".mp3"
                )
                if os.path.exists(file_name):
                    continue

                tts.generate(text, file_name)

        # Send questions to user
        for question in QUESTION_LIST:
            for order in range(3):
                order_prefix = QUESTION_ORDER_PREFIX_LIST[order]
                text = order_prefix + question
                file_name = (
                    hash_with_sha256(urllib.parse.quote(text).encode())[:32] + ".mp3"
                )
                with open(file_name, "rb") as f:
                    sound_data = f.read()

                sound_command: ActuatorCommand = {
                    "endpoint": "question",
                    "messageId": "ActuatorCommand",
                    "data": {
                        "order": order,
                        "question": question,
                        "sound": base64.encodebytes(sound_data).decode(),
                    },
                }

                comm.send("actuator", json.dumps(sound_command))


def vlm_thread() -> None:
    vlm = VLM()

    while True:
        time.sleep(5)

        if not os.path.exists("img.jpg"):
            info_db.insert(
                {
                    "endpoint": "vlm",
                    "description": "本系统用于分析图片中的场景，以便进行安防推理",
                    "data": "缺失",
                }
            )
            continue

        vlm_response = vlm.generate("img.jpg")

        print(vlm_response)

        info_db.insert(
            {
                "endpoint": "vlm",
                "description": "本系统用于分析图片中的场景，以便进行安防推理",
                "data": vlm_response,
            }
        )


def hash_with_sha256(data: bytes):
    sha256 = hashlib.sha256()

    sha256.update(data)

    return sha256.hexdigest()


if __name__ == "__main__":
    main()
