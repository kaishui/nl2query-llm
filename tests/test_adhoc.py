"""opencode 动态 SQL（adhoc 分支）测试：用 FakeLLM + 注入 fake nl2sql，不依赖真实 opencode/LLM。

覆盖：
  - adhoc 全链路：意图 adhoc → opencode 生成 SQL → 人工审批 → 校验 → 执行 → 答案
  - adhoc 生成失败优雅降级（返回 error）
  - adhoc 生成危险 SQL 被安全校验拦截
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.types import Command

from app import db
from app.graph import Intent, build_graph


class FakeStructured:
    def __init__(self, intents):
        self._intents = list(intents)

    def invoke(self, _msgs):
        assert self._intents, "意图队列已空"
        return self._intents.pop(0)


class FakeLLM:
    def __init__(self, intents, answer="基于数据的答案"):
        self._structured = FakeStructured(intents)
        self._answer = answer

    def with_structured_output(self, _schema):
        return self._structured

    def invoke(self, _msgs):
        return SimpleNamespace(content=self._answer)


def _cfg(tag):
    return {"configurable": {"thread_id": f"test-adhoc-{tag}"}}


def _fake_nl2sql_ok(question):
    return {"sql": "SELECT branch, SUM(interest_income - interest_expense) AS nii FROM nii_monthly GROUP BY branch", "rows": []}


def _fake_nl2sql_error(question):
    return {"error": "opencode 调用失败：模拟错误"}


def _fake_nl2sql_danger(question):
    return {"sql": "DELETE FROM nii_monthly", "rows": []}


def test_adhoc_flow_approve():
    """adhoc 全链路：生成 SQL → 审批批准 → 校验执行成功。"""
    db.get_conn()
    graph = build_graph(
        FakeLLM([Intent(kind="adhoc")]),
        nl2sql_fn=_fake_nl2sql_ok,
    )
    result = graph.invoke({"question": "各分行 NII 明细", "messages": []}, config=_cfg("ok"))
    assert "__interrupt__" in result, "adhoc 应触发人工审批"
    payload = result["__interrupt__"][0].value
    assert payload["type"] == "approval_required"
    result = graph.invoke(Command(resume=True), config=_cfg("ok"))
    assert result["data"]["type"] == "adhoc"
    assert "sql" in result["data"]
    assert result["data"]["rows"] is not None
    print("✓ adhoc 全链路通过（审批批准 + 校验 + 执行）")


def test_adhoc_generation_error():
    """opencode 生成失败时优雅降级，返回 error 且不调用 LLM 解读。"""
    graph = build_graph(
        FakeLLM([Intent(kind="adhoc")]),
        nl2sql_fn=_fake_nl2sql_error,
    )
    result = graph.invoke({"question": "任意问题", "messages": []}, config=_cfg("err"))
    assert result["data"]["type"] == "adhoc"
    assert "error" in result["data"]
    assert "自由取数失败" in result["answer"]
    print("✓ adhoc 生成失败优雅降级")


def test_adhoc_danger_sql_blocked():
    """opencode 生成危险 SQL（DELETE）被 sql_guard 拦截。"""
    graph = build_graph(
        FakeLLM([Intent(kind="adhoc")]),
        nl2sql_fn=_fake_nl2sql_danger,
    )
    result = graph.invoke({"question": "任意问题", "messages": []}, config=_cfg("danger"))
    assert "__interrupt__" in result, "adhoc 仍应先审批"
    result = graph.invoke(Command(resume=True), config=_cfg("danger"))
    # 审批通过后，危险 SQL 会被二次校验拦截
    assert "error" in result["data"], "危险 SQL 应被拦截"
    assert "安全校验" in result["data"]["error"]
    print("✓ adhoc 危险 SQL 被安全校验拦截")


if __name__ == "__main__":
    test_adhoc_flow_approve()
    test_adhoc_generation_error()
    test_adhoc_danger_sql_blocked()
    print("\nopencode adhoc 分支测试全部通过 ✓")
