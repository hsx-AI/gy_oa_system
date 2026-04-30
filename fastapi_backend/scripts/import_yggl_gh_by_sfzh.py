# -*- coding: utf-8 -*-
"""
根据身份证号(sfzh) 更新 yggl.gh。

表格列（支持表头别名）：
  - 身份证号 / sfzh / 身份证 → 匹配 yggl.sfzh（会去掉空格、末位 X 大写后与库内比对）
  - 工号 / gh / 编号 → 写入 yggl.gh

用法（在 fastapi_backend 目录下）:
  python scripts/import_yggl_gh_by_sfzh.py <表格路径>
  python scripts/import_yggl_gh_by_sfzh.py ./yggl_gh_sfzh_export.xlsx --dry-run

dry-run：只打印将更新哪些行，不写库。
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db


def normalize_sfzh(s):
    return (s or "").strip().replace(" ", "").upper()


def read_table(path):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    lower = path.lower()

    if lower.endswith(".csv"):
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            r = csv.reader(f)
            return [list(row) for row in r]

    if lower.endswith(".xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = []
        for row in ws.iter_rows(values_only=True):
            rows.append(list(row))
        wb.close()
        return rows

    if lower.endswith(".xls"):
        import xlrd
        with xlrd.open_workbook(path) as book:
            sheet = book.sheet_by_index(0)
            rows = []
            for i in range(sheet.nrows):
                rows.append([sheet.cell_value(i, j) for j in range(sheet.ncols)])
            return rows

    raise ValueError("仅支持 .csv / .xlsx / .xls")


def find_col(headers, aliases):
    hlow = [(str(h or "").strip().lower()) for h in headers]
    for i, hl in enumerate(hlow):
        for a in aliases:
            if hl == a or hl.replace("_", "").replace(" ", "") == a.replace("_", ""):
                return i
        if any(a in hl for a in aliases if len(a) > 1):
            return i
    return None


def parse_pairs(rows):
    if not rows:
        return []

    hdr = [str(x or "").strip() for x in rows[0]]
    i_sfzh = find_col(hdr, ["sfzh", "身份证号", "身份证号码", "身份证"])
    i_gh = find_col(hdr, ["gh", "工号", "编号", "员工编号"])

    if i_sfzh is None or i_gh is None:
        # 无表头：假定 A=sfzh B=gh
        if len(hdr) >= 2 and not any(
            k in "".join(hdr).lower() for k in ("sfzh", "身份证", "工号", "gh")
        ):
            pairs = []
            for row in rows:
                if len(row) <= max(i for i in (0, 1) if True):
                    continue
                s = normalize_sfzh(row[0])
                g = str(row[1] or "").strip()
                if s and g:
                    pairs.append((s, g))
            return pairs

        raise ValueError(
            f"需要表头列：身份证号(sfzh) 与 工号(gh)。当前首行: {hdr}\n"
            "或提供无表头两列：A列身份证、B列工号"
        )

    pairs = []
    for row in rows[1:]:
        while len(row) <= max(i_sfzh, i_gh):
            row.append("")
        s = normalize_sfzh(row[i_sfzh])
        g = str(row[i_gh] or "").strip()
        if not s:
            continue
        pairs.append((s, g))
    return pairs


def main():
    ap = argparse.ArgumentParser(description="按 sfzh 更新 yggl.gh")
    ap.add_argument("path", nargs="?", help="Excel / CSV 路径")
    ap.add_argument("--dry-run", action="store_true", help="不写库，只打印预览")
    args = ap.parse_args()

    base = os.getcwd()
    path = args.path
    if not path:
        for name in ("yggl_gh_sfzh_export.xlsx", "yggl_gh_sfzh_export.csv", "import_gh_by_sfzh.xlsx"):
            p = os.path.join(base, name)
            if os.path.isfile(p):
                path = p
                break
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if not path:
            for name in ("yggl_gh_sfzh_export.xlsx", "import_gh_by_sfzh.xlsx"):
                p = os.path.join(script_dir, name)
                if os.path.isfile(p):
                    path = p
                    break
    if not path:
        ap.error("请指定表格路径")

    rows = read_table(path)
    pairs = parse_pairs(rows)
    if not pairs:
        print("表格中无有效的 (身份证号, 工号) 行")
        return

    # 按 sfzh 去重：后者覆盖前者
    by_sfzh = {}
    for s, g in pairs:
        by_sfzh[s] = g

    updated = 0
    skipped_no_match = []
    skipped_multi = []
    skipped_empty_gh = []
    unchanged = []

    for s, gh in sorted(by_sfzh.items()):
        if not gh:
            skipped_empty_gh.append(s)
            continue
        cand = db.execute_query(
            "SELECT name, gh, sfzh FROM yggl WHERE "
            "REPLACE(UPPER(TRIM(COALESCE(sfzh,''))), ' ', '') = %s",
            (s,),
        )
        if not cand:
            skipped_no_match.append(s)
            continue
        if len(cand) > 1:
            skipped_multi.append((s, [c.get("name") for c in cand]))
            continue
        row = cand[0]
        old_gh = str(row.get("gh") or "").strip()
        if old_gh == gh:
            unchanged.append((row.get("name"), s, gh))
            continue
        if args.dry_run:
            print(f"[dry-run] {row.get('name')} sfzh=...{s[-4:]} gh: {old_gh!r} -> {gh!r}")
            updated += 1
            continue
        db.execute_update(
            "UPDATE yggl SET gh = %s WHERE REPLACE(UPPER(TRIM(COALESCE(sfzh,''))), ' ', '') = %s",
            (gh, s),
        )
        updated += 1

    print(f"表格中有效唯一条目: {len(by_sfzh)}")
    print(f"已更新: {updated}" + (" (dry-run)" if args.dry_run else ""))
    print(f"未匹配到 yggl 行: {len(skipped_no_match)}")
    if skipped_no_match[:5]:
        print("  示例:", skipped_no_match[:5])
    print(f"多条同身份证(需人工处理): {len(skipped_multi)}")
    for s, names in skipped_multi[:5]:
        print(f"  {s[-6:]} -> {names}")
    print(f"工号为空跳过: {len(skipped_empty_gh)}")
    print(f"工号已相同跳过: {len(unchanged)}")


if __name__ == "__main__":
    main()
