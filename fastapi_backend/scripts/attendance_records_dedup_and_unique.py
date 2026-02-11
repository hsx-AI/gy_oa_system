# -*- coding: utf-8 -*-
"""
考勤记录表去重并添加唯一约束，避免同一文件多次上传产生重复数据
运行方式（在 fastapi_backend 目录下）: python scripts/attendance_records_dedup_and_unique.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db


def main():
    print("开始处理 attendance_records 表去重和唯一约束...")

    # 1. 去重：保留每个 (employee_id, attendance_date) 中 id 最小的一条
    print("\n步骤 1: 去重（保留每个 employee_id + attendance_date 中 id 最小的记录）...")
    try:
        sql_dedup = """
            DELETE t1 FROM attendance_records t1
            INNER JOIN attendance_records t2
            ON t1.employee_id = t2.employee_id 
               AND t1.attendance_date = t2.attendance_date 
               AND t1.id > t2.id
        """
        n = db.execute_update(sql_dedup, ())
        print(f"已删除 {n} 条重复记录")
    except Exception as e:
        print(f"去重失败: {e}")
        sys.exit(1)

    # 2. 检查唯一约束是否已存在
    print("\n步骤 2: 检查唯一约束是否已存在...")
    try:
        check_sql = """
            SELECT COUNT(*) AS cnt 
            FROM information_schema.STATISTICS 
            WHERE table_schema = DATABASE() 
              AND table_name = 'attendance_records' 
              AND index_name = 'uk_employee_date'
        """
        result = db.execute_query(check_sql, ())
        exists = result[0].get("cnt", 0) > 0 if result else False

        if exists:
            print("唯一约束 uk_employee_date 已存在，跳过添加")
        else:
            print("添加唯一约束 uk_employee_date...")
            sql_add_unique = """
                ALTER TABLE attendance_records 
                ADD UNIQUE KEY uk_employee_date (employee_id(100), attendance_date(20))
            """
            db.execute_update(sql_add_unique, ())
            print("唯一约束添加成功")
    except Exception as e:
        if "Duplicate key name" in str(e) or "already exists" in str(e).lower():
            print("唯一约束已存在（可能由其他连接创建），跳过")
        else:
            print(f"添加唯一约束失败: {e}")
            sys.exit(1)

    print("\n处理完成！现在 attendance_records 表已按 (employee_id, attendance_date) 唯一，重复上传会更新而非插入新记录。")


if __name__ == "__main__":
    main()
