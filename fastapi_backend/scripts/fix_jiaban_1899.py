# -*- coding: utf-8 -*-
"""
一次性脚本：将 jiaban 表的 timefrom、timeto 字段中所有 1899 替换为 2025（修复错误日期）
运行方式（在 fastapi_backend 目录下）: python -m scripts.fix_jiaban_1899
或: cd fastapi_backend && python scripts/fix_jiaban_1899.py
"""
import sys
import os

# 使可导入上级目录的 database
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db


def main():
    # 将 timefrom、timeto 中所有 1899 替换为 2025（只更新包含 1899 的行）
    sql = """
        UPDATE jiaban
        SET timefrom = REPLACE(timefrom, '1899', '2025'),
            timeto = REPLACE(timeto, '1899', '2025')
        WHERE timefrom LIKE %s OR timeto LIKE %s
    """
    try:
        n = db.execute_update(sql, ('%1899%', '%1899%'))
        print(f"已更新 jiaban 表 {n} 行（timefrom/timeto 中的 1899 已替换为 2025）")
    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
