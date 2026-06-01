# -*- coding: utf-8 -*-
"""
为高频查询补充 MySQL 索引。

运行方式：
    python scripts/add_performance_indexes.py

脚本会先检查索引是否已存在，重复执行不会重复创建。
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import db  # noqa: E402


INDEXES = [
    ("yggl", "idx_yggl_name", "`name`(50)", ["name"]),
    ("yggl", "idx_yggl_lsys_zaizhi", "`lsys`(100), `zaizhi`", ["lsys", "zaizhi"]),
    ("yggl", "idx_yggl_gh", "`gh`(50)", ["gh"]),
    ("attendance_records", "idx_att_date_name_dept", "`attendance_date`(20), `employee_name`(50), `department`(100)", ["attendance_date", "employee_name", "department"]),
    ("attendance_records", "idx_att_name_dept_date", "`employee_name`(50), `department`(100), `attendance_date`(20)", ["employee_name", "department", "attendance_date"]),
    ("attendance_suggestions", "idx_sugg_ym_status", "`year`, `month`, `status`", ["year", "month", "status"]),
    ("qj", "idx_qj_approver_status_time", "`spr`(50), `qjzt`, `qjtime`", ["spr", "qjzt", "qjtime"]),
    ("qj", "idx_qj_approver2_status_time", "`spr2`(50), `qjzt`, `qjtime`", ["spr2", "qjzt", "qjtime"]),
    ("qj", "idx_qj_person_period_status", "`xm`(50), `timefrom`, `timeto`, `qjzt`", ["xm", "timefrom", "timeto", "qjzt"]),
    ("jiaban", "idx_jiaban_approver_status_time", "`spr2`(50), `jiabanzt`, `jiabantime`", ["spr2", "jiabanzt", "jiabantime"]),
    ("jiaban", "idx_jiaban_person_period_status", "`xm`(50), `timefrom`, `timeto`, `jiabanzt`", ["xm", "timefrom", "timeto", "jiabanzt"]),
    ("jiaban", "idx_jiaban_person_date_status", "`xm`(50), `timedate`(20), `jiabanzt`", ["xm", "timedate", "jiabanzt"]),
    ("gcsqb", "idx_gcsqb_approver_status_time", "`bld`(50), `bldzt`, `yjcfsj`", ["bld", "bldzt", "yjcfsj"]),
    ("gcsqb", "idx_gcsqb_approver2_status_time", "`szr`(50), `szrzt`, `yjcfsj`", ["szr", "szrzt", "yjcfsj"]),
    ("gcsqb", "idx_gcsqb_person_period_status", "`gcr`(50), `yjcfsj`, `yjfhsj`, `bldzt`, `szrzt`", ["gcr", "yjcfsj", "yjfhsj", "bldzt", "szrzt"]),
    ("hxp", "idx_hxp_name_sl_sj", "`name`(50), `sl`, `sj`", ["name", "sl", "sj"]),
    ("hxp", "idx_hxp_name_read_sj", "`name`(50), `is_read`, `sj`", ["name", "is_read", "sj"]),
]


def index_exists(table_name: str, index_name: str) -> bool:
    rows = db.execute_query(
        """
        SELECT 1
        FROM information_schema.STATISTICS
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND index_name = %s
        LIMIT 1
        """,
        (table_name, index_name),
    )
    return bool(rows)


def table_exists(table_name: str) -> bool:
    rows = db.execute_query(
        """
        SELECT 1
        FROM information_schema.TABLES
        WHERE table_schema = DATABASE()
          AND table_name = %s
        LIMIT 1
        """,
        (table_name,),
    )
    return bool(rows)


def missing_columns(table_name: str, columns: list[str]) -> list[str]:
    rows = db.execute_query(
        """
        SELECT column_name
        FROM information_schema.COLUMNS
        WHERE table_schema = DATABASE()
          AND table_name = %s
        """,
        (table_name,),
    )
    exists = {str(row.get("column_name") or row.get("COLUMN_NAME") or "") for row in rows}
    return [col for col in columns if col not in exists]


def main() -> None:
    created = 0
    skipped = 0
    failed = 0

    for table_name, index_name, columns, required_columns in INDEXES:
        if not table_exists(table_name):
            print(f"[SKIP] table not found: {table_name}")
            skipped += 1
            continue
        missing = missing_columns(table_name, required_columns)
        if missing:
            print(f"[SKIP] {table_name}.{index_name} missing columns: {', '.join(missing)}")
            skipped += 1
            continue
        if index_exists(table_name, index_name):
            print(f"[SKIP] {table_name}.{index_name} exists")
            skipped += 1
            continue

        sql = f"ALTER TABLE `{table_name}` ADD INDEX `{index_name}` ({columns})"
        result = db.execute_update(sql)
        if result >= 0:
            print(f"[OK] {table_name}.{index_name} ({columns})")
            created += 1
        else:
            print(f"[FAIL] {table_name}.{index_name} ({columns})")
            failed += 1

    print(f"Done. created={created}, skipped={skipped}, failed={failed}")


if __name__ == "__main__":
    main()
