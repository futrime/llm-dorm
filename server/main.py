import asyncio
import datetime

from langchain_community.llms.tongyi import Tongyi
from langchain_core.prompts import PromptTemplate

from comm import ZmqComm

BROKER_HOST = "10.8.0.5"
BROKER_FRONTEND_PORT = 5555
BROKER_BACKEND_PORT = 5556
ENDPOINT = "server"


async def main():
    comm = ZmqComm(
        broker_host=BROKER_HOST,
        broker_backend_port=BROKER_BACKEND_PORT,
        broker_frontend_port=BROKER_FRONTEND_PORT,
        endpoint=ENDPOINT,
    )

    await comm.connect()

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
