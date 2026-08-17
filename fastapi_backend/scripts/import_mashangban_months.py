# -*- coding: utf-8 -*-
"""
手动导入工艺码上办月度综合报表（不经过 pusher）。
默认导入当年 1 月到当前月；也可传月份列表。

用法:
  python scripts/import_mashangban_months.py
  python scripts/import_mashangban_months.py 2026-01 2026-02 2026-08
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from routers.mashangban import (  # noqa: E402
    LATEST_EXCEL_NAME,
    _keep_only_latest_excel,
    _parse_workbook,
    _replace_month_data,
    _validate_year_month,
)
from database import db  # noqa: E402

EXPORT_URL = "http://backend.gysc.hec-china.com/wo/workOrder/statics/exportComprehensiveReport"
API_KEY = "Q8s7kP2r9Lz5dFg0bTnXjR4vYc6mShw1GqN3aBuDzE7iJfKp5xVt2yM"


def download(year_month: str) -> bytes:
    resp = requests.get(
        EXPORT_URL,
        params={"yearMonth": year_month, "apiKey": API_KEY},
        timeout=120,
    )
    resp.raise_for_status()
    content = resp.content or b""
    if len(content) < 100:
        raise RuntimeError(f"{year_month} 下载内容过小: {len(content)} bytes")
    ctype = (resp.headers.get("Content-Type") or "").lower()
    if "json" in ctype or content[:1] in (b"{", b"["):
        raise RuntimeError(f"{year_month} 返回非 Excel: {content[:200]!r}")
    return content


def import_one(year_month: str) -> dict:
    year_month = _validate_year_month(year_month)
    content = download(year_month)
    parsed = _parse_workbook(content, year_month)
    if not parsed["dept"] and not parsed["person"] and not parsed["order"]:
        raise RuntimeError(f"{year_month} 未解析到有效数据")
    _replace_month_data(year_month, parsed)
    _keep_only_latest_excel(content)
    dept_n = len(parsed["dept"])
    person_n = len(parsed["person"])
    order_n = len(parsed["order"])
    db.execute_update(
        """
        INSERT INTO mashangban_import_log
          (report_month, file_name, file_size, dept_rows, person_rows, order_rows, status, message)
        VALUES (%s,%s,%s,%s,%s,%s,'ok',%s)
        """,
        (
            year_month,
            LATEST_EXCEL_NAME,
            len(content),
            dept_n,
            person_n,
            order_n,
            f"manual import; dept={dept_n}, person={person_n}, order={order_n}",
        ),
    )
    return {"yearMonth": year_month, "deptRows": dept_n, "personRows": person_n, "orderRows": order_n}


def default_months() -> list[str]:
    # 按需求：2026 年 1–8 月
    return [f"2026-{m:02d}" for m in range(1, 9)]


def main():
    months = sys.argv[1:] or default_months()
    print(f"准备导入月份: {', '.join(months)}")
    ok = 0
    for ym in months:
        try:
            result = import_one(ym)
            ok += 1
            print(
                f"[OK] {result['yearMonth']}: "
                f"dept={result['deptRows']}, person={result['personRows']}, order={result['orderRows']}"
            )
        except Exception as exc:
            print(f"[ERR] {ym}: {exc}")
            db.execute_update(
                """
                INSERT INTO mashangban_import_log
                  (report_month, file_name, file_size, dept_rows, person_rows, order_rows, status, message)
                VALUES (%s,%s,0,0,0,0,'error',%s)
                """,
                (ym, "manual_import", str(exc)[:480]),
            )
    print(f"完成: 成功 {ok}/{len(months)}")
    if ok != len(months):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
