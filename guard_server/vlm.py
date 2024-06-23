import json
import os
from typing import List, TypedDict

import dashscope
import dashscope.api_entities

PROMPT = """
你是一个先进的访客管理和家庭安防系统助手。
请你认真观察图片，尽可能详细地描述图片中的场景，尤其关注环境和人物。

然后，分析图片中与安防相关的特征，进行详细的一步一步推理，最后以陈述句形式输出图片中访客（如果有）身上可能威胁安全的信息，并提出需要关注的问题。

你的回复必须绝对严格遵循以下给出的JSON格式。

JSON回复格式：

```
{{
    "reasoning": "对当前情况的谨慎逐步推理过程，力求详细",
    "description": "对图片内容的详细描述，包括环境和人物",
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
