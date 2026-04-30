# -*- coding: utf-8 -*-
"""
从 yggl 导出 工号(gh)、身份证号(sfzh)，可选附带姓名、科室便于核对。

用法（在 fastapi_backend 目录下）:
  python scripts/export_yggl_gh_sfzh.py [输出路径]
  python scripts/export_yggl_gh_sfzh.py ./yggl_gh_sfzh.xlsx
  python scripts/export_yggl_gh_sfzh.py ./yggl_gh_sfzh.csv

默认输出: fastapi_backend/yggl_gh_sfzh_export.xlsx （若 openpyxl 不可用则 .csv）
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db


def _normalize_sfzh(s):
    return (s or "").strip().replace(" ", "").upper()


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    rows = db.execute_query(
        "SELECT name, gh, sfzh, lsys, zaizhi FROM yggl "
        "WHERE name IS NOT NULL AND TRIM(name) != '' "
        "ORDER BY COALESCE(zaizhi, 0), lsys, gh, name"
    ) or []

    headers = ["姓名", "工号_gh", "身份证号_sfzh", "科室_lsys", "在职_zaizhi0"]
    table = []
    for r in rows:
        table.append([
            (r.get("name") or "").strip(),
            str(r.get("gh") or "").strip(),
            _normalize_sfzh(r.get("sfzh") or ""),
            (r.get("lsys") or "").strip(),
            r.get("zaizhi"),
        ])

    if out_path:
        out_path = os.path.abspath(out_path)
        ext = os.path.splitext(out_path)[1].lower()
    else:
        ext = ".xlsx"

    if out_path and ext == ".csv":
        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(table)
        print(f"已导出 CSV: {out_path} 共 {len(table)} 行")
        return

    if ext not in ("", ".xlsx") and out_path:
        out_path_x = out_path
    elif out_path:
        out_path_x = out_path
    else:
        out_path_x = os.path.join(base_dir, "yggl_gh_sfzh_export.xlsx")

    try:
        import openpyxl
        from openpyxl.styles import Font
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "yggl"
        ws.append(headers)
        for row in table:
            ws.append(row)
        ws.freeze_panes = "A2"
        for cell in ws[1]:
            cell.font = Font(bold=True)
        wb.save(out_path_x)
        wb.close()
        print(f"已导出 Excel: {out_path_x} 共 {len(table)} 行")
    except ImportError:
        fallback = (
            os.path.splitext(out_path_x)[0] + ".csv"
            if out_path_x.lower().endswith(".xlsx")
            else out_path_x + ".csv"
        )
        with open(fallback, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(table)
        print("未安装 openpyxl，已改为导出 CSV:")
        print(f"  {fallback} 共 {len(table)} 行")
        print("安装: pip install openpyxl")


if __name__ == "__main__":
    main()
