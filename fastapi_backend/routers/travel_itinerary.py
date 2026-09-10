# -*- coding: utf-8 -*-
"""Travel itinerary from public pusher: departure/arrival Harbin reports."""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database import db
from routers.db_manager import _get_admin1

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/travel-itinerary", tags=["travel-itinerary"])

TABLE_DEPARTURE = "travel_itinerary_departure_harbin"
TABLE_ARRIVAL = "travel_itinerary_arrival_harbin"

REPORT_KEY_TO_TABLE = {
    "departure_harbin": TABLE_DEPARTURE,
    "arrival_harbin": TABLE_ARRIVAL,
}

REPORT_KEY_LABELS = {
    "departure_harbin": "leave Harbin (depart city = Harbin)",
    "arrival_harbin": "arrive Harbin (arrive city = Harbin)",
}

# Chinese headers from export; also support merged-header aliases (*_2 / *_3)
FIELD_ALIASES: Dict[str, Tuple[str, ...]] = {
    "bill_no": ("\u5355\u636e\u7f16\u53f7",),
    "account_dept": ("\u62a5\u8d26\u90e8\u95e8",),
    "reimbursed_by": ("\u62a5\u9500\u4eba",),
    "depart_city": ("\u51fa\u53d1\u57ce\u5e02", "\u51fa\u53d1\u5230\u8fbe\u57ce\u5e02"),
    "arrive_city": ("\u5230\u8fbe\u57ce\u5e02", "\u51fa\u53d1\u5230\u8fbe\u57ce\u5e02_2"),
    "depart_date": ("\u51fa\u53d1\u65e5\u671f", "\u51fa\u53d1\u5230\u8fbe\u79bb\u5f00\u65e5\u671f"),
    "arrive_date": ("\u5230\u8fbe\u65e5\u671f", "\u51fa\u53d1\u5230\u8fbe\u79bb\u5f00\u65e5\u671f_2"),
    "leave_date": ("\u79bb\u5f00\u65e5\u671f", "\u51fa\u53d1\u5230\u8fbe\u79bb\u5f00\u65e5\u671f_3"),
    "trip_days": ("\u51fa\u5dee\u5929\u6570",),
    "transport": ("\u4ea4\u901a\u5de5\u5177",),
    "seat_class": ("\u5750\u5e2d\u7b49\u7ea7",),
    "transport_fee": ("\u4ea4\u901a\u8d39",),
    "hotel_fee": ("\u4f4f\u5bbf\u8d39",),
    "taxi_fee": ("\u6253\u8f66\u8d39",),
    "prepaid_transport": ("\u4ee3\u57ab\u4ea4\u901a\u8d39",),
    "prepaid_hotel": ("\u4ee3\u57ab\u4f4f\u5bbf\u8d39",),
    "prepaid_taxi": ("\u4ee3\u57ab\u6253\u8f66\u8d39",),
    "refund_fee": ("\u9000\u7968\u8d39",),
    "change_fee": ("\u6539\u7b7e\u8d39",),
    "remark": ("\u62a5\u9500\u8bf4\u660e",),
    "fill_date": ("\u586b\u62a5\u65e5\u671f",),
    "bill_status": ("\u5355\u636e\u72b6\u6001",),
}

STATUS_DONE = "\u5b8c\u6210"
HEADER_BILL_NO = "\u5355\u636e\u7f16\u53f7"

_INIT_DONE = False


def _require_admin1(current_user: str) -> None:
    admin1 = _get_admin1()
    if not admin1 or (current_user or "").strip() != admin1:
        raise HTTPException(status_code=403, detail="admin1 only")


def _create_table_sql(table_name: str) -> str:
    return f"""
    CREATE TABLE IF NOT EXISTS `{table_name}` (
        bill_no VARCHAR(64) NOT NULL PRIMARY KEY,
        account_dept VARCHAR(100) DEFAULT '',
        reimbursed_by VARCHAR(100) DEFAULT '',
        depart_city VARCHAR(100) DEFAULT '',
        arrive_city VARCHAR(100) DEFAULT '',
        depart_date DATE DEFAULT NULL,
        arrive_date DATE DEFAULT NULL,
        leave_date DATE DEFAULT NULL,
        trip_days INT DEFAULT NULL,
        transport VARCHAR(50) DEFAULT '',
        seat_class VARCHAR(50) DEFAULT '',
        transport_fee DECIMAL(14, 2) DEFAULT NULL,
        hotel_fee DECIMAL(14, 2) DEFAULT NULL,
        taxi_fee DECIMAL(14, 2) DEFAULT NULL,
        prepaid_transport DECIMAL(14, 2) DEFAULT NULL,
        prepaid_hotel DECIMAL(14, 2) DEFAULT NULL,
        prepaid_taxi DECIMAL(14, 2) DEFAULT NULL,
        refund_fee DECIMAL(14, 2) DEFAULT NULL,
        change_fee DECIMAL(14, 2) DEFAULT NULL,
        remark TEXT,
        fill_date DATE DEFAULT NULL,
        bill_status VARCHAR(32) DEFAULT '',
        source_key VARCHAR(64) DEFAULT '',
        fetched_at VARCHAR(32) DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_bill_status (bill_status),
        INDEX idx_reimbursed_by (reimbursed_by),
        INDEX idx_depart_date (depart_date),
        INDEX idx_fill_date (fill_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """


def ensure_tables() -> None:
    global _INIT_DONE
    if _INIT_DONE:
        return
    try:
        db.execute_update(_create_table_sql(TABLE_DEPARTURE), ())
        db.execute_update(_create_table_sql(TABLE_ARRIVAL), ())
        _INIT_DONE = True
    except Exception as exc:
        logger.warning("create travel itinerary tables failed: %s", exc)


ensure_tables()


def _pick(row: Dict[str, Any], *keys: str) -> str:
    if not row:
        return ""
    for key in keys:
        if key in row and row[key] is not None:
            return str(row[key]).strip()
    normalized = {str(k).strip(): v for k, v in row.items()}
    for key in keys:
        if key in normalized and normalized[key] is not None:
            return str(normalized[key]).strip()
    return ""


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("/", "-").replace(".", "-")[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None


def _parse_money(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "").replace(" ", "")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _row_to_record(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    bill_no = _pick(row, *FIELD_ALIASES["bill_no"])
    if not bill_no or bill_no == HEADER_BILL_NO:
        return None
    return {
        "bill_no": bill_no[:64],
        "account_dept": _pick(row, *FIELD_ALIASES["account_dept"])[:100],
        "reimbursed_by": _pick(row, *FIELD_ALIASES["reimbursed_by"])[:100],
        "depart_city": _pick(row, *FIELD_ALIASES["depart_city"])[:100],
        "arrive_city": _pick(row, *FIELD_ALIASES["arrive_city"])[:100],
        "depart_date": _parse_date(_pick(row, *FIELD_ALIASES["depart_date"])),
        "arrive_date": _parse_date(_pick(row, *FIELD_ALIASES["arrive_date"])),
        "leave_date": _parse_date(_pick(row, *FIELD_ALIASES["leave_date"])),
        "trip_days": _parse_int(_pick(row, *FIELD_ALIASES["trip_days"])),
        "transport": _pick(row, *FIELD_ALIASES["transport"])[:50],
        "seat_class": _pick(row, *FIELD_ALIASES["seat_class"])[:50],
        "transport_fee": _parse_money(_pick(row, *FIELD_ALIASES["transport_fee"])),
        "hotel_fee": _parse_money(_pick(row, *FIELD_ALIASES["hotel_fee"])),
        "taxi_fee": _parse_money(_pick(row, *FIELD_ALIASES["taxi_fee"])),
        "prepaid_transport": _parse_money(_pick(row, *FIELD_ALIASES["prepaid_transport"])),
        "prepaid_hotel": _parse_money(_pick(row, *FIELD_ALIASES["prepaid_hotel"])),
        "prepaid_taxi": _parse_money(_pick(row, *FIELD_ALIASES["prepaid_taxi"])),
        "refund_fee": _parse_money(_pick(row, *FIELD_ALIASES["refund_fee"])),
        "change_fee": _parse_money(_pick(row, *FIELD_ALIASES["change_fee"])),
        "remark": _pick(row, *FIELD_ALIASES["remark"]),
        "fill_date": _parse_date(_pick(row, *FIELD_ALIASES["fill_date"])),
        "bill_status": _pick(row, *FIELD_ALIASES["bill_status"])[:32],
    }


def _is_completed(status: Optional[str]) -> bool:
    return (status or "").strip() == STATUS_DONE


def upsert_report_rows(
    report_key: str,
    rows: List[Dict[str, Any]],
    fetched_at: str = "",
) -> Dict[str, int]:
    ensure_tables()
    table = REPORT_KEY_TO_TABLE.get(report_key)
    if not table:
        return {"inserted": 0, "updated": 0, "skipped_completed": 0, "skipped_invalid": 0}

    inserted = updated = skipped_completed = skipped_invalid = 0
    # Keep completed rows immutable via IF(bill_status = done, old, new)
    sql = f"""
        INSERT INTO `{table}` (
            bill_no, account_dept, reimbursed_by, depart_city, arrive_city,
            depart_date, arrive_date, leave_date, trip_days, transport, seat_class,
            transport_fee, hotel_fee, taxi_fee, prepaid_transport, prepaid_hotel, prepaid_taxi,
            refund_fee, change_fee, remark, fill_date, bill_status, source_key, fetched_at
        ) VALUES (
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s
        )
        ON DUPLICATE KEY UPDATE
            account_dept = IF(bill_status = '{STATUS_DONE}', account_dept, VALUES(account_dept)),
            reimbursed_by = IF(bill_status = '{STATUS_DONE}', reimbursed_by, VALUES(reimbursed_by)),
            depart_city = IF(bill_status = '{STATUS_DONE}', depart_city, VALUES(depart_city)),
            arrive_city = IF(bill_status = '{STATUS_DONE}', arrive_city, VALUES(arrive_city)),
            depart_date = IF(bill_status = '{STATUS_DONE}', depart_date, VALUES(depart_date)),
            arrive_date = IF(bill_status = '{STATUS_DONE}', arrive_date, VALUES(arrive_date)),
            leave_date = IF(bill_status = '{STATUS_DONE}', leave_date, VALUES(leave_date)),
            trip_days = IF(bill_status = '{STATUS_DONE}', trip_days, VALUES(trip_days)),
            transport = IF(bill_status = '{STATUS_DONE}', transport, VALUES(transport)),
            seat_class = IF(bill_status = '{STATUS_DONE}', seat_class, VALUES(seat_class)),
            transport_fee = IF(bill_status = '{STATUS_DONE}', transport_fee, VALUES(transport_fee)),
            hotel_fee = IF(bill_status = '{STATUS_DONE}', hotel_fee, VALUES(hotel_fee)),
            taxi_fee = IF(bill_status = '{STATUS_DONE}', taxi_fee, VALUES(taxi_fee)),
            prepaid_transport = IF(bill_status = '{STATUS_DONE}', prepaid_transport, VALUES(prepaid_transport)),
            prepaid_hotel = IF(bill_status = '{STATUS_DONE}', prepaid_hotel, VALUES(prepaid_hotel)),
            prepaid_taxi = IF(bill_status = '{STATUS_DONE}', prepaid_taxi, VALUES(prepaid_taxi)),
            refund_fee = IF(bill_status = '{STATUS_DONE}', refund_fee, VALUES(refund_fee)),
            change_fee = IF(bill_status = '{STATUS_DONE}', change_fee, VALUES(change_fee)),
            remark = IF(bill_status = '{STATUS_DONE}', remark, VALUES(remark)),
            fill_date = IF(bill_status = '{STATUS_DONE}', fill_date, VALUES(fill_date)),
            bill_status = IF(bill_status = '{STATUS_DONE}', bill_status, VALUES(bill_status)),
            source_key = IF(bill_status = '{STATUS_DONE}', source_key, VALUES(source_key)),
            fetched_at = IF(bill_status = '{STATUS_DONE}', fetched_at, VALUES(fetched_at)),
            updated_at = IF(bill_status = '{STATUS_DONE}', updated_at, CURRENT_TIMESTAMP)
    """

    existing_status: Dict[str, str] = {}
    try:
        existing_rows = db.execute_query(f"SELECT bill_no, bill_status FROM `{table}`", ()) or []
        for r in existing_rows:
            bn = (r.get("bill_no") or "").strip()
            if bn:
                existing_status[bn] = (r.get("bill_status") or "").strip()
    except Exception as exc:
        logger.warning("load existing travel bills failed: %s", exc)

    for raw in rows or []:
        if not isinstance(raw, dict):
            skipped_invalid += 1
            continue
        record = _row_to_record(raw)
        if not record:
            skipped_invalid += 1
            continue
        bill_no = record["bill_no"]
        if _is_completed(existing_status.get(bill_no)):
            skipped_completed += 1
            continue

        params = (
            record["bill_no"],
            record["account_dept"],
            record["reimbursed_by"],
            record["depart_city"],
            record["arrive_city"],
            record["depart_date"],
            record["arrive_date"],
            record["leave_date"],
            record["trip_days"],
            record["transport"],
            record["seat_class"],
            record["transport_fee"],
            record["hotel_fee"],
            record["taxi_fee"],
            record["prepaid_transport"],
            record["prepaid_hotel"],
            record["prepaid_taxi"],
            record["refund_fee"],
            record["change_fee"],
            record["remark"],
            record["fill_date"],
            record["bill_status"],
            report_key,
            (fetched_at or "")[:32],
        )
        try:
            affected = db.execute_update(sql, params)
            if affected < 0:
                skipped_invalid += 1
                continue
            if bill_no in existing_status:
                updated += 1
            else:
                inserted += 1
            existing_status[bill_no] = record["bill_status"]
        except Exception as exc:
            logger.warning("travel upsert failed [%s] %s: %s", report_key, bill_no, exc)
            skipped_invalid += 1

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped_completed": skipped_completed,
        "skipped_invalid": skipped_invalid,
    }


def ingest_pushed_report(report_key: str, data: Any) -> Optional[Dict[str, int]]:
    if report_key not in REPORT_KEY_TO_TABLE:
        return None
    if not isinstance(data, dict):
        return {"inserted": 0, "updated": 0, "skipped_completed": 0, "skipped_invalid": 0}
    rows = data.get("rows") or []
    if not isinstance(rows, list):
        rows = []
    fetched_at = str(data.get("fetchedAt") or data.get("fetched_at") or "")
    return upsert_report_rows(report_key, rows, fetched_at=fetched_at)


class PushTravelReportRequest(BaseModel):
    key: str = Field(..., description="arrival_harbin / departure_harbin")
    data: Any = None
    rows: Optional[List[Dict[str, Any]]] = None
    fetchedAt: str = ""


@router.post("/push")
def push_travel_report(req: PushTravelReportRequest):
    key = (req.key or "").strip()
    if key not in REPORT_KEY_TO_TABLE:
        raise HTTPException(status_code=400, detail="key must be arrival_harbin or departure_harbin")
    data = req.data if isinstance(req.data, dict) else {}
    rows = req.rows if isinstance(req.rows, list) else (data.get("rows") if isinstance(data, dict) else [])
    fetched_at = req.fetchedAt or (data.get("fetchedAt") if isinstance(data, dict) else "") or ""
    stats = upsert_report_rows(key, rows or [], fetched_at=str(fetched_at))
    return {"success": True, "key": key, "stats": stats}


@router.get("/summary")
def travel_summary(current_user: str = Query(...)):
    _require_admin1(current_user)
    ensure_tables()
    items = []
    for key, table in REPORT_KEY_TO_TABLE.items():
        row = db.execute_query(
            f"""
            SELECT COUNT(1) AS total,
                   SUM(CASE WHEN bill_status=%s THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN bill_status!=%s OR bill_status IS NULL OR bill_status='' THEN 1 ELSE 0 END) AS processing,
                   MAX(updated_at) AS latestUpdate
            FROM `{table}`
            """,
            (STATUS_DONE, STATUS_DONE),
        ) or []
        r = row[0] if row else {}
        items.append({
            "key": key,
            "label": (
                "\u79bb\u5f00\u54c8\u5c14\u6ee8\uff08\u51fa\u53d1\u57ce\u5e02=\u54c8\u5c14\u6ee8\uff09"
                if key == "departure_harbin"
                else "\u5230\u8fbe\u54c8\u5c14\u6ee8\uff08\u5230\u8fbe\u57ce\u5e02=\u54c8\u5c14\u6ee8\uff09"
            ),
            "total": int(r.get("total") or 0),
            "completed": int(r.get("completed") or 0),
            "processing": int(r.get("processing") or 0),
            "latestUpdate": str(r.get("latestUpdate") or ""),
        })
    return {"success": True, "items": items}


@router.get("/list")
def list_travel_itinerary(
    current_user: str = Query(...),
    direction: str = Query("departure"),
    keyword: str = Query(""),
    bill_status: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    _require_admin1(current_user)
    ensure_tables()
    direction = (direction or "").strip().lower()
    if direction in ("departure", "departure_harbin", "leave"):
        table = TABLE_DEPARTURE
        key = "departure_harbin"
    elif direction in ("arrival", "arrival_harbin", "arrive"):
        table = TABLE_ARRIVAL
        key = "arrival_harbin"
    else:
        raise HTTPException(status_code=400, detail="direction must be departure or arrival")

    where = ["1=1"]
    params: List[Any] = []
    kw = (keyword or "").strip()
    if kw:
        where.append(
            "(bill_no LIKE %s OR reimbursed_by LIKE %s OR depart_city LIKE %s "
            "OR arrive_city LIKE %s OR remark LIKE %s OR account_dept LIKE %s)"
        )
        like = f"%{kw}%"
        params.extend([like, like, like, like, like, like])
    status = (bill_status or "").strip()
    if status:
        where.append("bill_status = %s")
        params.append(status)
    if (date_from or "").strip():
        where.append("depart_date >= %s")
        params.append(date_from.strip()[:10])
    if (date_to or "").strip():
        where.append("depart_date <= %s")
        params.append(date_to.strip()[:10])

    where_sql = " AND ".join(where)
    count_rows = db.execute_query(
        f"SELECT COUNT(1) AS cnt FROM `{table}` WHERE {where_sql}",
        tuple(params),
    ) or []
    total = int((count_rows[0] or {}).get("cnt") or 0)
    offset = (page - 1) * page_size
    rows = db.execute_query(
        f"""
        SELECT bill_no AS billNo, account_dept AS accountDept, reimbursed_by AS reimbursedBy,
               depart_city AS departCity, arrive_city AS arriveCity,
               DATE_FORMAT(depart_date, '%%Y-%%m-%%d') AS departDate,
               DATE_FORMAT(arrive_date, '%%Y-%%m-%%d') AS arriveDate,
               DATE_FORMAT(leave_date, '%%Y-%%m-%%d') AS leaveDate,
               trip_days AS tripDays, transport, seat_class AS seatClass,
               transport_fee AS transportFee, hotel_fee AS hotelFee, taxi_fee AS taxiFee,
               prepaid_transport AS prepaidTransport, prepaid_hotel AS prepaidHotel,
               prepaid_taxi AS prepaidTaxi, refund_fee AS refundFee, change_fee AS changeFee,
               remark, DATE_FORMAT(fill_date, '%%Y-%%m-%%d') AS fillDate,
               bill_status AS billStatus, fetched_at AS fetchedAt,
               DATE_FORMAT(updated_at, '%%Y-%%m-%%d %%H:%%i:%%s') AS updatedAt
        FROM `{table}`
        WHERE {where_sql}
        ORDER BY COALESCE(depart_date, fill_date) DESC, bill_no DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (page_size, offset),
    ) or []

    return {
        "success": True,
        "direction": key,
        "label": (
            "\u79bb\u5f00\u54c8\u5c14\u6ee8\uff08\u51fa\u53d1\u57ce\u5e02=\u54c8\u5c14\u6ee8\uff09"
            if key == "departure_harbin"
            else "\u5230\u8fbe\u54c8\u5c14\u6ee8\uff08\u5230\u8fbe\u57ce\u5e02=\u54c8\u5c14\u6ee8\uff09"
        ),
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": rows,
    }
