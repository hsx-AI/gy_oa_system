# -*- coding: utf-8 -*-
"""
从 Excel 导入员工入职时间到 yggl.rcnf
- A列：姓名
- B列：身份证号（与 yggl.sfzh 匹配）
- C列：入厂时间
按身份证号匹配后更新 yggl.rcnf；未在 yggl 中匹配到的身份证号写入 未匹配身份证号_rcnf.txt。

运行方式（在 fastapi_backend 目录下）:
  python scripts/import_employee_rcnf_from_excel.py [Excel文件路径]
  不传路径时默认使用当前目录下的 入厂时间.xls / 入厂时间.xlsx
"""
import sys
import os
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db


def _normalize_date(val):
    """
    将 Excel 或字符串的日期转为 YYYY-MM-DD。
    支持: datetime, date, 纯年份(1900-2100 的整数→只存年份 "YYYY"),
    浮点数(Excel 序列日), 字符串 "YYYY-MM-DD" / "YYYY/MM/DD" / "1990" 等。
    """
    if val is None:
        return None
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, (int, float)):
        # 纯年份：Excel 里 C 列只填 1990、2023 等时，只存年份，不拼 -01-01
        try:
            y = int(val)
            if 1900 <= y <= 2100 and (val == y or abs(val - y) < 1e-6):
                return str(y)
        except (ValueError, TypeError):
            pass
        # Excel 日期序列：1900-01-01 为 1（数值很大时才当序列日）
        try:
            from datetime import timedelta
            base = datetime(1899, 12, 30)  # Excel 序列 1 = 1900-01-01
            d = base + timedelta(days=float(val))
            return d.strftime("%Y-%m-%d")
        except Exception:
            return None
    s = str(val).strip()
    if not s:
        return None
    # 纯 4 位年份（Excel 有时会把年份当文本），只存年份
    if re.match(r"^\d{4}$", s):
        y = int(s)
        if 1900 <= y <= 2100:
            return str(y)
    # 纯数字 8 位 YYYYMMDD
    if re.match(r"^\d{8}$", s):
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    # YYYY-MM-DD 或 YYYY/MM/DD
    for sep in ("-", "/", "."):
        if sep in s and len(s) >= 10:
            parts = s.split(sep)
            if len(parts) >= 3:
                try:
                    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                    if 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31:
                        return f"{y:04d}-{m:02d}-{d:02d}"
                except ValueError:
                    pass
    return None


def read_excel_rows(path: str):
    """读取 Excel，返回 [(姓名, 身份证号, 入厂时间), ...]。A=姓名，B=身份证号，C=入厂时间。"""
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"文件不存在: {path}")

    lower = path.lower()
    if lower.endswith(".xlsx"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
            rows = []
            for row in ws.iter_rows(min_row=1, max_col=3, values_only=True):
                a = row[0] if len(row) > 0 else None
                b = row[1] if len(row) > 1 else None
                c = row[2] if len(row) > 2 else None
                if a is not None or b is not None or c is not None:
                    rows.append((a, b, c))
            wb.close()
            return rows
        except Exception as e:
            raise RuntimeError(f"读取 xlsx 失败: {e}") from e
    if lower.endswith(".xls"):
        try:
            import xlrd
            with xlrd.open_workbook(path) as book:
                sheet = book.sheet_by_index(0)
                rows = []
                for i in range(sheet.nrows):
                    a = sheet.cell_value(i, 0) if sheet.ncols > 0 else None
                    b = sheet.cell_value(i, 1) if sheet.ncols > 1 else None
                    c = sheet.cell_value(i, 2) if sheet.ncols > 2 else None
                    rows.append((a, b, c))
                return rows
        except Exception as e:
            raise RuntimeError(f"读取 xls 失败: {e}") from e
    raise ValueError("仅支持 .xls 或 .xlsx 文件")


def main():
    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
    else:
        base = os.getcwd()
        for name in ("入厂时间.xls", "入厂时间.xlsx"):
            p = os.path.join(base, name)
            if os.path.isfile(p):
                excel_path = p
                break
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            for name in ("入厂时间.xls", "入厂时间.xlsx"):
                p = os.path.join(script_dir, name)
                if os.path.isfile(p):
                    excel_path = p
                    break
            else:
                excel_path = os.path.join(base, "入厂时间.xlsx")

    print(f"读取: {excel_path}")
    rows = read_excel_rows(excel_path)
    if not rows:
        print("表格无数据")
        return

    # 若首行为表头则跳过
    first_a = str(rows[0][0] or "").strip()
    first_b = str(rows[0][1] or "").strip()
    first_c = str(rows[0][2] or "").strip()
    if first_a in ("姓名", "名字", "name") or first_b in ("身份证号", "身份证", "sfzh") or first_c in ("入厂时间", "入职时间", "rcnf"):
        rows = rows[1:]
    if not rows:
        print("除表头外无数据")
        return

    # 收集 (姓名, 身份证号, 入厂时间)，以身份证号为主键匹配，身份证号去空
    triples = []
    for a, b, c in rows:
        sfzh = str(b or "").strip().replace(" ", "")
        if not sfzh:
            continue
        name = str(a or "").strip()
        rcnf = _normalize_date(c)
        triples.append((name, sfzh, rcnf))

    if not triples:
        print("没有有效的「身份证号」列数据")
        return

    updated = 0
    unmapped = []  # 未匹配的 (姓名, 身份证号)

    for name, sfzh, rcnf in triples:
        # 按身份证号匹配 yggl（TRIM + 去空格比较）
        exist = db.execute_query(
            "SELECT name FROM yggl WHERE REPLACE(TRIM(COALESCE(sfzh,'')), ' ', '') = %s LIMIT 1",
            (sfzh,)
        )
        if not exist:
            unmapped.append((name or "", sfzh))
            continue
        db_name = exist[0].get("name")
        # rcnf 可为 DATE 或 VARCHAR；传 YYYY-MM-DD 或 NULL
        n = db.execute_update(
            "UPDATE yggl SET rcnf = %s WHERE name = %s",
            (rcnf, db_name)
        )
        if n > 0:
            updated += n

    print(f"已按身份证号更新 yggl.rcnf：{updated} 条记录。")

    out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_file = os.path.join(out_dir, "未匹配身份证号_rcnf.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        for name, sfzh in unmapped:
            f.write(f"{name}\t{sfzh}\n")
    print(f"未在 yggl 中匹配到的身份证号（共 {len(unmapped)} 个）已写入: {out_file}")
    if unmapped:
        preview = ", ".join(f"{n or '?'}({s})" for n, s in unmapped[:15])
        if len(unmapped) > 15:
            preview += " ..."
        print("未匹配示例:", preview)


if __name__ == "__main__":
    main()
