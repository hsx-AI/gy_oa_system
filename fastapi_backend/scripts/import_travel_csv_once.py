# -*- coding: utf-8 -*-
"""One-off: import departure Harbin travel CSV into OA DB."""
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routers.travel_itinerary import TABLE_DEPARTURE, db, upsert_report_rows  # noqa: E402

CSV_DIR = Path(r"f:\xwechat_files\wxid_q7u3d7jnqtkg21_de5d\msg\file\2026-09")
CSV_NAME = "\u90e8\u95e8\u5dee\u65c5\u884c\u7a0b\u660e\u7ec6\u67e5\u8be2 (2).csv"
CSV_PATH = CSV_DIR / CSV_NAME


def decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_csv(path: Path):
    text = decode_bytes(path.read_bytes())
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    matrix = [row for row in csv.reader(io.StringIO(text), dialect)]
    header_idx = 0
    for i, row in enumerate(matrix[:5]):
        joined = ",".join(row)
        if ("\u51fa\u53d1\u57ce\u5e02" in joined) and ("\u5230\u8fbe\u57ce\u5e02" in joined):
            header_idx = i
            break
    columns = [(c or "").strip() for c in matrix[header_idx]]
    used = set()
    cols = []
    for i, name in enumerate(columns):
        base = name or f"col_{i + 1}"
        unique = base
        n = 2
        while unique in used:
            unique = f"{base}_{n}"
            n += 1
        used.add(unique)
        cols.append(unique)

    bill_key = "\u5355\u636e\u7f16\u53f7"
    rows = []
    for raw_row in matrix[header_idx + 1 :]:
        if not any((cell or "").strip() for cell in raw_row):
            continue
        normalized = list(raw_row[: len(cols)]) + [""] * max(0, len(cols) - len(raw_row))
        item = {cols[i]: (normalized[i] or "").strip() for i in range(len(cols))}
        bill_no = item.get(bill_key, "")
        if not bill_no or bill_no == bill_key:
            continue
        rows.append(item)
    return cols, rows


def main():
    path = CSV_PATH
    print("csv:", path)
    print("exists:", path.exists())
    if not path.exists():
        # fallback: find by suffix in dir
        matches = list(CSV_DIR.glob("*(2).csv"))
        print("fallback matches:", [m.name for m in matches])
        if not matches:
            sys.exit(1)
        path = matches[0]

    cols, rows = parse_csv(path)
    print("columns:", cols)
    print("parsed rows:", len(rows))
    if rows:
        print(
            "sample:",
            rows[0].get("\u5355\u636e\u7f16\u53f7"),
            rows[0].get("\u62a5\u9500\u4eba"),
            rows[0].get("\u51fa\u53d1\u57ce\u5e02"),
            rows[0].get("\u5230\u8fbe\u57ce\u5e02"),
            rows[0].get("\u5355\u636e\u72b6\u6001"),
        )

    before = db.execute_query(f"SELECT COUNT(1) AS c FROM `{TABLE_DEPARTURE}`", ()) or [{"c": 0}]
    print("before:", before[0]["c"])

    stats = upsert_report_rows(
        "departure_harbin",
        rows,
        fetched_at="manual-csv-2026-09-10",
    )
    print("stats:", stats)

    after = db.execute_query(f"SELECT COUNT(1) AS c FROM `{TABLE_DEPARTURE}`", ()) or [{"c": 0}]
    done = db.execute_query(
        f"SELECT COUNT(1) AS c FROM `{TABLE_DEPARTURE}` WHERE bill_status=%s",
        ("\u5b8c\u6210",),
    ) or [{"c": 0}]
    print("after:", after[0]["c"], "completed:", done[0]["c"])


if __name__ == "__main__":
    main()
