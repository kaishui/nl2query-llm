"""NII 模拟数据与 SQLite 初始化。

生产环境可替换为 Postgres / ClickHouse，接口保持不变。
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "nii.db"

# 维度枚举
BRANCHES = ["总行", "北京分行", "上海分行", "深圳分行"]
PRODUCTS = ["对公贷款", "零售贷款", "同业资产", "债券投资", "对公存款", "零售存款", "同业负债"]
CURRENCIES = ["人民币", "美元"]


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS nii_monthly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT NOT NULL,          -- 月份 YYYY-MM
            branch TEXT NOT NULL,          -- 分行
            product TEXT NOT NULL,         -- 产品线
            currency TEXT NOT NULL,        -- 币种
            asset_balance REAL NOT NULL,   -- 生息资产余额（亿元）
            asset_rate REAL NOT NULL,      -- 生息资产收益率（年化 %）
            interest_income REAL NOT NULL, -- 利息收入（亿元）
            liability_balance REAL NOT NULL,-- 计息负债余额（亿元）
            liability_rate REAL NOT NULL,  -- 计息负债成本率（年化 %）
            interest_expense REAL NOT NULL -- 利息支出（亿元）
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nii_period ON nii_monthly(period)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nii_branch ON nii_monthly(branch)")


def _seed(conn: sqlite3.Connection) -> None:
    """生成 2024-01 ~ 2026-08 的月度模拟数据（32 个月）。"""
    import random

    random.seed(42)

    rows = []
    periods = []
    # 生成 2024-01 到 2026-08
    for year in (2024, 2025, 2026):
        end_month = 12 if year < 2026 else 8
        for month in range(1, end_month + 1):
            periods.append(f"{year}-{month:02d}")

    for period in periods:
        for branch in BRANCHES:
            for product in PRODUCTS:
                for currency in CURRENCIES:
                    # 资产端 / 负债端
                    is_asset = product in {"对公贷款", "零售贷款", "同业资产", "债券投资"}
                    # 基础规模（亿元），随时间缓慢增长
                    base_balance = random.uniform(80, 500) * (1 + 0.01 * periods.index(period) / 12)
                    if is_asset:
                        asset_balance = base_balance
                        asset_rate = random.uniform(3.0, 5.5)
                        interest_income = asset_balance * asset_rate / 100 / 12
                        liability_balance = 0.0
                        liability_rate = 0.0
                        interest_expense = 0.0
                    else:
                        asset_balance = 0.0
                        asset_rate = 0.0
                        interest_income = 0.0
                        liability_balance = base_balance * 0.9
                        liability_rate = random.uniform(1.2, 2.8)
                        interest_expense = liability_balance * liability_rate / 100 / 12

                    rows.append(
                        (
                            period, branch, product, currency,
                            round(asset_balance, 2), round(asset_rate, 4),
                            round(interest_income, 4), round(liability_balance, 2),
                            round(liability_rate, 4), round(interest_expense, 4),
                        )
                    )

    conn.executemany(
        """INSERT INTO nii_monthly
           (period, branch, product, currency, asset_balance, asset_rate,
            interest_income, liability_balance, liability_rate, interest_expense)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()


def get_conn() -> sqlite3.Connection:
    """返回一个已初始化好 schema 与数据的连接。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    # 首次初始化时灌数据
    cnt = conn.execute("SELECT COUNT(*) AS c FROM nii_monthly").fetchone()["c"]
    if cnt == 0:
        _seed(conn)
    return conn


if __name__ == "__main__":
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM nii_monthly").fetchone()["c"]
    print(f"NII 数据初始化完成，共 {n} 行，数据库：{DB_PATH}")
    print(conn.execute("SELECT period, branch, product, interest_income, interest_expense "
                       "FROM nii_monthly LIMIT 3").fetchall())
