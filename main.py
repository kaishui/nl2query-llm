"""CLI 入口：python main.py "你的问题" """

import sys

from langchain_core.messages import HumanMessage

from app import db
from app.agent import build_agent, create_default_llm


def main() -> None:
    # 初始化数据（幂等）
    db.get_conn()

    if len(sys.argv) < 2:
        print("用法：python main.py \"你的问题\"")
        sys.exit(1)

    question = sys.argv[1]
    llm = create_default_llm()
    agent = build_agent(llm)

    print(f"问：{question}\n")
    result = agent.invoke({"messages": [HumanMessage(content=question)]})
    # 取最后一条 AI 消息作为答案
    answer = result["messages"][-1].content
    print(answer)


if __name__ == "__main__":
    main()
