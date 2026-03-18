# -*- coding: utf-8 -*-
"""
第一步：从旧系统 Access 数据库同步换休票到新系统 MySQL hxp 表

步骤：
  1. 清空新库 hxp 表
  2. 从 report1.mdb 的 yggl 表筛选 zaizhi=0 的行，将 (hxp + t2025 + t2026) -> sl，name -> name，sj=今天，ly=老数据库迁移

使用：
  cd fastapi_backend
  python scripts/sync_hxp_from_access.py [--mdb path/to/report1.mdb] [--dry-run]

  --mdb     Access 数据库路径，默认使用项目根目录下的 report1.mdb
  --dry-run 仅预览，不清空、不插入
"""

import sys
import uuid
import os
import argparse
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database import db


# 默认 mdb：OA_system/report1.mdb（相对 fastapi_backend 为 ../report1.mdb）
DEFAULT_MDB = os.path.join(os.path.dirname(__file__), "..", "..", "report1.mdb")


def _ensure_ly_column():
    """确保 hxp 表有 ly 列"""
    try:
        db.execute_update(
            "ALTER TABLE hxp ADD COLUMN ly VARCHAR(200) DEFAULT NULL",
            (),
        )
    except Exception as e:
        if "Duplicate column" in str(e) or "1060" in str(e):
            pass  # 列已存在
        else:
            raise


def clear_hxp():
    """清空 hxp 表"""
    n = db.execute_update("DELETE FROM hxp", ())
    return n


def read_yggl_from_access(mdb_path: str):
    """
    从 Access 读取 yggl 表中 zaizhi=0 的 name, hxp, t2025, t2026。
    返回 list of (name, sl) 其中 sl = hxp + t2025 + t2026 三字段之和。
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
    cursor.execute(
        "SELECT name, hxp, t2025, t2026 FROM yggl WHERE zaizhi = 0"
    )
    rows = cursor.fetchall()
    conn.close()

    def _to_float(v):
        try:
            return float(v) if v is not None else 0
        except (TypeError, ValueError):
            return 0

    out = []
    for row in rows:
        name = (row[0] or "").strip() if row[0] is not None else ""
        if not name:
            continue
        sl = _to_float(row[1]) + _to_float(row[2]) + _to_float(row[3])
        if sl < 0:
            sl = 0
        out.append((name, sl))
    return out


def main():
    parser = argparse.ArgumentParser(description="从 Access 同步换休票到 MySQL hxp 表")
    parser.add_argument("--mdb", default=DEFAULT_MDB, help="Access 数据库路径 (report1.mdb)")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行清空和插入")
    args = parser.parse_args()

    mdb_path = os.path.abspath(args.mdb)
    today = date.today().strftime("%Y-%m-%d")
    ly_val = "老数据库迁移"

    print("=" * 60)
    print("换休票同步脚本（第一步）")
    print(f"Access 文件: {mdb_path}")
    print(f"新库 hxp: sl=旧yggl.(hxp+t2025+t2026), name=旧yggl.name, sj={today}, ly={ly_val}")
    print("=" * 60)

    if args.dry_run:
        print("\n[dry-run] 预览模式")

    # 1. 从 Access 读取
    print("\n[1/3] 从 Access 读取 yggl (zaizhi=0)...")
    try:
        rows = read_yggl_from_access(mdb_path)
    except Exception as e:
        print(f"  错误: {e}")
        sys.exit(1)
    print(f"  共读取 {len(rows)} 条（name 非空且 zaizhi=0）")

    if not rows:
        print("  无数据，退出。")
        return

    # 只同步 sl > 0 的也可以，这里按您要求全部同步（含 sl=0）
    nonzero = sum(1 for _, sl in rows if sl > 0)
    print(f"  其中 sl（hxp+t2025+t2026）> 0 的有 {nonzero} 条")

    if args.dry_run:
        print("\n  预览前 10 条: name -> sl")
        for name, sl in rows[:10]:
            print(f"    {name} -> {sl}")
        if len(rows) > 10:
            print(f"    ... 共 {len(rows)} 条")
        print("\n[dry-run] 未执行清空与插入。")
        return

    # 2. 清空新库 hxp
    print("\n[2/3] 清空新库 hxp 表...")
    _ensure_ly_column()
    deleted = clear_hxp()
    print(f"  已删除 {deleted} 条原有记录")

    # 3. 插入新库（表有 id 则带 id 插入，否则仅 name, sl, sj, ly）
    print("\n[3/3] 插入新库 hxp...")
    params_list = [(name, sl, today, ly_val) for name, sl in rows]
    sql_with_id = "INSERT INTO hxp (id, name, sl, sj, ly) VALUES (%s, %s, %s, %s, %s)"
    sql_no_id = "INSERT INTO hxp (name, sl, sj, ly) VALUES (%s, %s, %s, %s)"
    # 探测表是否有 id 列
    use_id = True
    try:
        db.execute_update(sql_with_id, (uuid.uuid4().hex, params_list[0][0], params_list[0][1], today, ly_val))
        db.execute_update("DELETE FROM hxp WHERE name = %s AND sj = %s AND ly = %s", (params_list[0][0], today, ly_val))
    except Exception as e:
        if "Unknown column 'id'" in str(e) or "1054" in str(e):
            use_id = False
        else:
            raise
    inserted = 0
    if use_id:
        params_with_id = [(uuid.uuid4().hex, name, sl, today, ly_val) for name, sl in rows]
        for i in range(0, len(params_with_id), 200):
            batch = params_with_id[i : i + 200]
            db.execute_many(sql_with_id, batch)
            inserted += len(batch)
            print(f"  已插入 {min(i + 200, len(params_with_id))}/{len(params_with_id)} 条...")
    else:
        for i in range(0, len(params_list), 200):
            batch = params_list[i : i + 200]
            db.execute_many(sql_no_id, batch)
            inserted += len(batch)
            print(f"  已插入 {min(i + 200, len(params_list))}/{len(params_list)} 条...")

    print(f"\n完成。共插入 {inserted} 条换休票记录（sj={today}, ly={ly_val}）。")


if __name__ == "__main__":
    main()
