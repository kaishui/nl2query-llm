"""NII 归因三效应计算。

NII = 资产端利息收入 - 负债端利息支出
归因增量分解（环比/同比）：
  - 规模效应 = Δ余额 × 上期利率
  - 价格效应 = 上期余额 × Δ利率
  - 结构效应 = 交叉项（残差，Δ余额 × Δ利率）
"""

from __future__ import annotations


def attribute_single_side(
    bal_prev: float,
    bal_curr: float,
    rate_prev: float,
    rate_curr: float,
) -> dict[str, float]:
    """对单边（资产端或负债端）做量×价归因。

    利率为年化 %，余额为亿元，返回各项对「利息」的贡献（亿元/月）。
    """
    # 利息 = 余额 × 利率(%) / 100 / 12
    def interest(bal: float, rate: float) -> float:
        return bal * rate / 100 / 12

    i_prev = interest(bal_prev, rate_prev)
    i_curr = interest(bal_curr, rate_curr)
    total_delta = i_curr - i_prev

    # 规模效应：余额变化 × 上期利率
    scale = interest(bal_curr - bal_prev, rate_prev)
    # 价格效应：上期余额 × 利率变化
    price = interest(bal_prev, rate_curr - rate_prev)
    # 结构效应（交叉项）
    structure = total_delta - scale - price

    return {
        "total_delta": round(total_delta, 4),
        "scale_effect": round(scale, 4),
        "price_effect": round(price, 4),
        "structure_effect": round(structure, 4),
    }


def attribute_nii(
    asset_prev: dict[str, float],
    asset_curr: dict[str, float],
    liab_prev: dict[str, float],
    liab_curr: dict[str, float],
) -> dict[str, float]:
    """NII 归因 = 资产端归因 - 负债端归因（负债端取反）。"""
    a = attribute_single_side(
        asset_prev["balance"], asset_curr["balance"],
        asset_prev["rate"], asset_curr["rate"],
    )
    l = attribute_single_side(
        liab_prev["balance"], liab_curr["balance"],
        liab_prev["rate"], liab_curr["rate"],
    )
    # 负债端利息支出增加会降低 NII，故取负
    nii_delta = a["total_delta"] - l["total_delta"]
    scale = a["scale_effect"] - l["scale_effect"]
    price = a["price_effect"] - l["price_effect"]
    # 结构效应用残差计算，保证三项之和精确等于 nii_delta（避免浮点舍入误差）
    structure = nii_delta - scale - price
    return {
        "nii_delta": round(nii_delta, 4),
        "scale_effect": round(scale, 4),
        "price_effect": round(price, 4),
        "structure_effect": round(structure, 4),
    }
