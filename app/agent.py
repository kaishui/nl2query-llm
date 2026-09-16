"""LangChain 问数 Agent 主链路。

流程：意图识别 → SQL 生成（受指标口径约束）→ 执行 → 归因/解读。

LLM 通过 tool-calling 调用 `query_metric` / `attribute_nii` 两个工具，
SQL 在工具内部基于受治理的指标口径确定性拼装，而非 LLM 直写裸 SQL。
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from langchain_core.tools import tool

from . import db, metrics
from .attribution import attribute_nii


# ---------------------------------------------------------------------------
# 工具层：受治理的取数能力
# ---------------------------------------------------------------------------

@tool
def query_metric(
    metric: str,
    period_start: str | None = None,
    period_end: str | None = None,
    branch: str | None = None,
    product: str | None = None,
    currency: str | None = None,
) -> str:
    """按受治理指标查询 NII 数据。

    参数：
      metric: 指标名，必须是 metrics.py 中定义的指标（如「NII」「净息差_NIM」）
      period_start/period_end: 月份范围，如 "2025-01"、"2025-12"
      branch: 分行（可选）
      product: 产品线（可选）
      currency: 币种（可选）

    返回 JSON 字符串，含指标值或按 period 分组的时间序列。
    """
    meta = metrics.resolve_metric(metric)
    if meta is None:
        return json.dumps({"error": f"未知指标「{metric}」", "available": list(metrics.METRICS)}, ensure_ascii=False)

    where, params = [], []
    if period_start:
        where.append("period >= ?")
        params.append(period_start)
    if period_end:
        where.append("period <= ?")
        params.append(period_end)
    if branch:
        where.append("branch = ?")
        params.append(branch)
    if product:
        where.append("product = ?")
        params.append(product)
    if currency:
        where.append("currency = ?")
        params.append(currency)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    conn: sqlite3.Connection = db.get_conn()
    rows = conn.execute(
        f"SELECT period, {meta['sql']} AS value FROM nii_monthly {where_sql} "
        f"GROUP BY period ORDER BY period",
        params,
    ).fetchall()

    result = {"metric": metric, "unit": meta["unit"], "series": [dict(r) for r in rows]}
    return json.dumps(result, ensure_ascii=False)


@tool
def attribute_nii_between(
    period_prev: str,
    period_curr: str,
    branch: str | None = None,
    product: str | None = None,
) -> str:
    """对两个期间做 NII 归因分解（规模/价格/结构三效应）。

    参数：
      period_prev: 基期月份，如 "2025-06"
      period_curr: 比较期月份，如 "2025-09"
      branch/product: 可选过滤

    返回 JSON，含 nii_delta、scale_effect、price_effect、structure_effect。
    """
    def agg(period: str) -> dict[str, float]:
        cond = "period = ?"
        params: list[Any] = [period]
        if branch:
            cond += " AND branch = ?"
            params.append(branch)
        if product:
            cond += " AND product = ?"
            params.append(product)
        conn = db.get_conn()
        row = conn.execute(
            f"SELECT SUM(asset_balance) AS asset_balance, "
            f"SUM(interest_income) / NULLIF(SUM(asset_balance),0) * 100 * 12 AS asset_rate, "
            f"SUM(liability_balance) AS liability_balance, "
            f"SUM(interest_expense) / NULLIF(SUM(liability_balance),0) * 100 * 12 AS liability_rate "
            f"FROM nii_monthly WHERE {cond}",
            params,
        ).fetchone()
        return {
            "asset_balance": row["asset_balance"] or 0.0,
            "asset_rate": row["asset_rate"] or 0.0,
            "liability_balance": row["liability_balance"] or 0.0,
            "liability_rate": row["liability_rate"] or 0.0,
        }

    prev = agg(period_prev)
    curr = agg(period_curr)
    result = attribute_nii(
        {"balance": prev["asset_balance"], "rate": prev["asset_rate"]},
        {"balance": curr["asset_balance"], "rate": curr["asset_rate"]},
        {"balance": prev["liability_balance"], "rate": prev["liability_rate"]},
        {"balance": curr["liability_balance"], "rate": curr["liability_rate"]},
    )
    result["period_prev"] = period_prev
    result["period_curr"] = period_curr
    return json.dumps(result, ensure_ascii=False)


TOOLS = [query_metric, attribute_nii_between]


# ---------------------------------------------------------------------------
# Agent 层
# ---------------------------------------------------------------------------

def build_agent(llm):
    """基于给定的 LLM 构建 Agent（tool-calling）。

    返回 LangGraph 编译图，invoke 输入为 {"messages": [HumanMessage(...)]}，
    输出为 {"messages": [...]}，最后一条 AIMessage 即答案。
    """
    from langchain.agents import create_agent

    system = (
        "你是银行 NII（净利息收入）智能分析助手。\n"
        "回答必须基于调用工具得到的真实数据，不得凭空编造数字。\n"
        "分析类问题（环比/同比变化、归因、为什么下降）应优先调用 attribute_nii_between 做归因分解。\n"
        "取值类问题应调用 query_metric，且指标名必须来自受治理指标。\n\n"
        + metrics.build_metrics_prompt()
    )
    return create_agent(
        model=llm,
        tools=TOOLS,
        system_prompt=system,
    )


def create_default_llm():
    """创建默认 LLM（OpenAI 兼容接口）。"""
    import os

    from langchain_openai import ChatOpenAI

    base_url = os.getenv("OPENAI_BASE_URL")
    kwargs: dict[str, Any] = {"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "temperature": 0}
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)
