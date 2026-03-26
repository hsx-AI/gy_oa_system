# -*- coding: utf-8 -*-
"""
从 Excel 按姓名将企业邮箱写入 yggl.enterprise_email
- A 列：姓名（与 yggl.name 匹配）
- B 列：邮箱地址

需已执行 scripts/add_yggl_enterprise_email.sql 增加字段。

运行方式（在 fastapi_backend 目录下）:
  python scripts/import_yggl_enterprise_email_from_excel.py [Excel路径]
  python scripts/import_yggl_enterprise_email_from_excel.py --dry-run [Excel路径]

不传路径时依次尝试：当前目录、项目根目录下的 address.xlsx
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db


def _norm_cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v)).strip()
    return str(v).strip()


def read_excel_name_email(path: str) -> list[tuple[str, str]]:
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"文件不存在: {path}")

    lower = path.lower()
    if not lower.endswith(".xlsx"):
        raise ValueError("当前仅支持 .xlsx，请将表格另存为 xlsx 或使用 openpyxl 可读格式")

    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        rows: list[tuple[str, str]] = []
        for row in ws.iter_rows(min_row=1, max_col=2, values_only=True):
            a = row[0] if len(row) > 0 else None
            b = row[1] if len(row) > 1 else None
            name = _norm_cell(a)
            email = _norm_cell(b)
            if not name and not email:
                continue
            rows.append((name, email))
        return rows
    finally:
        wb.close()


def _looks_like_header(name: str, email: str) -> bool:
    nl, el = name.lower(), email.lower()
    if name in ("姓名", "名字", "name") or nl == "name":
        return True
    if "邮" in name and "箱" in name:
        return True
    if email in ("邮箱", "邮箱地址", "企业邮箱", "email", "e-mail") or el in ("email", "e-mail"):
        return True
    return False


def default_excel_path() -> str:
    base = os.getcwd()
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(base, "address.xlsx"),
        os.path.normpath(os.path.join(backend, "..", "address.xlsx")),
        os.path.join(backend, "address.xlsx"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return candidates[1]


def main() -> None:
    args = [a for a in sys.argv[1:] if a]
    dry_run = False
    if args and args[0] == "--dry-run":
        dry_run = True
        args = args[1:]
    excel_path = args[0] if args else default_excel_path()

    print(f"读取: {excel_path}")
    rows = read_excel_name_email(excel_path)
    if not rows:
        print("表格无数据")
        return

    if rows and _looks_like_header(rows[0][0], rows[0][1]):
        rows = rows[1:]
    if not rows:
        print("除表头外无数据")
        return

    pairs: list[tuple[str, str]] = []
    for name, email in rows:
        if not name:
            print(f"跳过：姓名为空，邮箱={email!r}")
            continue
        pairs.append((name, email))

    if not pairs:
        print("没有有效的「姓名」行")
        return

    updated = 0
    # 未映射：Excel 里有姓名，但 yggl 中 TRIM(name) 无匹配
    unmapped: list[tuple[str, str]] = []

    for name, email in pairs:
        exist = db.execute_query(
            "SELECT name FROM yggl WHERE TRIM(name) = %s LIMIT 1",
            (name,),
        )
        if not exist:
            unmapped.append((name, email))
            continue
        db_name = exist[0].get("name")
        val = email if email else None
        if dry_run:
            print(f"[dry-run] {db_name!r} -> {val!r}")
            updated += 1
            continue
        n = db.execute_update(
            "UPDATE yggl SET enterprise_email = %s WHERE name = %s",
            (val, db_name),
        )
        if n > 0:
            updated += 1

    mode = "（演练，未写库）" if dry_run else ""
    print(f"处理完成{mode}：匹配并更新 yggl.enterprise_email 共 {updated} 条。")
    print(f"未在 yggl（在职）中匹配到的行数：{len(unmapped)}")

    if unmapped:
        print("\n======== 未映射上的姓名与邮箱（请核对是否与 yggl.name 一致、是否已在库）========")
        for n, e in unmapped:
            print(f"  {n}\t{e}")
        out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out_file = os.path.join(out_dir, "enterprise_email_unmapped.txt")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("姓名\t邮箱\n")
            for n, e in unmapped:
                f.write(f"{n}\t{e}\n")
        print(f"\n以上内容已写入: {out_file}")


if __name__ == "__main__":
    main()
