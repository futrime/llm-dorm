import base64
import datetime
import json
import os
import random
import threading
import time
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
        "data": "缺失",
    },
    {
        "endpoint": "fingerprint",
        "description": "本系统用于验证访客的身份，以便进行访客管理",
        "data": "缺失",
    },
]

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

    # questions = random.sample(QUESTION_LIST, 3)
    # answers = [input(f"{question}\n") for question in questions]
    # info_db.insert(
    #     {
    #         "endpoint": "questions",
    #         "description": "用户回答了随机抽取的问题",
    #         "data": dict(zip(questions, answers)),
    #     }
    # )

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

    while True:
        time.sleep(5)

        llm_response = llm.generate(json.dumps(info_db.get()))

        if llm_response["decision"] == "准入":
            gate_command: ActuatorCommand = {
                "endpoint": "gate",
                "messageId": "ActuatorCommand",
                "data": "unlock",
            }

        else:
            gate_command = {
                "endpoint": "gate",
                "messageId": "ActuatorCommand",
                "data": "lock",
            }

        comm.send("actuator", json.dumps(gate_command))

        # TODO: sound


def qa_thread() -> None:
    pass


def vlm_thread() -> None:
    vlm = VLM()

    while True:
        time.sleep(5)

        if not os.path.exists("img.jpg"):
            continue

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
