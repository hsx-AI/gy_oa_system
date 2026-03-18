# -*- coding: utf-8 -*-
"""
从 Excel 读取 (姓名, 换休票数量)，按姓名映射批量增加到 hxp 表。
A列=姓名，B列=增加数量，无表头，从第1行开始。
sj = 当前时间，ly = '表格批量导入'。

使用：
  cd fastapi_backend
  python scripts/add_hxp_from_xlsx.py [--xlsx path/to/file.xlsx] [--dry-run]

  --xlsx     Excel 文件路径，默认为项目根目录下的 换休票增加.xlsx
  --dry-run  仅预览，不实际修改数据库
"""

import sys
import os
import uuid
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database import db

DEFAULT_XLSX = os.path.join(os.path.dirname(__file__), "..", "..", "换休票增加.xlsx")
LY_VALUE = "表格批量导入"


def load_xlsx(path):
    """读取 xlsx：A列=姓名，B列=增加数量，无表头，从第1行开始"""
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
            amount = round(float(row[1]), 3)
        except (TypeError, ValueError):
            continue
        if name and amount > 0:
            data.append((name, amount))
    wb.close()
    return data


def main():
    parser = argparse.ArgumentParser(description="从 Excel 批量增加换休票")
    parser.add_argument("--xlsx", default=DEFAULT_XLSX, help="xlsx 文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不修改")
    args = parser.parse_args()

    if not os.path.exists(args.xlsx):
        print(f"文件不存在: {args.xlsx}")
        sys.exit(1)

    entries = load_xlsx(args.xlsx)
    print(f"从 xlsx 读取到 {len(entries)} 条记录")
    print("=" * 60)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    added = 0
    skipped = 0
    skipped_names = []

    for name, amount in entries:
        emp = db.execute_query(
            "SELECT name FROM yggl WHERE name = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
            (name,),
        )
        if not emp:
            print(f"  [跳过] {name}（+{amount}）：yggl 中无此在职员工")
            skipped += 1
            skipped_names.append((name, amount))
            continue

        if args.dry_run:
            print(f"  [预览-新增] {name}: +{amount}，sj={now_str}，ly={LY_VALUE}")
        else:
            hxp_id = uuid.uuid4().hex
            db.execute_update(
                "INSERT INTO hxp (id, name, sl, sj, ly) VALUES (%s, %s, %s, %s, %s)",
                (hxp_id, name, amount, now_str, LY_VALUE),
            )
            print(f"  [新增] {name}: +{amount}")
        added += 1

    print("=" * 60)
    print(f"完成: 新增 {added} 条, 跳过 {skipped} 人")
    if skipped_names:
        print(f"未映射到的姓名及数量:")
        for sn, sa in skipped_names:
            print(f"    {sn}  (+{sa})")
    if args.dry_run:
        print("（dry-run 模式，未实际修改数据库）")


if __name__ == "__main__":
    main()
