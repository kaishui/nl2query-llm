"""opencode 动态 SQL 生成模块。

当用户问题无法命中受治理指标时，走 opencode 兜底：
自然语言 → opencode 生成 SQL → sql_guard 校验 → 只读执行。

opencode 采用 client/server 架构：Python 进程连接一个 opencode server
（默认 http://127.0.0.1:4010，可用 OPENCODE_BASE_URL 覆盖），
通过 session.chat() 发消息。

注意：opencode 只负责生成 SQL，执行与校验始终在本模块的 Python 层，
opencode 不直接接触数据库。
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from . import db
from .sql_guard import execute_readonly, SQLSecurityError

# opencode SDK 导入失败时优雅降级（未安装不影响确定性路径）
try:
    from opencode_ai import Opencode as _Opencode
    _OPENCODE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _Opencode = None
    _OPENCODE_AVAILABLE = False

OPENCODE_BASE_URL = os.getenv("OPENCODE_BASE_URL", "http://127.0.0.1:4010")


def build_schema_prompt() -> str:
    """生成只读 schema 说明，注入给 opencode。"""
    conn = db.get_conn()
    cols = conn.execute("PRAGMA table_info(nii_monthly)").fetchall()
    col_desc = "\n".join(f"  - {c['name']} ({c['type']})" for c in cols)

    return (
        "你是一个 SQL 生成器，只负责把自然语言问题翻译成一条 SQLite 的 SELECT 语句。\n"
        "严格约束：\n"
        "1. 只能生成一条 SELECT 查询，禁止任何写操作（INSERT/UPDATE/DELETE 等）。\n"
        "2. 只能使用下面的表和列，禁止自造表名或列名。\n"
        "3. 不要写注释，不要带分号结尾的多语句。\n"
        "4. 只输出 SQL 本身，不要任何解释、不要 markdown 代码块。\n\n"
        f"表 nii_monthly 的列：\n{col_desc}\n\n"
        "数据口径：asset_balance=生息资产余额(亿元)、asset_rate=生息资产收益率(年化%)、"
        "interest_income=利息收入(亿元)、liability_balance=计息负债余额(亿元)、"
        "liability_rate=计息负债成本率(年化%)、interest_expense=利息支出(亿元)。\n"
        "净利息收入 NII = interest_income - interest_expense。\n"
    )


class OpencodeSQLGenerator:
    """封装 opencode 客户端，负责生成 SQL。"""

    def __init__(self) -> None:
        if not _OPENCODE_AVAILABLE:
            raise RuntimeError(
                "opencode SDK 未安装，请先 `pip install --pre opencode-ai`，"
                "并启动 opencode server（默认 127.0.0.1:4010）"
            )
        self._client = _Opencode(base_url=OPENCODE_BASE_URL)

    def generate_sql(self, question: str) -> str:
        """调 opencode 生成一条 SELECT 语句。"""
        session = self._client.sessions.create()
        try:
            prompt = build_schema_prompt() + f"\n\n问题：{question}"
            response = session.chat(message=prompt)
            sql = self._extract_sql(response)
            return sql
        finally:
            # 清理会话（若 SDK 支持 delete）
            try:
                session.delete()  # type: ignore[attr-defined]
            except Exception:
                pass

    @staticmethod
    def _extract_sql(response: Any) -> str:
        """从 opencode 响应中提取 SQL 文本（兼容多种返回结构）。"""
        text = ""
        if isinstance(response, str):
            text = response
        elif hasattr(response, "content"):
            content = response.content
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = "".join(
                    getattr(c, "text", "") or str(c) for c in content
                )
        else:
            text = str(response)

        # 去掉可能的 markdown 代码块包裹
        text = re.sub(r"```(?:sql)?", "", text).strip()
        # 截取第一条 SELECT 到结尾
        m = re.search(r"(?is)\bSELECT\b.*", text)
        if m:
            text = m.group(0).strip().rstrip(";")
        return text


def nl2sql(question: str, generator: OpencodeSQLGenerator | None = None) -> dict[str, Any]:
    """自然语言 → opencode 生成 SQL → 校验 → 只读执行。

    返回 {"sql": ..., "rows": [...], "source": "opencode"}，
    失败时返回 {"error": ..., "source": "opencode"}。
    """
    try:
        gen = generator or OpencodeSQLGenerator()
        sql = gen.generate_sql(question)
    except Exception as e:  # opencode 不可用/调用失败
        return {"error": f"opencode 调用失败：{e}", "source": "opencode"}

    try:
        rows = execute_readonly(sql)
    except SQLSecurityError as e:
        return {"error": f"SQL 未通过安全校验：{e}", "sql": sql, "source": "opencode"}
    except Exception as e:
        return {"error": f"SQL 执行失败：{e}", "sql": sql, "source": "opencode"}

    return {"sql": sql, "rows": rows, "source": "opencode"}
