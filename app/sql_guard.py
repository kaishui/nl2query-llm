"""SQL 安全校验与只读执行。

opencode 只负责「生成 SQL」，本模块负责「校验 + 执行」，确保：
1. 只允许 SELECT（只读），拒绝任何写操作
2. 拒绝多语句、注释注入、危险关键字
3. 用只读连接执行，双保险
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from . import db

# 危险关键字（大小写不敏感匹配），命中即拒绝
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE", "ATTACH",
    "DETACH", "VACUUM", "PRAGMA", "EXEC", "EXECUTE", "CALL",
]

# 多语句 / 注释注入特征
DANGEROUS_PATTERNS = [
    r";\s*\w",      # 分号后跟新语句
    r"--",          # SQL 注释
    r"/\*",         # 块注释
    r"\*/",
]


class SQLSecurityError(Exception):
    """SQL 未通过安全校验时抛出。"""


def validate_sql(sql: str) -> None:
    """校验 SQL 是否只读安全，不安全则抛 SQLSecurityError。"""
    if not sql or not sql.strip():
        raise SQLSecurityError("SQL 为空")

    # 去掉首尾空白后必须是一个 SELECT 语句
    stripped = sql.strip()
    if not re.match(r"(?i)^SELECT\b", stripped):
        raise SQLSecurityError(f"仅允许 SELECT 查询，收到：{stripped[:50]}")

    # 危险关键字检查（词边界匹配）
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"(?i)\b{kw}\b", stripped):
            raise SQLSecurityError(f"SQL 含危险关键字：{kw}")

    # 注入特征检查
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, stripped):
            raise SQLSecurityError(f"SQL 含危险模式：{pat}")

    # 分号数量检查（只允许末尾一个可选分号）
    if stripped.count(";") > 1:
        raise SQLSecurityError("SQL 含多语句")


def execute_readonly(sql: str, limit: int = 200) -> list[dict[str, Any]]:
    """校验并只读执行 SQL，返回行列表（dict）。

    使用 SQLite 的只读连接 + 结果行数限制，双保险。
    """
    validate_sql(sql)

    # 附加 LIMIT 保护（若 SQL 未显式 limit）
    if not re.search(r"(?i)\bLIMIT\b", sql):
        sql = sql.rstrip().rstrip(";") + f" LIMIT {limit}"

    # 只读连接
    conn = sqlite3.connect(f"file:{db.DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
