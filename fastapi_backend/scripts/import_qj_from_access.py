# -*- coding: utf-8 -*-
"""
从老 Access 数据库 report1.mdb 的 qj 表导入 timeto < 2025-03-01 的请假记录到 MySQL qj 表。

使用方法:
    cd fastapi_backend
    python scripts/import_qj_from_access.py              # 默认 dry-run，仅统计不写库
    python scripts/import_qj_from_access.py --commit      # 实际写入

安全说明:
    1. hxp 表不受影响：qj 与 hxp 之间无外键、无触发器；
       hxp 的写操作仅在**审批通过**时由 Python 代码触发，
       本脚本只做 INSERT，不会触发审批流程，也不修改 qjzt 为 4，因此不影响 hxp。
    2. 脚本使用 INSERT IGNORE，若 id 重复则跳过（不覆盖现有数据）。
    3. 建议先 dry-run 确认待导入行数和字段无误后再 --commit。

依赖:
    pip install pyodbc          # 仅此脚本用，用于读 .mdb
"""

import sys, os, argparse, uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MDB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "report1.mdb")

# ── MySQL qj 表接受的列（按 SHOW COLUMNS 结果列出，不含 bhyy —— 老库大概率无此列） ──
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


def connect_access(mdb_path):
    import pyodbc
    abs_path = os.path.abspath(mdb_path)
    conn_str = (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={abs_path};"
    )
    return pyodbc.connect(conn_str)


def get_access_columns(cursor, table="qj"):
    cursor.execute(f"SELECT TOP 1 * FROM [{table}]")
    return [desc[0] for desc in cursor.description]


def main():
    parser = argparse.ArgumentParser(description="从 Access report1.mdb 导入 qj 数据到 MySQL")
    parser.add_argument("--commit", action="store_true", help="实际写入（默认 dry-run）")
    parser.add_argument("--mdb", default=MDB_PATH, help="mdb 文件路径")
    parser.add_argument("--cutoff", default="2025-03-01", help="timeto < 此日期的记录才导入")
    args = parser.parse_args()

    from database import db

    print(f"[INFO] MDB 路径: {os.path.abspath(args.mdb)}")
    print(f"[INFO] 截止日期: timeto < {args.cutoff}")
    print(f"[INFO] 模式: {'实际写入' if args.commit else 'DRY-RUN（不写库）'}")
    print()

    # ── 1. 连接 Access ──
    acc_conn = connect_access(args.mdb)
    acc_cur = acc_conn.cursor()

    # ── 2. 获取 Access qj 列名，取与 MySQL 的交集 ──
    acc_cols = get_access_columns(acc_cur)
    print(f"[INFO] Access qj 列 ({len(acc_cols)}): {acc_cols}")
    common_cols = [c for c in acc_cols if c in MYSQL_QJ_COLUMNS_SET]
    dropped_cols = [c for c in acc_cols if c not in MYSQL_QJ_COLUMNS_SET]
    print(f"[INFO] 共同列 ({len(common_cols)}): {common_cols}")
    if dropped_cols:
        print(f"[WARN] Access 有但 MySQL 无，将舍弃: {dropped_cols}")
    print()

    # ── 3. 查询 Access 数据 ──
    sel_cols = ", ".join(f"[{c}]" for c in acc_cols)
    sql = f"SELECT {sel_cols} FROM qj WHERE timeto < #{args.cutoff}#"
    acc_cur.execute(sql)
    rows = acc_cur.fetchall()
    print(f"[INFO] Access 中 timeto < {args.cutoff} 的记录数: {len(rows)}")
    if not rows:
        print("[INFO] 无需导入的数据，退出。")
        return

    # ── 4. 检查 MySQL 已有 id（避免重复） ──
    existing_ids_rows = db.execute_query("SELECT id FROM qj")
    existing_ids = set(str(r["id"]) for r in existing_ids_rows)
    print(f"[INFO] MySQL qj 已有记录数: {len(existing_ids)}")

    # ── 5. 构造待插入数据 ──
    col_idx = {c: i for i, c in enumerate(acc_cols)}
    insert_cols = list(common_cols)
    has_id = "id" in col_idx

    to_insert = []
    skipped_dup = 0
    skipped_null_id = 0

    for row in rows:
        # 取出 id
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
            if isinstance(v, datetime):
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

    # 预览前5条
    print("[PREVIEW] 前 5 条待插入数据:")
    for i, rec in enumerate(to_insert[:5]):
        print(f"  [{i+1}] id={rec.get('id','?')[:12]}... xm={rec.get('xm','?')} "
              f"qjfs={rec.get('qjfs','?')} timefrom={rec.get('timefrom','?')} "
              f"timeto={rec.get('timeto','?')} qjzt={rec.get('qjzt','?')}")
    print()

    if not args.commit:
        print("[DRY-RUN] 加 --commit 参数后实际写入。")
        acc_conn.close()
        return

    # ── 6. 批量 INSERT IGNORE ──
    # 用反引号包裹列名（2j 等为保留字）
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
                    print(f"[ERROR] id={rec.get('id','?')[:12]}... err={e}")
        print(f"  ... 已处理 {min(batch_start + batch_size, len(to_insert))}/{len(to_insert)}")

    print()
    print(f"[DONE] 成功插入: {success}，失败/跳过: {fail}")
    print(f"[DONE] MySQL qj 表当前记录数: {db.execute_query('SELECT COUNT(*) AS c FROM qj')[0]['c']}")

    acc_conn.close()


if __name__ == "__main__":
    main()
