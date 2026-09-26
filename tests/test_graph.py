"""状态图测试：用 FakeLLM 驱动，不依赖真实 LLM。

覆盖：
  - query 全链路（意图 → 生成 → 校验 → 执行 → 答案）
  - 校验失败带错误反馈重试
  - 高危查询 interrupt 人工审批（批准 / 驳回）
  - checkpointer 多轮会话记忆
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.types import Command

from app import db
from app.graph import Intent, build_graph


class FakeStructured:
    """模拟 llm.with_structured_output(Intent) 的返回值，按队列依次吐意图。"""

    def __init__(self, intents):
        self._intents = list(intents)

    def invoke(self, _msgs):
        assert self._intents, "意图队列已空，图的路由不符合预期"
        return self._intents.pop(0)


class FakeLLM:
    """intent 队列依次返回；invoke（答案生成）返回固定文本。"""

    def __init__(self, intents, answer="这是基于真实数据生成的答案"):
        self._structured = FakeStructured(intents)
        self._answer = answer

    def with_structured_output(self, _schema):
        return self._structured

    def invoke(self, _msgs):
        return SimpleNamespace(content=self._answer)


def _cfg(tag: str) -> dict:
    return {"configurable": {"thread_id": f"test-{tag}"}}


def test_query_flow():
    """query 全链路：查到 2025 年前 3 个月 NII 序列。"""
    db.get_conn()
    graph = build_graph(FakeLLM([
        Intent(kind="query", metric="NII", period_start="2025-01", period_end="2025-03"),
    ]))
    result = graph.invoke({"question": "2025年一季度 NII 多少", "messages": []}, config=_cfg("query"))
    assert result["answer"] == "这是基于真实数据生成的答案"
    assert result["data"]["type"] == "query"
    assert len(result["data"]["series"]) == 3, "应有 3 个月数据"
    assert result["retry_count"] == 0
    print(f"✓ query 全链路通过，序列 {len(result['data']['series'])} 期，无重试")


def test_attribution_flow():
    """attribution 全链路：三效应自洽。"""
    graph = build_graph(FakeLLM([
        Intent(kind="attribution", period_prev="2025-06", period_curr="2025-09"),
    ]))
    result = graph.invoke({"question": "Q3 NII 环比为什么变了", "messages": []}, config=_cfg("attr"))
    data = result["data"]
    assert data["type"] == "attribution"
    total = data["scale_effect"] + data["price_effect"] + data["structure_effect"]
    assert abs(total - data["nii_delta"]) < 1e-3, "归因三项之和应等于 nii_delta"
    print(f"✓ attribution 全链路通过，nii_delta={data['nii_delta']}")


def test_validation_retry():
    """第一次给出未知指标被打回，带错误反馈重试后成功。"""
    graph = build_graph(FakeLLM([
        Intent(kind="query", metric="不存在的指标", period_start="2025-01", period_end="2025-03"),
        Intent(kind="query", metric="NII", period_start="2025-01", period_end="2025-03"),
    ]))
    result = graph.invoke({"question": "一季度 NII", "messages": []}, config=_cfg("retry"))
    assert result["retry_count"] == 1, "应重试 1 次"
    assert result["data"]["type"] == "query", "重试后应成功取数"
    print("✓ 校验失败带错误反馈重试成功（retry_count=1）")


def test_validation_give_up():
    """连续坏意图超过重试上限后，走 give_up 给确定性答复（不再调用意图）。"""
    bad = Intent(kind="query", metric="不存在的指标", period_start="2025-01", period_end="2025-03")
    # MAX_RETRIES=2 → 最多 3 次意图识别（首次 + 2 次重试）
    graph = build_graph(FakeLLM([bad, bad, bad]))
    result = graph.invoke({"question": "查一个不存在的指标", "messages": []}, config=_cfg("giveup"))
    assert "data" not in result, "放弃时不应有取数结果"
    assert "无法" in result["answer"] or "多次" in result["answer"]
    print("✓ 超过重试上限后优雅放弃，返回确定性错误答复")


def test_high_risk_interrupt_approve():
    """无时间条件触发全表扫描审批；批准后正常执行。"""
    graph = build_graph(FakeLLM([
        Intent(kind="query", metric="NII"),  # 不带时间 → 高危
    ]))
    result = graph.invoke({"question": "全部 NII", "messages": []}, config=_cfg("approve"))
    assert "__interrupt__" in result, "高危查询应触发 interrupt"
    payload = result["__interrupt__"][0].value
    assert payload["type"] == "approval_required"
    result = graph.invoke(Command(resume=True), config=_cfg("approve"))
    assert result["data"]["type"] == "query", "批准后应执行查询"
    assert len(result["data"]["series"]) > 12, "全表扫描应返回全部月份"
    print(f"✓ 高危查询审批批准后执行，返回 {len(result['data']['series'])} 期")


def test_high_risk_interrupt_reject():
    """人工驳回后不执行、不调 LLM，直接给确定性答复。"""
    graph = build_graph(FakeLLM([
        Intent(kind="query", metric="NII"),
    ]))
    result = graph.invoke({"question": "全部 NII", "messages": []}, config=_cfg("reject"))
    assert "__interrupt__" in result
    result = graph.invoke(Command(resume=False), config=_cfg("reject"))
    assert result["rejected"] is True
    assert "驳回" in result["answer"]
    assert "data" not in result, "驳回后不应有取数结果"
    print("✓ 高危查询人工驳回，未执行且返回确定性答复")


def test_checkpointer_multi_turn():
    """同一 thread_id 多轮：第二轮可复用第一轮状态（checkpointer 生效）。"""
    graph = build_graph(FakeLLM([
        Intent(kind="query", metric="NII", period_start="2025-01", period_end="2025-03"),
        Intent(kind="attribution", period_prev="2025-03", period_curr="2025-06"),
    ]))
    r1 = graph.invoke({"question": "Q1 NII", "messages": []}, config=_cfg("multi"))
    r2 = graph.invoke({"question": "那 Q2 环比为什么变", "messages": []}, config=_cfg("multi"))
    assert r1["data"]["type"] == "query"
    assert r2["data"]["type"] == "attribution"
    print("✓ checkpointer 多轮会话正常（同一 thread 两次 invoke）")


if __name__ == "__main__":
    test_query_flow()
    test_attribution_flow()
    test_validation_retry()
    test_validation_give_up()
    test_high_risk_interrupt_approve()
    test_high_risk_interrupt_reject()
    test_checkpointer_multi_turn()
    print("\n状态图测试全部通过 ✓")
