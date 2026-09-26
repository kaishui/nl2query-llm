"""CLI 入口。

单问单答：
    python main.py "2025年9月 NII 是多少"

多轮会话（同一 thread_id 共享记忆，可追问）：
    python main.py --chat

高危查询（全表扫描 / 跨度超 12 个月）会触发人工审批，按提示输入 y/n。
"""

import sys

from langgraph.types import Command

from app import db
from app.agent import create_default_llm
from app.graph import build_graph


def ask(graph, config: dict, question: str) -> str:
    """跑一轮问数；遇到 interrupt（人工审批）时提示用户确认后续跑。"""
    result = graph.invoke({"question": question, "messages": []}, config=config)
    while "__interrupt__" in result:
        hit = result["__interrupt__"][0].value
        print(f"\n[人工审批] {hit.get('reason', '高危查询')}")
        print(f"  SQL: {hit.get('sql', '')}")
        choice = input("  是否批准执行？(y/n) ").strip().lower()
        result = graph.invoke(Command(resume=(choice == "y")), config=config)
    return result.get("answer", "（未生成答案）")


def main() -> None:
    db.get_conn()  # 初始化数据（幂等）

    llm = create_default_llm()
    graph = build_graph(llm)
    config = {"configurable": {"thread_id": "cli-default"}}

    if len(sys.argv) >= 2 and sys.argv[1] == "--chat":
        print("进入多轮会话（同一 thread 共享记忆），输入 exit 退出。")
        while True:
            try:
                question = input("\n问：").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if question.lower() in {"exit", "quit", ""}:
                break
            print(f"\n答：{ask(graph, config, question)}")
        return

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    question = sys.argv[1]
    print(f"问：{question}\n")
    print(f"答：{ask(graph, config, question)}")


if __name__ == "__main__":
    main()
