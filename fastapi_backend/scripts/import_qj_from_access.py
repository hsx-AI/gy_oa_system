# -*- coding: utf-8 -*-
"""
从老 Access 数据库 report1.mdb 的 qj 表导入 timeto < 2025-03-01 的请假记录到 MySQL qj 表。

使用方法:
    cd fastapi_backend
    python scripts/import_qj_from_access.py              # 默认 dry-run，仅统计不写库
    python scripts/import_qj_from_access.py --commit      # 实际写入

Ubuntu 服务器安装依赖:
    sudo apt-get install mdbtools
    pip install pandas

Windows 也可用（自动检测 pyodbc / pandas+subprocess 两种驱动）:
    pip install pyodbc    # Windows 首选
    或
    pip install pandas    # 配合 mdbtools 的跨平台方案

安全说明:
    1. hxp 表不受影响：qj 与 hxp 之间无外键、无触发器；
       hxp 的写操作仅在**审批通过**时由 Python 代码触发，
       本脚本只做 INSERT，不会触发审批流程，也不修改 qjzt 为 4，因此不影响 hxp。
    2. 脚本使用 INSERT IGNORE，若 id 重复则跳过（不覆盖现有数据）。
    3. 建议先 dry-run 确认待导入行数和字段无误后再 --commit。
"""

import sys, os, argparse, uuid, subprocess, shutil
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MDB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "report1.mdb")

MYSQL_QJ_COLUMNS = [
    "id", "bz", "xm", "xb", "jb", "bc", "sfzh", "qjfs",
    "timefrom", "timeto", "jy", "smcl", "smclwj",
    "qjtime", "qjr", "gx", "yj", "spr", "sptime", "sctime", "scr",
    "zw", "content", "qjzt", "tian", "xiaoshi",
    "2j", "spr2", "sp2time", "sp2zt",
    "jibie", "bianhao", "bianhaoweishu",
    "lsys", "timefromdate",
    "hxwc", "hxpxh", "hxps", "hxpsy",
    "bhyy",
]
MYSQL_QJ_COLUMNS_SET = set(MYSQL_QJ_COLUMNS)


# ── 驱动层：自动选择 pyodbc (Windows) 或 mdbtools (Linux/macOS) ──

def _detect_driver():
    """返回 'pyodbc' | 'mdbtools'，优先用 pyodbc（Windows 有 Access Driver 时最快）"""
    try:
        import pyodbc
        drivers = [d for d in pyodbc.drivers() if "Access" in d]
        if drivers:
            return "pyodbc"
    except Exception:
        pass
    if shutil.which("mdb-tables"):
        return "mdbtools"
    raise RuntimeError(
        "未找到可用的 Access 驱动。\n"
        "  Windows: pip install pyodbc 并安装 Microsoft Access Database Engine\n"
        "  Linux:   sudo apt-get install mdbtools && pip install pandas"
    )


def _read_via_pyodbc(mdb_path, table="qj"):
    """用 pyodbc 读取整表，返回 (columns: list[str], rows: list[tuple])"""
    import pyodbc
    abs_path = os.path.abspath(mdb_path)
    conn = pyodbc.connect(
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={abs_path};"
    )
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM [{table}]")
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    return columns, [tuple(r) for r in rows]


def _read_via_mdbtools(mdb_path, table="qj"):
    """
    用 mdb-export (mdbtools) 将表导出为 CSV，再用 pandas 解析。
    返回 (columns: list[str], rows: list[tuple])
    """
    import pandas as pd
    import io

    abs_path = os.path.abspath(mdb_path)
    result = subprocess.run(
        ["mdb-export", abs_path, table],
        capture_output=True, text=True, check=True
    )
    csv_text = result.stdout
    if not csv_text.strip():
        return [], []

    df = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)
    columns = list(df.columns)
    rows = [tuple(row) for row in df.itertuples(index=False, name=None)]
    return columns, rows


def read_access_table(mdb_path, table="qj"):
    """统一入口：自动选驱动，返回 (columns, rows)"""
    driver = _detect_driver()
    print(f"[INFO] 使用驱动: {driver}")
    if driver == "pyodbc":
        return _read_via_pyodbc(mdb_path, table)
    else:
        return _read_via_mdbtools(mdb_path, table)


def _parse_datetime(val):
    """将各种格式的日期时间字符串/datetime 对象统一为 'YYYY-MM-DD HH:MM:SS' 或 None"""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    s = str(val).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S",
                "%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return s


def _parse_cutoff(cutoff_str):
    """将截止日期字符串解析为 datetime 对象"""
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(cutoff_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析截止日期: {cutoff_str}")


def _to_datetime(val):
    """尝试将值转为 datetime，失败返回 None（用于 Python 侧日期过滤）"""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S",
                "%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _safe_int(val):
    """安全转 int（mdbtools 导出的全是字符串）"""
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _safe_float(val):
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


INT_COLUMNS = {"qjzt", "2j", "sp2zt", "bianhaoweishu", "hxwc"}
FLOAT_COLUMNS = {"hxpxh", "hxps", "hxpsy"}
DATETIME_COLUMNS = {"timefrom", "timeto"}


def main():
    parser = argparse.ArgumentParser(description="从 Access report1.mdb 导入 qj 数据到 MySQL")
    parser.add_argument("--commit", action="store_true", help="实际写入（默认 dry-run）")
    parser.add_argument("--mdb", default=MDB_PATH, help="mdb 文件路径")
    parser.add_argument("--cutoff", default="2026-03-01", help="timeto < 此日期的记录才导入")
    args = parser.parse_args()

    from database import db

    print(f"[INFO] MDB 路径: {os.path.abspath(args.mdb)}")
    print(f"[INFO] 截止日期: timeto < {args.cutoff}")
    print(f"[INFO] 模式: {'实际写入' if args.commit else 'DRY-RUN（不写库）'}")
    print()

    cutoff_dt = _parse_cutoff(args.cutoff)

    # ── 1. 读取 Access 全表（mdbtools 不支持 WHERE，Python 侧过滤） ──
    acc_cols, acc_rows = read_access_table(args.mdb, "qj")
    print(f"[INFO] Access qj 列 ({len(acc_cols)}): {acc_cols}")
    common_cols = [c for c in acc_cols if c in MYSQL_QJ_COLUMNS_SET]
    dropped_cols = [c for c in acc_cols if c not in MYSQL_QJ_COLUMNS_SET]
    print(f"[INFO] 共同列 ({len(common_cols)}): {common_cols}")
    if dropped_cols:
        print(f"[WARN] Access 有但 MySQL 无，将舍弃: {dropped_cols}")
    print(f"[INFO] Access qj 全量行数: {len(acc_rows)}")

    # ── 2. Python 侧按 timeto < cutoff 过滤 ──
    col_idx = {c: i for i, c in enumerate(acc_cols)}
    timeto_idx = col_idx.get("timeto")
    if timeto_idx is None:
        print("[ERROR] Access qj 表无 timeto 列，无法过滤。")
        return

    filtered_rows = []
    for row in acc_rows:
        tt = _to_datetime(row[timeto_idx])
        if tt is not None and tt < cutoff_dt:
            filtered_rows.append(row)

    print(f"[INFO] timeto < {args.cutoff} 的记录数: {len(filtered_rows)}")
    if not filtered_rows:
        print("[INFO] 无需导入的数据，退出。")
        return

    # ── 3. 检查 MySQL 已有 id ──
    existing_ids_rows = db.execute_query("SELECT id FROM qj")
    existing_ids = set(str(r["id"]) for r in existing_ids_rows)
    print(f"[INFO] MySQL qj 已有记录数: {len(existing_ids)}")

    # ── 4. 构造待插入数据 ──
    insert_cols = list(common_cols)
    has_id = "id" in col_idx

    to_insert = []
    skipped_dup = 0
    skipped_null_id = 0

    for row in filtered_rows:
        if has_id:
            rid = row[col_idx["id"]]
            if rid is None or str(rid).strip() == "":
                rid = uuid.uuid4().hex
                skipped_null_id += 1
            else:
                rid = str(rid).strip()
        else:
            rid = uuid.uuid4().hex

        if rid in existing_ids:
            skipped_dup += 1
            continue

        vals = {}
        for c in common_cols:
            v = row[col_idx[c]]
            if c == "id":
                v = rid
            elif c in DATETIME_COLUMNS:
                v = _parse_datetime(v)
            elif c in INT_COLUMNS:
                v = _safe_int(v)
            elif c in FLOAT_COLUMNS:
                v = _safe_float(v)
            elif isinstance(v, datetime):
                v = v.strftime("%Y-%m-%d %H:%M:%S")
            vals[c] = v

        to_insert.append(vals)
        existing_ids.add(rid)

    print(f"[INFO] 跳过(id 已存在): {skipped_dup}")
    print(f"[INFO] id 为空自动生成: {skipped_null_id}")
    print(f"[INFO] 待插入: {len(to_insert)}")
    print()

    if not to_insert:
        print("[INFO] 全部已存在，无需导入。")
        return

    print("[PREVIEW] 前 5 条待插入数据:")
    for i, rec in enumerate(to_insert[:5]):
        print(f"  [{i+1}] id={str(rec.get('id','?'))[:12]}... xm={rec.get('xm','?')} "
              f"qjfs={rec.get('qjfs','?')} timefrom={rec.get('timefrom','?')} "
              f"timeto={rec.get('timeto','?')} qjzt={rec.get('qjzt','?')}")
    print()

    if not args.commit:
        print("[DRY-RUN] 加 --commit 参数后实际写入。")
        return

    # ── 5. 批量 INSERT IGNORE ──
    col_names = ", ".join(f"`{c}`" for c in insert_cols)
    placeholders = ", ".join(["%s"] * len(insert_cols))
    insert_sql = f"INSERT IGNORE INTO qj ({col_names}) VALUES ({placeholders})"

    success = 0
    fail = 0
    batch_size = 200
    for batch_start in range(0, len(to_insert), batch_size):
        batch = to_insert[batch_start:batch_start + batch_size]
        for rec in batch:
            params = tuple(rec.get(c) for c in insert_cols)
            try:
                n = db.execute_update(insert_sql, params)
                if n > 0:
                    success += 1
                else:
                    fail += 1
            except Exception as e:
                fail += 1
                if fail <= 5:
                    print(f"[ERROR] id={str(rec.get('id','?'))[:12]}... err={e}")
        print(f"  ... 已处理 {min(batch_start + batch_size, len(to_insert))}/{len(to_insert)}")

    print()
    print(f"[DONE] 成功插入: {success}，失败/跳过: {fail}")
    print(f"[DONE] MySQL qj 表当前记录数: {db.execute_query('SELECT COUNT(*) AS c FROM qj')[0]['c']}")


if __name__ == "__main__":
    main()
