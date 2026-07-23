# -*- coding: utf-8 -*-
"""为已启用的绩效表增加绩效等级字段，并回填既有数据。"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from database import db  # noqa: E402

RATIOS = (("A", 0.2), ("B+", 0.3), ("B", 0.4), ("C", 0.1))


def grade_counts(total):
    raw = [(name, total * ratio) for name, ratio in RATIOS]
    counts = {name: int(value) for name, value in raw}
    order = {name: index for index, (name, _) in enumerate(RATIOS)}
    for name, _ in sorted(raw, key=lambda item: (item[1] - int(item[1]), -order[item[0]]), reverse=True)[:total - sum(counts.values())]:
        counts[name] += 1
    return counts


def fill_grades():
    groups = db.execute_query("SELECT DISTINCT performance_month, department FROM performance_records")
    for group in groups:
        rows = db.execute_query(
            """SELECT id FROM performance_records WHERE performance_month=%s AND department=%s
               AND rank_no IS NOT NULL ORDER BY rank_no, employee_name""",
            (group["performance_month"], group["department"]),
        )
        counts = grade_counts(len(rows))
        grades = [grade for grade, _ in RATIOS for _ in range(counts[grade])]
        db.execute_update(
            "UPDATE performance_records SET performance_grade=NULL WHERE performance_month=%s AND department=%s",
            (group["performance_month"], group["department"]),
        )
        db.execute_many("UPDATE performance_records SET performance_grade=%s WHERE id=%s", [(grade, row["id"]) for row, grade in zip(rows, grades)])


def main():
    exists = db.execute_query(
        """SELECT 1 FROM information_schema.COLUMNS WHERE table_schema=DATABASE()
           AND table_name='performance_records' AND column_name='performance_grade'"""
    )
    if not exists and db.execute_update("ALTER TABLE performance_records ADD COLUMN performance_grade VARCHAR(4) NULL COMMENT '自动绩效等级：A、B+、B、C；不参与排名时为空' AFTER rank_percent") < 0:
        raise SystemExit("增加绩效等级字段失败")
    fill_grades()
    print("绩效等级字段已就绪，历史绩效等级已回填。")


if __name__ == "__main__":
    main()
