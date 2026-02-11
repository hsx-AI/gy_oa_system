# -*- coding: utf-8 -*-
"""
将 qj 表的 timefrom、timeto 改为 DATETIME(0)：
- 不存小数秒，避免 .000000
- 用原生类型做时间段比较，减轻压力，便于索引
运行方式（在 fastapi_backend 目录下）: python scripts/alter_qj_timefrom_timeto_datetime.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db


def main():
    for col in ("timefrom", "timeto"):
        sql = f"ALTER TABLE qj MODIFY COLUMN {col} DATETIME(0) NULL DEFAULT NULL"
        try:
            db.execute_update(sql, ())
            print(f"已将 qj.{col} 改为 DATETIME(0)")
        except Exception as e:
            print(f"修改 {col} 失败: {e}")
            sys.exit(1)
    print("完成。qj 表 timefrom、timeto 现已为 DATETIME(0)，比较与索引更高效，且无小数秒。")


if __name__ == "__main__":
    main()
