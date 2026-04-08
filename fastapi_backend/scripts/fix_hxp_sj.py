# -*- coding: utf-8 -*-
"""
批量修改 hxp 表：将 ly 为「老数据库迁移」或「表格批量导入」的记录，
sj 统一改为 2026-12-31 00:00:00。

使用：
  cd fastapi_backend
  python scripts/fix_hxp_sj.py [--dry-run]

  --dry-run  仅预览受影响行数，不实际修改
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database import db

TARGET_SJ = "2026-12-31 00:00:00"
TARGET_LY = ("老数据库迁移", "表格批量导入")


def main():
    parser = argparse.ArgumentParser(description="将 hxp 表历史迁移/批量导入记录的 sj 统一改为 2026-12-31")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不修改")
    args = parser.parse_args()

    ph = ",".join(["%s"] * len(TARGET_LY))
    count_sql = f"SELECT COUNT(*) AS cnt FROM hxp WHERE TRIM(ly) IN ({ph})"
    rows = db.execute_query(count_sql, TARGET_LY)
    total = rows[0]["cnt"] if rows else 0

    print(f"匹配条件: ly IN {TARGET_LY}")
    print(f"受影响记录数: {total}")
    print(f"目标 sj 值: {TARGET_SJ}")

    if total == 0:
        print("\n无需修改，退出。")
        return

    preview_sql = (
        f"SELECT id, name, sl, sj, ly FROM hxp WHERE TRIM(ly) IN ({ph}) "
        "ORDER BY ly, name LIMIT 20"
    )
    preview = db.execute_query(preview_sql, TARGET_LY)
    print(f"\n前 {len(preview)} 条预览:")
    print(f"  {'姓名':<10} {'数量':>6}  {'当前sj':<20} {'ly'}")
    print("  " + "-" * 60)
    for r in preview:
        name = (r.get("name") or "").strip()
        sl = r.get("sl") or 0
        sj = str(r.get("sj") or "")[:19]
        ly = (r.get("ly") or "").strip()
        print(f"  {name:<10} {sl:>6}  {sj:<20} {ly}")
    if total > 20:
        print(f"  ... 还有 {total - 20} 条")

    if args.dry_run:
        print("\n[dry-run] 未执行修改。")
        return

    update_sql = f"UPDATE hxp SET sj = %s WHERE TRIM(ly) IN ({ph})"
    affected = db.execute_update(update_sql, (TARGET_SJ,) + TARGET_LY)
    print(f"\n已更新 {affected} 条记录的 sj -> {TARGET_SJ}")


if __name__ == "__main__":
    main()
