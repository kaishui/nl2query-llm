"""冒烟测试：验证数据层、指标口径、归因逻辑（不依赖真实 LLM）。"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db
from app.agent import query_metric, attribute_nii_between
from app.attribution import attribute_nii


def test_db_init():
    conn = db.get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM nii_monthly").fetchone()["c"]
    assert n > 0, "数据表为空"
    print(f"✓ 数据初始化成功，共 {n} 行")


def test_query_metric():
    result = json.loads(query_metric.invoke({"metric": "NII", "period_start": "2025-01", "period_end": "2025-03"}))
    assert "error" not in result, f"查询报错：{result}"
    assert len(result["series"]) == 3, "应有 3 个月的数据"
    assert result["unit"] == "亿元"
    print(f"✓ query_metric(NII) 返回 3 期数据，单位 {result['unit']}")


def test_query_metric_unknown():
    result = json.loads(query_metric.invoke({"metric": "不存在的指标"}))
    assert "error" in result, "未知指标应报错"
    print("✓ query_metric 对未知指标正确报错")


def test_query_metric_alias():
    result = json.loads(query_metric.invoke({"metric": "净利息收入", "period_end": "2025-01"}))
    assert "error" not in result, f"别名解析失败：{result}"
    print("✓ 指标别名「净利息收入」正确解析为 NII")


def test_attribute_nii():
    result = json.loads(attribute_nii_between.invoke({"period_prev": "2025-06", "period_curr": "2025-09"}))
    assert "nii_delta" in result, f"缺少 nii_delta：{result}"
    # 归因三项之和应约等于 nii_delta
    total = result["scale_effect"] + result["price_effect"] + result["structure_effect"]
    assert abs(total - result["nii_delta"]) < 1e-3, "归因三项之和应等于 nii_delta"
    print(f"✓ 归因三效应自洽：nii_delta={result['nii_delta']}，三项和={round(total, 4)}")


def test_attribute_math():
    # 纯量×价分解自洽性
    r = attribute_nii(
        {"balance": 100.0, "rate": 4.0},
        {"balance": 120.0, "rate": 4.5},
        {"balance": 90.0, "rate": 2.0},
        {"balance": 95.0, "rate": 2.2},
    )
    total = r["scale_effect"] + r["price_effect"] + r["structure_effect"]
    assert abs(total - r["nii_delta"]) < 1e-3
    print(f"✓ 归因数学分解自洽（nii_delta={r['nii_delta']}）")


if __name__ == "__main__":
    test_db_init()
    test_query_metric()
    test_query_metric_unknown()
    test_query_metric_alias()
    test_attribute_nii()
    test_attribute_math()
    print("\n全部冒烟测试通过 ✓")
