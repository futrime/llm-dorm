"""Main module."""

import asyncio
import datetime

from langchain_community.llms.tongyi import Tongyi
from langchain_core.prompts import PromptTemplate


async def main():
    """Main function."""

    llm = Tongyi(model_name="qwen-turbo")  # type: ignore

    template = """Question: {question}

    Answer: Let's think step by step."""

    prompt = PromptTemplate.from_template(template)

    chain = prompt | llm

    question = "What NFL team won the Super Bowl in the year Justin Bieber was born?"

    print(datetime.datetime.now())

    ans = await chain.ainvoke({"question": question})

    print(datetime.datetime.now())

    print(ans)


if __name__ == "__main__":
    asyncio.run(main())
