import json
from typing import TypedDict

import dashscope
import dashscope.api_entities

PROMPT_SYSTEM_TEMPLATE = """
你是一个先进的访客管理系统助手，负责根据输入的信息综合判断是否允许访客进入。你的决策需综合考虑以下因素：

1. **人脸识别结果**：匹配表示已注册并授权的访客，不匹配表示未注册或非授权人员，缺失表示无法获取人脸数据。
2. **指纹识别结果**：匹配表示验证通过，不匹配表示验证未通过，缺失表示未使用指纹识别功能。
3. **地理位置安全级别**：结合城市和国家的治安情况，评估当前地点的安全风险。
4. **时间与日期信息**：考虑24小时制的时间段安全性，以及是否为节假日、周末或工作日，以调整安全策略。
5. **门口照片**：用于环境安全检查，确认无安全隐患。
6. **访客发言录音**：分析内容，判断是否有威胁性言辞或异常行为指示。

基于上述信息，你需要输出：

- **准入许可**：明确给出“准入”或“禁止”的决定。如果不能确定，请选择“禁止”。
- 所有决策必须有一步一步的推理过程，不得出现无法解释的决策。
- 礼貌而又热情地向访客解释决策的理由。

记住，保护隐私是首要原则，不得要求提供与安全无关的个人信息。你可以访问互联网搜索所需信息。
"""

PROMPT_USER_TEMPLATE = """
现在边缘传感系统反馈了以下信息：

```
{info}
```

你需要首先综合所有信息分析当前状况，并基于谨慎和倾向于禁止的原则进行推理。然后给出准入 / 禁止 的决策，并向访客解释决策的理由。
你的回复必须绝对严格遵循以下给出的JSON格式。
JSON回复格式：

```json
{{
    "reasoning": "对当前情况的谨慎逐步推理过程，力求详细",
    "decision": "准入 / 禁止",
    "explanation": "向访客口头说明的内容，请尽可能热情，不要那么正式。",
}}
```

请保证回复能够被Python的json.loads解析。
"""


class LLMResponse(TypedDict):
    reasoning: str
    decision: str
    explanation: str


class LLM:
    def generate(self, info: str) -> LLMResponse:
        messages = [
            {
                "role": "system",
                "content": PROMPT_SYSTEM_TEMPLATE,
            },
            {
                "role": "user",
                "content": PROMPT_USER_TEMPLATE.format(info=info),
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
