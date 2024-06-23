import json
import os

import aliyunsdkcore.client
import aliyunsdkcore.request
import requests


class TTS:
    def __init__(self):
        self.client = aliyunsdkcore.client.AcsClient(
            os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
            os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
            "cn-shanghai",
        )

    def generate(self, text: str, output_path: str) -> None:
        request = aliyunsdkcore.request.CommonRequest()
        request.set_method("POST")
        request.set_domain("nls-meta.cn-shanghai.aliyuncs.com")
        request.set_version("2019-02-28")
        request.set_action_name("CreateToken")

        response = self.client.do_action_with_exception(request)
        assert isinstance(response, bytes)
        jss = json.loads(response.decode())
        token = jss["Token"]["Id"]

        response = requests.post(
            "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/tts",
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {
                    "appkey": os.getenv("NLS_APP_KEY"),
                    "text": text,
                    "token": token,
                    "format": "mp3",
                }
            ),
        )

        with open(output_path, "wb") as f:
            f.write(response.content)
