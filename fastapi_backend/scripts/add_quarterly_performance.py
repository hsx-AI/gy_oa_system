# -*- coding: utf-8 -*-
"""为现有系统补充月度等级人工调整和季度绩效表。"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from database import db  # noqa: E402


def column_exists(table, column):
    return bool(db.execute_query(
        """SELECT 1 FROM information_schema.COLUMNS WHERE table_schema=DATABASE()
           AND table_name=%s AND column_name=%s""", (table, column)
    ))


def main():
    if not column_exists("performance_records", "grade_manual"):
        db.execute_update("ALTER TABLE performance_records ADD COLUMN grade_manual TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1=绩效等级由人工调整' AFTER performance_grade")
    db.execute_update("""
      CREATE TABLE IF NOT EXISTS quarterly_performance_records (
        id BIGINT NOT NULL AUTO_INCREMENT, quarter_start DATE NOT NULL, department VARCHAR(100) NOT NULL,
        employee_name VARCHAR(64) NOT NULL, job_level VARCHAR(100) NULL, monthly_total DECIMAL(12,2) NOT NULL DEFAULT 0,
        work_performance_score DECIMAL(12,2) NULL, ability_score DECIMAL(10,2) NULL,
        behavior_score DECIMAL(10,2) NULL, adjustment_score DECIMAL(10,2) NOT NULL DEFAULT 0,
        total_score DECIMAL(12,2) NULL, rank_no INT NULL, rank_percent DECIMAL(10,6) NULL,
        assessment_grade VARCHAR(4) NULL, grade_manual TINYINT(1) NOT NULL DEFAULT 0, remark VARCHAR(500) NULL,
        created_by VARCHAR(64) NOT NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id), UNIQUE KEY uk_quarter_employee (quarter_start, employee_name),
        KEY idx_quarter_dept (quarter_start, department), KEY idx_quarter_employee (employee_name, quarter_start)
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='员工季度绩效'
    """)
    # 评分项和总分允许为空，以便新建季度先由主任/副主任逐项填写。
    for column in ("work_performance_score", "ability_score", "behavior_score", "total_score"):
        db.execute_update(f"ALTER TABLE quarterly_performance_records MODIFY COLUMN {column} DECIMAL(12,2) NULL")
    print("季度绩效数据表及等级人工调整字段已就绪。")


if __name__ == "__main__":
    main()
