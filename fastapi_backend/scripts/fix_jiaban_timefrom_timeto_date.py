# -*- coding: utf-8 -*-
"""
一次性脚本：将 jiaban 表的 timefrom、timeto 中的日期部分替换为 timedate 的日期
（原数据中日期错误地默认为 2025-12-30，应使用同行的 timedate 的 xxx-xx-xx）
运行方式（在 fastapi_backend 目录下）: python scripts/fix_jiaban_timefrom_timeto_date.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db


def main():
    # 用 timedate 的日期（YYYY-MM-DD）+ timefrom/timeto 的时间部分，覆盖 timefrom、timeto
    sql = """
        UPDATE jiaban
        SET timefrom = CONCAT(DATE_FORMAT(timedate, '%%Y-%%m-%%d'), ' ', TIME(timefrom)),
            timeto = CONCAT(DATE_FORMAT(timedate, '%%Y-%%m-%%d'), ' ', TIME(timeto))
        WHERE timedate IS NOT NULL
          AND timefrom IS NOT NULL AND timefrom != ''
          AND timeto IS NOT NULL AND timeto != ''
    """
    try:
        n = db.execute_update(sql, ())
        print(f"已更新 jiaban 表 {n} 行（timefrom/timeto 的日期已替换为 timedate 的日期）")
    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
