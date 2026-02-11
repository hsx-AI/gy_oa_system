# -*- coding: utf-8 -*-
"""
将 jiaban 表的 timefrom、timeto 从 TEXT/VARCHAR 改为 DATETIME(0)：
- 不再存小数秒，避免 .000000
- 用原生类型做时间段比较，减轻压力，便于索引
运行方式（在 fastapi_backend 目录下）: python scripts/alter_jiaban_timefrom_timeto_datetime.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db


def main():
    # DATETIME(0) 表示不保留小数秒；现有字符串如 2025-10-07 10:30:00 或 2025-10-07 10:30:00.000000 会被正确转换
    for col in ("timefrom", "timeto"):
        sql = f"ALTER TABLE jiaban MODIFY COLUMN {col} DATETIME(0) NULL DEFAULT NULL"
        try:
            db.execute_update(sql, ())
            print(f"已将 jiaban.{col} 改为 DATETIME(0)")
        except Exception as e:
            print(f"修改 {col} 失败: {e}")
            sys.exit(1)
    print("完成。timefrom、timeto 现已为 DATETIME(0)，比较与索引更高效，且无小数秒。")


if __name__ == "__main__":
    main()
