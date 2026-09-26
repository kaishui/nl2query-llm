"""SQL 安全校验与只读执行测试（不依赖 opencode / LLM / pytest）。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.sql_guard import validate_sql, execute_readonly, SQLSecurityError


def test_select_allowed():
    validate_sql("SELECT * FROM nii_monthly")


def test_reject_write():
    bad = [
        "INSERT INTO nii_monthly VALUES (1)",
        "UPDATE nii_monthly SET asset_rate = 0",
        "DELETE FROM nii_monthly",
        "DROP TABLE nii_monthly",
    ]
    for sql in bad:
        try:
            validate_sql(sql)
            raise AssertionError(f"应拒绝：{sql}")
        except SQLSecurityError:
            pass


def test_reject_non_select():
    try:
        validate_sql("SELECT 1; DROP TABLE nii_monthly")
        raise AssertionError("应拒绝非纯 SELECT")
    except SQLSecurityError:
        pass


def test_reject_comment_injection():
    try:
        validate_sql("SELECT * FROM nii_monthly -- comment")
        raise AssertionError("应拒绝注释注入")
    except SQLSecurityError:
        pass


def test_reject_multiple_statements():
    try:
        validate_sql("SELECT 1; SELECT 2")
        raise AssertionError("应拒绝多语句")
    except SQLSecurityError:
        pass


def test_execute_readonly_works():
    rows = execute_readonly("SELECT period, branch FROM nii_monthly WHERE period = '2025-01' LIMIT 3")
    assert len(rows) > 0
    assert "period" in rows[0]


def test_execute_readonly_blocks_write():
    try:
        execute_readonly("DELETE FROM nii_monthly")
        raise AssertionError("应拒绝写操作")
    except SQLSecurityError:
        pass


def test_auto_limit_applied():
    rows = execute_readonly("SELECT * FROM nii_monthly")
    assert len(rows) <= 200


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"✓ {name}")
    print("\nSQL 安全校验测试全部通过")
