# -*- coding: utf-8 -*-
"""
从 员工编号.xls 导入员工编号到 yggl.gh
- A列：编号（gh）
- B列：姓名（与 yggl.name 匹配）
按姓名匹配后更新 yggl.gh；未在 yggl 中匹配到的姓名写入 未匹配姓名.txt。

运行方式（在 fastapi_backend 目录下）:
  python scripts/import_employee_gh_from_excel.py [Excel文件路径]
  不传路径时默认使用当前目录下的 员工编号.xls
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db


def read_excel_rows(path: str):
    """读取 Excel，返回 [(编号, 姓名), ...]。A列=编号，B列=姓名。"""
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
            for row in ws.iter_rows(min_row=1, max_col=2, values_only=True):
                a, b = (row[0] if len(row) > 0 else None), (row[1] if len(row) > 1 else None)
                if a is not None or b is not None:
                    rows.append((a, b))
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
                    rows.append((a, b))
                return rows
        except Exception as e:
            raise RuntimeError(f"读取 xls 失败: {e}") from e
    raise ValueError("仅支持 .xls 或 .xlsx 文件")


def main():
    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
    else:
        # 默认：先当前目录，再脚本同目录
        base = os.getcwd()
        for name in ("员工编号.xls", "员工编号.xlsx"):
            p = os.path.join(base, name)
            if os.path.isfile(p):
                excel_path = p
                break
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            for name in ("员工编号.xls", "员工编号.xlsx"):
                p = os.path.join(script_dir, name)
                if os.path.isfile(p):
                    excel_path = p
                    break
            else:
                excel_path = os.path.join(base, "员工编号.xls")

    print(f"读取: {excel_path}")
    rows = read_excel_rows(excel_path)
    if not rows:
        print("表格无数据")
        return

    # 若首行为表头则跳过
    first_a, first_b = str(rows[0][0] or "").strip(), str(rows[0][1] or "").strip()
    if first_a in ("编号", "工号", "gh") or first_b in ("姓名", "名字", "name"):
        rows = rows[1:]
    if not rows:
        print("除表头外无数据")
        return

    # 收集 (编号, 姓名)，姓名去空
    pairs = []
    for a, b in rows:
        name = str(b or "").strip()
        if not name:
            continue
        code = str(a or "").strip()
        pairs.append((code, name))

    if not pairs:
        print("没有有效的「姓名」列数据")
        return

    updated = 0
    unmapped = []

    for code, name in pairs:
        # 按姓名匹配 yggl（支持库里 name 有首尾空格：用 TRIM(name)=%s 查）
        exist = db.execute_query(
            "SELECT name FROM yggl WHERE TRIM(name) = %s LIMIT 1", (name,)
        )
        if not exist:
            unmapped.append(name)
            continue
        db_name = exist[0].get("name")  # 使用库中实际 name 做 UPDATE
        n = db.execute_update("UPDATE yggl SET gh = %s WHERE name = %s", (code or "", db_name))
        if n > 0:
            updated += n

    print(f"已按姓名更新 yggl.gh：{updated} 条记录。")

    # 未匹配姓名写入 未匹配姓名.txt（与 fastapi_backend 同目录）
    out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_file = os.path.join(out_dir, "未匹配姓名.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        for name in unmapped:
            f.write(name + "\n")
    print(f"未在 yggl 中匹配到的姓名（共 {len(unmapped)} 个）已写入: {out_file}")
    if unmapped:
        print("未匹配名单:", ", ".join(unmapped[:20]) + (" ..." if len(unmapped) > 20 else ""))


if __name__ == "__main__":
    main()
