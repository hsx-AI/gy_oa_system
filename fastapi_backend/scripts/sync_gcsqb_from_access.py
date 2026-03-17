# -*- coding: utf-8 -*-
"""
从旧系统 Access 数据库将 gcsqb（公出申请表）导入新系统 MySQL。

字段映射（新表列 <- 旧表列）：
  wpdw      <- wpdw
  gcdw      <- gcdw
  gcr       <- gcryxm
  gzh       <- gzh
  wpsj      <- wpsj
  lxdh      <- lxdh
  yjfhsj    <- yjfhsj
  yjcfsj    <- gcsj        （旧 gcsj 同时映射到 yjcfsj 和 gcsj）
  bcgczrs   <- bcgczrs
  xmmc      <- xmmc
  tzdbh     <- tzdbh
  gcdd      <- gcdd
  qkje      <- qkje
  gcrw      <- gcrw
  szr       <- szr
  bld       <- bld
  gcsj      <- gcsj
  sjfhtime  <- fhtime
  bldzt     <- bldzt       （值 3 改为 2，其余不变）
  szrzt     <- szrzt       （值 3 改为 2，其余不变）
  szrpztime <- szrpztime
  bldpztime <- bldpztime

注意事项：
  - 旧表时间字段精度不到秒，新表 DATETIME(0) 需秒，统一补 00:00:00
  - 旧表 gcsj 在新表中同时写入 yjcfsj 和 gcsj

使用：
  cd fastapi_backend
  python scripts/sync_gcsqb_from_access.py [--mdb path/to/report1.mdb] [--dry-run]
"""

import sys
import os
import uuid
import argparse
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database import db


DEFAULT_MDB = os.path.join(os.path.dirname(__file__), "..", "..", "report1.mdb")

# 新表列 -> 旧表列
FIELD_MAP = [
    ("id",        None),           # 新表主键，自动生成 UUID
    ("wpdw",      "wpdw"),
    ("gcdw",      "gcdw"),
    ("gcr",       "gcryxm"),
    ("gzh",       "gzh"),
    ("wpsj",      "wpsj"),
    ("lxdh",      "lxdh"),
    ("yjfhsj",    "yjfhsj"),
    ("yjcfsj",    "gcsj"),       # 旧 gcsj -> 新 yjcfsj
    ("bcgczrs",   "bcgczrs"),
    ("xmmc",      "xmmc"),
    ("tzdbh",     "tzdbh"),
    ("gcdd",      "gcdd"),
    ("qkje",      "qkje"),
    ("gcrw",      "gcrw"),
    ("szr",       "szr"),
    ("bld",       "bld"),
    ("gcsj",      "gcsj"),       # 旧 gcsj -> 新 gcsj
    ("sjfhtime",  "fhtime"),
    ("bldzt",     "bldzt"),      # 值 3 -> 2
    ("szrzt",     "szrzt"),      # 值 3 -> 2
    ("szrpztime", "szrpztime"),
    ("bldpztime", "bldpztime"),
]

# 需要做 3->2 转换的列（新表列名）
STATUS_FIX_COLS = {"bldzt", "szrzt"}

# 时间类列（旧表可能只有日期无秒，需补到 YYYY-MM-DD HH:MM:SS）
TIME_COLS = {"wpsj", "yjfhsj", "yjcfsj", "gcsj", "sjfhtime", "szrpztime", "bldpztime"}


def _fix_datetime(val):
    """将旧表的日期/时间值统一为 'YYYY-MM-DD 00:00:00' 格式字符串。
    若已有时分秒则保留。"""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d") + " 00:00:00"
    s = str(val).strip()
    if not s:
        return None
    # 已经有时分秒
    if len(s) >= 19:
        return s[:19]
    # 只有日期（10 位）
    if len(s) == 10:
        return s + " 00:00:00"
    # 有日期+时分但无秒（如 2025-03-01 08:30）
    if len(s) == 16:
        return s + ":00"
    return s


def _fix_status(val):
    """bldzt / szrzt：旧表 3 -> 新表 2，其余保持不变"""
    if val is None:
        return None
    try:
        v = int(val)
        return 2 if v == 3 else v
    except (TypeError, ValueError):
        return val


def _to_val(val):
    """通用值转换"""
    if val is None:
        return None
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d %H:%M:%S") if isinstance(val, datetime) else val.strftime("%Y-%m-%d")
    return val


def read_gcsqb_from_access(mdb_path: str):
    """从 Access 读取 gcsqb 全表，返回 (旧表列名列表, rows)"""
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
    cursor.execute("SELECT * FROM gcsqb")
    old_cols = [(desc[0].strip() if desc[0] else f"col_{i}").lower() for i, desc in enumerate(cursor.description)]
    rows_raw = cursor.fetchall()
    conn.close()

    # 转为 dict 列表，方便按旧列名取值
    rows = []
    for row in rows_raw:
        d = {}
        for idx, col in enumerate(old_cols):
            d[col] = _to_val(row[idx])
        rows.append(d)

    return old_cols, rows


def main():
    parser = argparse.ArgumentParser(description="从 Access 导入 gcsqb（公出申请表）到 MySQL")
    parser.add_argument("--mdb", default=DEFAULT_MDB, help="Access 数据库路径 (report1.mdb)")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行清空和插入")
    args = parser.parse_args()

    mdb_path = os.path.abspath(args.mdb)

    print("=" * 60)
    print("gcsqb 表导入（公出申请表，旧 Access -> 新 MySQL）")
    print(f"Access 文件: {mdb_path}")
    print("=" * 60)

    if args.dry_run:
        print("\n[dry-run] 预览模式")

    # 1. 从 Access 读取
    print("\n[1/3] 从 Access 读取 gcsqb...")
    try:
        old_cols, old_rows = read_gcsqb_from_access(mdb_path)
    except Exception as e:
        print(f"  错误: {e}")
        sys.exit(1)

    print(f"  旧表列: {old_cols}")
    print(f"  共 {len(old_rows)} 行")

    # 检查映射中的旧列是否都存在
    needed_old = set(old_col for _, old_col in FIELD_MAP)
    missing = needed_old - set(old_cols)
    if missing:
        print(f"\n  [WARNING] 旧表缺少以下列，对应字段将填 NULL: {missing}")

    if not old_rows:
        print("  无数据，退出。")
        return

    # 2. 转换数据
    new_col_names = [new_col for new_col, _ in FIELD_MAP]
    new_rows = []
    for row_dict in old_rows:
        vals = []
        for new_col, old_col in FIELD_MAP:
            if old_col is None:
                vals.append(uuid.uuid4().hex)
                continue
            raw = row_dict.get(old_col)
            if new_col in TIME_COLS:
                raw = _fix_datetime(raw)
            elif new_col in STATUS_FIX_COLS:
                raw = _fix_status(raw)
            vals.append(raw)
        new_rows.append(tuple(vals))

    print(f"\n  映射后新表列: {new_col_names}")

    if args.dry_run:
        print("\n  预览前 3 行:")
        for i, row in enumerate(new_rows[:3]):
            print(f"    {dict(zip(new_col_names, row))}")
        print("\n[dry-run] 未执行清空与插入。")
        return

    # 3. 清空新库 gcsqb
    print("\n[2/3] 清空新库 gcsqb 表...")
    try:
        db.execute_update("SET FOREIGN_KEY_CHECKS = 0", ())
        db.execute_update("TRUNCATE TABLE gcsqb", ())
        db.execute_update("SET FOREIGN_KEY_CHECKS = 1", ())
    except Exception as e:
        if "TRUNCATE" in str(e):
            db.execute_update("DELETE FROM gcsqb", ())
            print("  已用 DELETE 清空（TRUNCATE 不可用时）")
        else:
            raise
    print("  已清空")

    # 4. 插入新库
    print("\n[3/3] 插入新库 gcsqb...")
    cols_quoted = [f"`{c}`" for c in new_col_names]
    placeholders = ", ".join(["%s"] * len(new_col_names))
    sql = f"INSERT INTO gcsqb ({', '.join(cols_quoted)}) VALUES ({placeholders})"

    batch_size = 200
    inserted = 0
    for i in range(0, len(new_rows), batch_size):
        batch = new_rows[i : i + batch_size]
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
        print(f"  已插入 {min(i + batch_size, len(new_rows))}/{len(new_rows)} 条...")

    print(f"\n完成。共插入 {inserted} 条到 gcsqb（公出申请表）。")
    print(f"  字段映射: {len(FIELD_MAP)} 个")
    print(f"  bldzt/szrzt: 旧值 3 已自动改为 2")
    print(f"  时间字段: 无秒的已补为 00:00:00")


if __name__ == "__main__":
    main()
