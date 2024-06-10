import json
import random
from typing import List

import geocoder
from comm import ZmqComm
from info_db import InfoDb
from llm import LLM
from vlm import VLM

BROKER_HOST = "10.8.0.5"
BROKER_FRONTEND_PORT = 5555
BROKER_BACKEND_PORT = 5556
ENDPOINT = "中央服务器"

QUESTION_LIST: List[str] = [
    "你住在哪里？",
    "你怎么来的？",
    "你的名字是什么？",
    "你之前来过这里吗？",
    "你今天来访的目的为何？",
]


def main():
    comm = ZmqComm(
        broker_host=BROKER_HOST,
        broker_backend_port=BROKER_BACKEND_PORT,
        broker_frontend_port=BROKER_FRONTEND_PORT,
        endpoint=ENDPOINT,
    )
    comm.connect()

    info = [
        {
            "endpoint": "正门摄像头人脸识别系统",
            "sensorDescription": "本系统用于识别访客的人脸信息，以便进行访客管理",
            "result": "匹配",
        },
        {
            "endpoint": "正门指纹识别系统",
            "sensorDescription": "本系统用于验证访客的身份，以便进行访客管理",
            "result": "缺失",
        },
        {
            "endpoint": "时间系统",
            "sensorDescription": "本系统用于获取当前时间和日期信息",
            "time": "2024-6-10 9:10PM",
            "date": "Monday",
            "holiday": "端午节",
            "weekend": "否",
        },
    ]
    info_db = InfoDb()
    for entry in info:
        info_db.insert(entry)

    ip_info = geocoder.ip("me")
    info_db.insert(
        {
            "endpoint": "定位系统",
            "sensorDescription": "本系统用于获取当前地理位置信息",
            "data": {
                "city": ip_info.city,
                "province": ip_info.state,
                "country": ip_info.country,
            },
        }
    )

    questions = random.sample(QUESTION_LIST, 3)
    answers = [input(f"{question}\n") for question in questions]
    info_db.insert(
        {
            "endpoint": "问答系统",
            "sensorDescription": "用户回答了随机抽取的问题",
            "data": dict(zip(questions, answers)),
        }
    )

    img_path = "img.jpg"
    vlm = VLM()
    vlm_response = vlm.generate(img_path)

    info_db.insert(
        {
            "endpoint": "视觉推理系统",
            "sensorDescription": "本系统用于分析图片中的场景，以便进行安防推理",
            "data": vlm_response,
        }
    )

    llm = LLM()
    llm_response = llm.generate(json.dumps(info_db.get()))

    print(llm_response)


if __name__ == "__main__":
    main()
