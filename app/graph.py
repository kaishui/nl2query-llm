"""显式 LangGraph 状态图：NII 智能问数主链路。

流程（每个环节都是显式节点，状态可审计、可回放）：

    意图识别 → SQL 生成（受指标口径约束）→ SQL 校验 → 执行 + 归因 → 答案生成
                    ↑                        │
                    └──── 校验失败带错误反馈重试（最多 MAX_RETRIES 次）

相比 langchain `create_agent` 黑盒，这里额外获得：
  - 自纠错回路：校验失败把错误原因回写给意图识别节点重新理解
  - human-in-the-loop：高危查询（全表扫描 / 超大跨度）interrupt 等人工审批
  - Checkpointer：会话状态持久化，支持多轮追问与断点续跑
  - 每个节点的输入输出都在 state 里，可接 LangSmith 做全链路 trace

SQL 仍基于 metrics.py 的受治理口径确定性拼装，LLM 不直写裸 SQL。
"""

from __future__ import annotations

import json
import re
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from . import db, metrics
from .attribution import attribute_nii
from .sql_guard import validate_sql, execute_readonly, SQLSecurityError

# 校验失败最多重试次数
MAX_RETRIES = 2
# 单次查询允许的最大时间跨度（月），超出视为口径错误直接打回
MAX_SPAN_MONTHS = 24
# 超过该跨度（或完全不带时间条件）视为高危查询，需人工审批
RISK_SPAN_MONTHS = 12

_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


# ---------------------------------------------------------------------------
# 状态定义
# ---------------------------------------------------------------------------

class QueryState(TypedDict, total=False):
    """状态图共享状态（每次问数一条 thread）。"""

    messages: Annotated[list, add_messages]
    question: str
    intent: dict[str, Any]           # 意图识别结果（Intent.model_dump）
    plan: dict[str, Any]             # SQL 生成结果：sql / params / 风险标记
    validation_error: str | None     # 校验失败原因（回写给意图节点重试）
    retry_count: int
    rejected: bool                   # 人工审批驳回标记
    data: dict[str, Any]             # 执行结果（查询序列或归因结果）
    answer: str


class Intent(BaseModel):
    """意图识别的结构化输出。"""

    kind: Literal["query", "attribution", "adhoc"] = Field(
        description=(
            "取值类问题用 query；环比/同比变化、归因、为什么涨降用 attribution；"
            "当受治理指标覆盖不了用户需求时用 adhoc（自由取数，走 opencode 生成 SQL）"
        )
    )
    metric: str | None = Field(default=None, description="受治理指标名，query 时必填")
    period_start: str | None = Field(default=None, description="起始月份 YYYY-MM")
    period_end: str | None = Field(default=None, description="结束月份 YYYY-MM")
    period_prev: str | None = Field(default=None, description="归因基期月份 YYYY-MM")
    period_curr: str | None = Field(default=None, description="归因比较期月份 YYYY-MM")
    branch: str | None = Field(default=None, description="分行，可选")
    product: str | None = Field(default=None, description="产品线，可选")
    currency: str | None = Field(default=None, description="币种，可选")


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _month_index(period: str) -> int:
    y, m = period.split("-")
    return int(y) * 12 + int(m)


def _span_months(start: str, end: str) -> int:
    return _month_index(end) - _month_index(start) + 1


def _build_where(intent: dict[str, Any], *, periods: tuple[str | None, str | None] | None = None,
                 single_period: str | None = None) -> tuple[str, list[Any]]:
    """按意图与受治理维度白名单拼 WHERE（列名全部来自代码常量，非 LLM 输入）。"""
    where, params = [], []
    if single_period:
        where.append("period = ?")
        params.append(single_period)
    elif periods:
        start, end = periods
        if start:
            where.append("period >= ?")
            params.append(start)
        if end:
            where.append("period <= ?")
            params.append(end)
    for key, col in (("branch", "branch"), ("product", "product"), ("currency", "currency")):
        if intent.get(key):
            where.append(f"{col} = ?")
            params.append(intent[key])
    return ("WHERE " + " AND ".join(where)) if where else "", params


# ---------------------------------------------------------------------------
# 节点
# ---------------------------------------------------------------------------

def build_graph(llm, checkpointer=None, nl2sql_fn=None):
    """构建 NII 问数状态图。

    llm 需支持 `with_structured_output`（意图识别）与 `invoke`（答案生成）。
    checkpointer 默认 MemorySaver（进程内会话记忆）；生产可换 SqliteSaver/PostgresSaver。
    nl2sql_fn 用于注入 opencode 动态取数函数（测试时可传 fake，默认用真实实现）。
    """
    if checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()

    if nl2sql_fn is None:
        from .opencode_sql import nl2sql as nl2sql_fn

    # -- 节点 1：意图识别 ----------------------------------------------------
    def intent_node(state: QueryState) -> dict:
        feedback = ""
        if state.get("validation_error"):
            feedback = (
                f"\n\n上一次理解有误，校验未通过：{state['validation_error']}\n"
                "请根据错误原因修正后重新输出。"
            )
        prompt = (
            "你是银行 NII（净利息收入）问数系统的意图识别器。"
            "请把用户问题解析为结构化意图，月份一律输出 YYYY-MM 格式。\n"
            "意图 kind 三选一：query=受治理指标取数；attribution=归因分析；"
            "adhoc=受治理指标覆盖不了的自由取数（走 opencode 动态生成 SQL，需人工审批）。\n\n"
            + metrics.build_metrics_prompt()
            + "\n\n维度取值范围：分行 "
            + "、".join(db.BRANCHES)
            + "；产品线 "
            + "、".join(db.PRODUCTS)
            + "；币种 "
            + "、".join(db.CURRENCIES)
            + "\n\n用户问题：" + state["question"]
            + feedback
        )
        intent: Intent = llm.with_structured_output(Intent).invoke(
            [HumanMessage(content=prompt)]
        )
        return {"intent": intent.model_dump(), "validation_error": None}

    # -- 节点 2：SQL 生成（受指标口径约束，确定性拼装；adhoc 走 opencode） ------
    def sql_gen_node(state: QueryState) -> dict:
        intent = state["intent"]
        plan: dict[str, Any] = {"kind": intent["kind"], "intent": intent}

        if intent["kind"] == "query":
            meta = metrics.resolve_metric(intent.get("metric") or "")
            # 指标未命中时不拼 SQL，交给校验节点打回
            plan["metric_meta"] = meta
            if meta:
                where, params = _build_where(
                    intent, periods=(intent.get("period_start"), intent.get("period_end"))
                )
                plan["sql"] = (
                    f"SELECT period, {meta['sql']} AS value FROM nii_monthly {where} "
                    "GROUP BY period ORDER BY period"
                )
                plan["params"] = params
        elif intent["kind"] == "attribution":
            plan["sql"] = (
                "SELECT SUM(asset_balance) AS asset_balance, "
                "SUM(interest_income) / NULLIF(SUM(asset_balance),0) * 100 * 12 AS asset_rate, "
                "SUM(liability_balance) AS liability_balance, "
                "SUM(interest_expense) / NULLIF(SUM(liability_balance),0) * 100 * 12 AS liability_rate "
                "FROM nii_monthly WHERE period = ? [+ 维度过滤]  -- 基期/比较期各执行一次"
            )
        else:  # adhoc：受治理指标覆盖不了，走 opencode 动态生成 SQL
            plan["adhoc"] = True
            plan["sql"] = None

        # 风险标记：无时间条件（全表扫描）或跨度超过 RISK_SPAN_MONTHS（仅 query 判定）
        start, end = intent.get("period_start"), intent.get("period_end")
        if intent["kind"] == "query":
            if not start and not end:
                plan["risk"] = {"flagged": True, "reason": "未限定时间范围，将全表扫描"}
            elif start and end and _PERIOD_RE.match(start) and _PERIOD_RE.match(end) \
                    and _span_months(start, end) > RISK_SPAN_MONTHS:
                plan["risk"] = {"flagged": True, "reason": f"查询跨度 {_span_months(start, end)} 个月，超过 {RISK_SPAN_MONTHS} 个月"}
        # adhoc 默认按高危处理（opencode 生成的 SQL 需人工审批）
        if intent["kind"] == "adhoc":
            plan["risk"] = {"flagged": True, "reason": "adhoc 自由取数（opencode 生成 SQL），需人工审批"}
        plan.setdefault("risk", {"flagged": False, "reason": ""})
        return {"plan": plan}

    # -- 节点 3：SQL 校验（口径 / 格式 / 跨度门禁） ---------------------------
    def validate_node(state: QueryState) -> dict:
        intent = state["intent"]
        plan = state["plan"]
        error: str | None = None

        if intent["kind"] == "query":
            if plan.get("metric_meta") is None:
                error = (
                    f"指标「{intent.get('metric')}」不在受治理指标字典中，"
                    f"可用指标：{'、'.join(metrics.METRICS)}"
                )
            else:
                for p in (intent.get("period_start"), intent.get("period_end")):
                    if p and not _PERIOD_RE.match(p):
                        error = f"月份格式非法：「{p}」，应为 YYYY-MM"
                        break
                start, end = intent.get("period_start"), intent.get("period_end")
                if error is None and start and end:
                    if _month_index(start) > _month_index(end):
                        error = f"起始月份 {start} 晚于结束月份 {end}"
                    elif _span_months(start, end) > MAX_SPAN_MONTHS:
                        error = f"查询跨度超过 {MAX_SPAN_MONTHS} 个月，请缩小时间范围"
        elif intent["kind"] == "attribution":
            prev, curr = intent.get("period_prev"), intent.get("period_curr")
            if not prev or not curr:
                error = "归因分析必须给出基期（period_prev）和比较期（period_curr）两个月份"
            elif not (_PERIOD_RE.match(prev) and _PERIOD_RE.match(curr)):
                error = f"归因月份格式非法：{prev} / {curr}，应为 YYYY-MM"
            elif _month_index(prev) >= _month_index(curr):
                error = f"基期 {prev} 必须早于比较期 {curr}"
        # adhoc：SQL 在 execute 阶段由 opencode 生成，生成后再由 sql_guard 校验，
        # 此处不做事先校验，直接放行。

        # 维度取值白名单
        if error is None:
            for key, enums, label in (
                ("branch", db.BRANCHES, "分行"),
                ("product", db.PRODUCTS, "产品线"),
                ("currency", db.CURRENCIES, "币种"),
            ):
                if intent.get(key) and intent[key] not in enums:
                    error = f"{label}「{intent[key]}」不存在，可选：{'、'.join(enums)}"
                    break

        retry_count = state.get("retry_count", 0)
        if error:
            retry_count += 1
        return {"validation_error": error, "retry_count": retry_count}

    # -- 节点 4：执行 + 归因（高危查询先 interrupt 人工审批） -----------------
    def execute_node(state: QueryState) -> dict:
        intent = state["intent"]
        plan = state["plan"]

        # adhoc：先由 opencode 生成 SQL，再走审批 + 校验 + 执行
        if intent["kind"] == "adhoc":
            result = nl2sql_fn(state["question"])
            if "error" in result:
                return {
                    "rejected": False,
                    "data": {"type": "adhoc", "error": result["error"]},
                }
            sql = result["sql"]
            # adhoc 一律要求人工审批（SQL 由 LLM 生成，金融合规）
            approved = interrupt({
                "type": "approval_required",
                "reason": "adhoc 自由取数（opencode 生成的 SQL）",
                "sql": sql,
            })
            if approved is not True:
                return {"rejected": True, "answer": "查询已被人工驳回（adhoc SQL），未执行。"}
            # 二次校验（防 opencode 绕过）
            try:
                rows = execute_readonly(sql)
            except SQLSecurityError as e:
                return {
                    "rejected": False,
                    "data": {"type": "adhoc", "error": f"SQL 未通过安全校验：{e}", "sql": sql},
                }
            return {
                "rejected": False,
                "data": {"type": "adhoc", "sql": sql, "rows": rows},
            }

        if plan["risk"]["flagged"]:
            approved = interrupt({
                "type": "approval_required",
                "reason": plan["risk"]["reason"],
                "sql": plan.get("sql", ""),
            })
            if approved is not True:
                return {"rejected": True, "answer": f"查询已被人工驳回（{plan['risk']['reason']}），未执行。"}

        conn = db.get_conn()
        if intent["kind"] == "query":
            rows = conn.execute(plan["sql"], plan["params"]).fetchall()
            data = {
                "type": "query",
                "metric": intent["metric"],
                "unit": plan["metric_meta"]["unit"],
                "series": [dict(r) for r in rows],
            }
        else:
            def agg(period: str) -> dict[str, float]:
                where, params = _build_where(intent, single_period=period)
                row = conn.execute(
                    "SELECT SUM(asset_balance) AS asset_balance, "
                    "SUM(interest_income) / NULLIF(SUM(asset_balance),0) * 100 * 12 AS asset_rate, "
                    "SUM(liability_balance) AS liability_balance, "
                    "SUM(interest_expense) / NULLIF(SUM(liability_balance),0) * 100 * 12 AS liability_rate "
                    f"FROM nii_monthly {where}",
                    params,
                ).fetchone()
                return {k: (row[k] or 0.0) for k in
                        ("asset_balance", "asset_rate", "liability_balance", "liability_rate")}

            prev = agg(intent["period_prev"])
            curr = agg(intent["period_curr"])
            result = attribute_nii(
                {"balance": prev["asset_balance"], "rate": prev["asset_rate"]},
                {"balance": curr["asset_balance"], "rate": curr["asset_rate"]},
                {"balance": prev["liability_balance"], "rate": prev["liability_rate"]},
                {"balance": curr["liability_balance"], "rate": curr["liability_rate"]},
            )
            result.update({
                "type": "attribution",
                "period_prev": intent["period_prev"],
                "period_curr": intent["period_curr"],
            })
            data = result
        return {"data": data, "rejected": False}

    # -- 节点 5：答案生成 ------------------------------------------------------
    def answer_node(state: QueryState) -> dict:
        # 校验最终失败 / 人工驳回时不调用 LLM，直接给确定性答复
        if state.get("rejected"):
            return {"answer": state["answer"]}
        if state.get("validation_error"):
            return {"answer": f"抱歉，多次尝试后仍无法理解您的问题：{state['validation_error']}"}
        # adhoc 生成/校验失败时直接返回错误
        if state.get("data", {}).get("error"):
            return {"answer": f"自由取数失败：{state['data']['error']}"}

        data_json = json.dumps(state["data"], ensure_ascii=False, indent=2)
        msgs = [
            SystemMessage(content=(
                "你是银行 NII（净利息收入）智能分析助手。"
                "只能基于给定数据作答，不得编造任何数字；"
                "归因问题须结合规模/价格/结构三效应解读。"
            )),
            HumanMessage(content=f"用户问题：{state['question']}\n\n取数结果（JSON）：\n{data_json}"),
        ]
        resp = llm.invoke(msgs)
        return {"answer": resp.content}

    # -- 路由 ------------------------------------------------------------------
    def route_after_validate(state: QueryState) -> str:
        if state.get("validation_error") is None:
            return "execute"
        if state.get("retry_count", 0) <= MAX_RETRIES:
            return "retry"
        return "give_up"

    # -- 组图 ------------------------------------------------------------------
    g = StateGraph(QueryState)
    g.add_node("intent", intent_node)
    g.add_node("sql_gen", sql_gen_node)
    g.add_node("validate", validate_node)
    g.add_node("execute", execute_node)
    g.add_node("answer", answer_node)

    g.add_edge(START, "intent")
    g.add_edge("intent", "sql_gen")
    g.add_edge("sql_gen", "validate")
    g.add_conditional_edges(
        "validate",
        route_after_validate,
        {"retry": "intent", "execute": "execute", "give_up": "answer"},
    )
    g.add_edge("execute", "answer")
    g.add_edge("answer", END)

    return g.compile(checkpointer=checkpointer)


__all__ = ["build_graph", "QueryState", "Intent", "Command"]
