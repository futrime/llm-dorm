import json
import os
from typing import List, TypedDict

import dashscope
import dashscope.api_entities

PROMPT = """
你是一个先进的环境照片分析助手。
请你认真观察图片，尽可能详细地描述图片中的场景，尤其关注环境。
你的目的是提供足够的推理依据给智能家居系统，以便系统能够根据你的描述做出合理的决策。

然后，分析图片中环境信息，得出多个陈述，以及提出多个问题。

你的回复必须绝对严格遵循以下给出的JSON格式。

JSON回复格式：

```
{{
    "reasoning": "对当前环境的推理过程，力求详细",
    "description": "对图片内容的详细描述，力求详细",
    "statements": [
        "陈述1",
        "陈述2",
        "陈述3",
        ...
    ],
    "questions": [
        "问题1",
        "问题2",
        "问题3",
        ...
    ]
}}
```

请保证回复能够被Python的json.loads解析。
"""


class VLMResponse(TypedDict):
    reasoning: str
    description: str
    statements: List[str]
    questions: List[str]


class VLM:
    def generate(self, img_path: str) -> VLMResponse:
        abs_path = os.path.abspath(img_path)
        image_url = f"file://{abs_path}"

        messages = [
            {
                "role": "user",
                "content": [
                    {"image": image_url},
                    {"text": PROMPT},
                ],
            },
        ]

        response = dashscope.MultiModalConversation.call(
            model="qwen-vl-plus",
            messages=messages,  # type: ignore
        )

        ans: str = response.output.choices[0].message.content[0]["text"]  # type: ignore

        # Remove everything out of { and }
        ans = ans[ans.find("{") : ans.rfind("}") + 1]

        # Replace all newlines with spaces
        ans = ans.replace("\n", " ")

        result = json.loads(ans)

        return result
