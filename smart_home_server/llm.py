import json
from typing import List, TypedDict

import dashscope
import dashscope.api_entities

PROMPT_SYSTEM_TEMPLATE = """
你是一个先进的智能管家系统，负责根据输入的信息和事件综合判断是否需要进行某些动作。

执行机构描述和命令格式信息：

```
{actuators}
```
"""

PROMPT_USER_TEMPLATE = """
边缘传感系统当前信息：

```
{sensors}
```

事件：

```
{event}
```

你需要首先综合所有信息分析当前状况，然后决定是否进行执行器命令。
你的回复必须绝对严格遵循以下给出的JSON格式。
JSON回复格式：

```json
{{
    "reasoning": "对当前情况的谨慎逐步推理过程，力求详细",
    "actuator_commands": [
        {{
            "endpoint": "执行机构的端点",
            "data": "执行机构的命令，请参照命令格式描述",
        }}
    ]
}}
```

请保证回复能够被Python的json.loads解析。
"""


class ActuatorCommand(TypedDict):
    endpoint: str
    data: str


class LLMResponse(TypedDict):
    reasoning: str
    actuator_commands: List[ActuatorCommand]


class LLM:
    def generate(self, actuators: str, sensors: str, event: str) -> LLMResponse:
        messages = [
            {
                "role": "system",
                "content": PROMPT_SYSTEM_TEMPLATE.format(actuators=actuators),
            },
            {
                "role": "user",
                "content": PROMPT_USER_TEMPLATE.format(sensors=sensors, event=event),
            },
        ]

        response = dashscope.Generation.call(
            model="qwen-max",
            messages=messages,  # type: ignore
        )

        ans: str = response.output.text  # type: ignore

        # Remove everything out of { and }
        ans = ans[ans.find("{") : ans.rfind("}") + 1]

        # Replace all newlines with spaces
        ans = ans.replace("\n", " ")

        result = json.loads(ans)

        return result
