# -*- coding: utf-8 -*-
"""
一次性迁移：attendance_suggestions 去掉 suggestion_date，将 start_time/end_time 改为带日期的 DATETIME(0)
若表已是新结构（无 suggestion_date）则跳过。
运行方式（在 fastapi_backend 目录下）: python scripts/migrate_attendance_suggestions_drop_suggestion_date.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db


def main():
    rows = db.execute_query(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'attendance_suggestions' AND COLUMN_NAME = 'suggestion_date'"
    )
    if not rows:
        print("表已是新结构（无 suggestion_date），无需迁移。")
        return
    print("开始迁移：去掉 suggestion_date，start_time/end_time 改为 DATETIME(0) 并带日期...")
    try:
        db.execute_update("ALTER TABLE attendance_suggestions ADD COLUMN start_time_new DATETIME(0) NULL", ())
        db.execute_update("ALTER TABLE attendance_suggestions ADD COLUMN end_time_new DATETIME(0) NULL", ())
        db.execute_update("""
            UPDATE attendance_suggestions
            SET start_time_new = CONCAT(suggestion_date, ' ', TRIM(COALESCE(start_time,'00:00')), CASE WHEN CHAR_LENGTH(TRIM(COALESCE(start_time,'00:00'))) = 5 THEN ':00' ELSE '' END),
                end_time_new = CONCAT(suggestion_date, ' ', TRIM(COALESCE(end_time,'00:00')), CASE WHEN CHAR_LENGTH(TRIM(COALESCE(end_time,'00:00'))) = 5 THEN ':00' ELSE '' END)
            WHERE suggestion_date IS NOT NULL
        """, ())
        db.execute_update("ALTER TABLE attendance_suggestions DROP COLUMN suggestion_date", ())
        db.execute_update("ALTER TABLE attendance_suggestions DROP COLUMN start_time", ())
        db.execute_update("ALTER TABLE attendance_suggestions DROP COLUMN end_time", ())
        db.execute_update("ALTER TABLE attendance_suggestions CHANGE COLUMN start_time_new start_time DATETIME(0) NULL", ())
        db.execute_update("ALTER TABLE attendance_suggestions CHANGE COLUMN end_time_new end_time DATETIME(0) NULL", ())
        print("迁移完成。")
    except Exception as e:
        print(f"迁移失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
