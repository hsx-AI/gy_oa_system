# -*- coding: utf-8 -*-
"""
从 换休票减去.xlsx 读取 (姓名, 减去数量)，
对 hxp 表中 ly='老数据库迁移' 的记录做 sl 减法。
若减后 sl <= 0，则删除该记录。

使用：
  cd fastapi_backend
  python scripts/subtract_hxp.py [--dry-run]

  --dry-run  仅预览，不实际修改数据库
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import db

DEFAULT_XLSX = os.path.join(os.path.dirname(__file__), "..", "..", "换休票减去.xlsx")
LY_VALUE = "老数据库迁移"


def load_xlsx(path):
    """读取 xlsx：A列=姓名，B列=减去数量，无表头，从第1行开始"""
    try:
        import openpyxl
    except ImportError:
        print("需要 openpyxl：pip install openpyxl")
        sys.exit(1)

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    data = []
    for row in ws.iter_rows(min_row=1, max_col=2, values_only=True):
        name = (str(row[0]).strip() if row[0] is not None else "")
        try:
            amount = float(row[1])
        except (TypeError, ValueError):
            continue
        if name and amount > 0:
            data.append((name, amount))
    wb.close()
    return data


def main():
    parser = argparse.ArgumentParser(description="换休票减法脚本")
    parser.add_argument("--xlsx", default=DEFAULT_XLSX, help="xlsx 文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不修改")
    args = parser.parse_args()

    if not os.path.exists(args.xlsx):
        print(f"文件不存在: {args.xlsx}")
        sys.exit(1)

    entries = load_xlsx(args.xlsx)
    print(f"从 xlsx 读取到 {len(entries)} 条记录")
    print("=" * 60)

    updated = 0
    deleted = 0
    skipped = 0
    skipped_names = []

    for name, subtract in entries:
        rows = db.execute_query(
            "SELECT id, sl FROM hxp WHERE name = %s AND ly = %s",
            (name, LY_VALUE),
        )
        if not rows:
            print(f"  [跳过] {name}（减 {subtract}）：hxp 中无 ly='{LY_VALUE}' 的记录")
            skipped += 1
            skipped_names.append(name)
            continue

        remaining = subtract
        for row in rows:
            if remaining <= 0:
                break
            rid = row.get("id")
            try:
                sl = float(row.get("sl") or 0)
            except (TypeError, ValueError):
                sl = 0
            if sl <= 0:
                continue

            new_sl = sl - remaining
            if new_sl <= 0:
                remaining = -new_sl
                if args.dry_run:
                    print(f"  [预览-删除] {name}: id={rid}, sl={sl} -> 删除 (差值 {remaining})")
                else:
                    db.execute_update("DELETE FROM hxp WHERE id = %s", (rid,))
                    print(f"  [删除] {name}: id={rid}, sl={sl} -> 删除")
                deleted += 1
            else:
                remaining = 0
                if args.dry_run:
                    print(f"  [预览-更新] {name}: id={rid}, sl={sl} -> {new_sl}")
                else:
                    db.execute_update("UPDATE hxp SET sl = %s WHERE id = %s", (new_sl, rid))
                    print(f"  [更新] {name}: id={rid}, sl={sl} -> {new_sl}")
                updated += 1

    print("=" * 60)
    print(f"完成: 更新 {updated} 条, 删除 {deleted} 条, 跳过 {skipped} 人")
    if skipped_names:
        print(f"未映射到的姓名: {', '.join(skipped_names)}")
    if args.dry_run:
        print("（dry-run 模式，未实际修改数据库）")


if __name__ == "__main__":
    main()
