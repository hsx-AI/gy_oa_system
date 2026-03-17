# -*- coding: utf-8 -*-
"""
从旧系统 Access 数据库将 gzh 表全量导入新系统 MySQL。

步骤：
  1. 清空新库 gzh 表
  2. 从 report1.mdb 的 gzh 表读取全部数据（字段与 New 库一致）
  3. 按相同字段全部插入到新库 gzh

使用：
  cd fastapi_backend
  python scripts/sync_gzh_from_access.py [--mdb path/to/report1.mdb] [--dry-run]

  --mdb     Access 数据库路径，默认使用项目根目录下的 report1.mdb
  --dry-run 仅预览，不清空、不插入
"""

import sys
import os
import argparse
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database import db


DEFAULT_MDB = os.path.join(os.path.dirname(__file__), "..", "..", "report1.mdb")


def _to_mysql_val(val):
    """将 Access 读出的值转为 MySQL 可接受的 Python 类型"""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d %H:%M:%S") if isinstance(val, datetime) else val.strftime("%Y-%m-%d")
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return val


def read_table_from_access(mdb_path: str, table_name: str):
    """
    从 Access 读取指定表全部数据。
    返回 (column_names, rows)，rows 为 list of tuple，与 column_names 顺序一致。
    """
    import pyodbc

    if not os.path.isfile(mdb_path):
        raise FileNotFoundError(f"Access 文件不存在: {mdb_path}")

    conn_str = (
        f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};"
        f"DBQ={os.path.abspath(mdb_path)};"
    )
    try:
        conn = pyodbc.connect(conn_str)
    except pyodbc.Error:
        conn_str = (
            f"DRIVER={{Microsoft Access Driver (*.mdb)}};"
            f"DBQ={os.path.abspath(mdb_path)};"
        )
        conn = pyodbc.connect(conn_str)

    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    col_names = [(desc[0].strip() if desc[0] else f"col_{i}").lower() for i, desc in enumerate(cursor.description)]
    rows_raw = cursor.fetchall()
    conn.close()

    rows = []
    for row in rows_raw:
        row_vals = [_to_mysql_val(row[i]) for i in range(len(col_names))]
        rows.append(tuple(row_vals))

    return col_names, rows


def main():
    parser = argparse.ArgumentParser(description="从 Access 全量导入 gzh 到 MySQL")
    parser.add_argument("--mdb", default=DEFAULT_MDB, help="Access 数据库路径 (report1.mdb)")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行清空和插入")
    args = parser.parse_args()

    mdb_path = os.path.abspath(args.mdb)
    table_name = "gzh"

    print("=" * 60)
    print("gzh 表全量导入（旧 Access -> 新 MySQL）")
    print(f"Access 文件: {mdb_path}")
    print("=" * 60)

    if args.dry_run:
        print("\n[dry-run] 预览模式")

    # 1. 从 Access 读取
    print(f"\n[1/3] 从 Access 读取 {table_name}...")
    try:
        col_names, rows = read_table_from_access(mdb_path, table_name)
    except Exception as e:
        print(f"  错误: {e}")
        sys.exit(1)

    print(f"  列: {col_names}")
    print(f"  共 {len(rows)} 行")

    if not rows:
        print("  无数据，退出。")
        return

    if args.dry_run:
        print("\n  预览前 3 行:")
        for i, row in enumerate(rows[:3]):
            print(f"    {dict(zip(col_names, row))}")
        print("\n[dry-run] 未执行清空与插入。")
        return

    # 2. 清空新库 gzh
    print(f"\n[2/3] 清空新库 {table_name} 表...")
    try:
        db.execute_update("SET FOREIGN_KEY_CHECKS = 0", ())
        db.execute_update("TRUNCATE TABLE gzh", ())
        db.execute_update("SET FOREIGN_KEY_CHECKS = 1", ())
    except Exception as e:
        if "TRUNCATE" in str(e):
            db.execute_update("DELETE FROM gzh", ())
            print("  已用 DELETE 清空（TRUNCATE 不可用时）")
        else:
            raise
    print("  已清空")

    # 3. 插入新库
    print(f"\n[3/3] 插入新库 {table_name}...")
    cols_quoted = [f"`{c}`" for c in col_names]
    placeholders = ", ".join(["%s"] * len(col_names))
    sql = f"INSERT INTO gzh ({', '.join(cols_quoted)}) VALUES ({placeholders})"
    batch_size = 200
    inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        try:
            db.execute_many(sql, batch)
            inserted += len(batch)
        except Exception as e:
            print(f"  批量插入失败: {e}，改为逐条插入...")
            for row in batch:
                try:
                    db.execute_update(sql, row)
                    inserted += 1
                except Exception as e2:
                    print(f"  [ERROR] 行 {inserted + 1}: {e2}")
        print(f"  已插入 {min(i + batch_size, len(rows))}/{len(rows)} 条...")

    print(f"\n完成。共插入 {inserted} 条到 {table_name}。")


if __name__ == "__main__":
    main()
