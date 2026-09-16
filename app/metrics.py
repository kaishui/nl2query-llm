"""NII 指标口径定义（受治理的指标字典）。

这是整个系统的核心资产：LLM 不直接写裸 SQL，而是基于这些受治理的
指标/维度生成查询，从而保证「口径即代码」、口径一致、可追溯。
"""

# 指标字典：name -> SQL 表达式（相对 nii_monthly 表）
METRICS = {
    "NII": {
        "sql": "SUM(interest_income - interest_expense)",
        "unit": "亿元",
        "desc": "净利息收入 = 利息收入 - 利息支出",
    },
    "利息收入": {
        "sql": "SUM(interest_income)",
        "unit": "亿元",
        "desc": "生息资产产生的利息收入",
    },
    "利息支出": {
        "sql": "SUM(interest_expense)",
        "unit": "亿元",
        "desc": "计息负债产生的利息支出",
    },
    "生息资产余额": {
        "sql": "SUM(asset_balance)",
        "unit": "亿元",
        "desc": "生息资产平均余额",
    },
    "计息负债余额": {
        "sql": "SUM(liability_balance)",
        "unit": "亿元",
        "desc": "计息负债平均余额",
    },
    "净息差_NIM": {
        "sql": "(SUM(interest_income) - SUM(interest_expense)) / NULLIF(SUM(asset_balance), 0) * 100 * 12",
        "unit": "%",
        "desc": "净息差（年化）= NII / 生息资产余额 × 12 × 100",
    },
    "生息资产收益率": {
        "sql": "SUM(interest_income) / NULLIF(SUM(asset_balance), 0) * 100 * 12",
        "unit": "%",
        "desc": "生息资产收益率（年化）",
    },
    "计息负债成本率": {
        "sql": "SUM(interest_expense) / NULLIF(SUM(liability_balance), 0) * 100 * 12",
        "unit": "%",
        "desc": "计息负债成本率（年化）",
    },
}

# 维度字典：name -> 列名
DIMENSIONS = {
    "时间": "period",
    "月份": "period",
    "分行": "branch",
    "产品": "product",
    "产品线": "product",
    "币种": "currency",
}

# 时间/维度别名（用于帮助 LLM 理解同义词）
ALIASES = {
    "NII": ["净利息收入", "利息净收入"],
    "净息差_NIM": ["NIM", "净息差", "息差"],
    "生息资产收益率": ["资产收益率", "资产端收益率"],
    "计息负债成本率": ["负债成本率", "负债端成本率", "资金成本"],
}


def build_metrics_prompt() -> str:
    """生成注入给 LLM 的指标口径说明。"""
    lines = ["可用的受治理指标（只能使用这些，禁止自造列名）："]
    for name, meta in METRICS.items():
        aliases = "、".join(ALIASES.get(name, []))
        alias_part = f"（别名：{aliases}）" if aliases else ""
        lines.append(f"  - {name}{alias_part}：{meta['desc']}，单位 {meta['unit']}")
    lines.append("可用维度（列）：period（月份）、branch（分行）、product（产品线）、currency（币种）")
    return "\n".join(lines)


def resolve_metric(name: str) -> dict | None:
    """根据名称或别名解析指标，找不到返回 None。"""
    if name in METRICS:
        return METRICS[name]
    for canonical, aliases in ALIASES.items():
        if name in aliases or name == canonical:
            return METRICS[canonical]
    return None
