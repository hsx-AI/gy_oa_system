# -*- coding: utf-8 -*-
"""部门公共按摩椅预约"""
import logging
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/massage-chair", tags=["按摩椅预约"])

SLOT_MINUTES = 15
MAX_SLOTS_PER_DAY = 2

# 可预约时段：(开始, 结束)，左闭右开
BOOKING_WINDOWS: List[Tuple[time, time]] = [
    (time(5, 0), time(8, 0)),
    (time(10, 0), time(10, 30)),
    (time(12, 0), time(13, 0)),
    (time(15, 0), time(15, 30)),
    (time(17, 0), time(22, 0)),
]

PERIOD_LABELS = [
    {"key": "early", "label": "早间", "start": "05:00", "end": "08:00"},
    {"key": "morning_break", "label": "上午工间操", "start": "10:00", "end": "10:30"},
    {"key": "lunch", "label": "午休", "start": "12:00", "end": "13:00"},
    {"key": "afternoon_break", "label": "下午工间操", "start": "15:00", "end": "15:30"},
    {"key": "evening", "label": "晚间", "start": "17:00", "end": "22:00"},
]

_INIT_DONE = False


def _ensure_table():
    global _INIT_DONE
    if _INIT_DONE:
        return
    db.execute_update("""
        CREATE TABLE IF NOT EXISTS massage_chair_booking (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booker VARCHAR(50) NOT NULL COMMENT '预约人姓名',
            department VARCHAR(100) DEFAULT '' COMMENT '所属科室',
            booking_date DATE NOT NULL COMMENT '预约日期',
            start_time TIME NOT NULL COMMENT '开始时间',
            end_time TIME NOT NULL COMMENT '结束时间',
            status TINYINT DEFAULT 1 COMMENT '1=有效 0=已取消',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_date (booking_date),
            INDEX idx_booker_date (booker, booking_date),
            INDEX idx_active (booking_date, start_time, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='按摩椅预约'
    """)
    _INIT_DONE = True


def _time_to_str(t: time) -> str:
    return t.strftime("%H:%M")


def _parse_time(s: str) -> time:
    parts = (s or "").strip().split(":")
    if len(parts) < 2:
        raise ValueError("invalid time")
    return time(int(parts[0]), int(parts[1]))


def _generate_all_slots() -> List[Tuple[time, time]]:
    slots: List[Tuple[time, time]] = []
    for win_start, win_end in BOOKING_WINDOWS:
        cur = datetime.combine(date.today(), win_start)
        end_dt = datetime.combine(date.today(), win_end)
        delta = timedelta(minutes=SLOT_MINUTES)
        while cur + delta <= end_dt:
            slot_start = cur.time()
            slot_end = (cur + delta).time()
            slots.append((slot_start, slot_end))
            cur += delta
    return slots


def _period_key_for_time(t: time) -> str:
    for item in PERIOD_LABELS:
        ps = _parse_time(item["start"])
        pe = _parse_time(item["end"])
        if ps <= t < pe:
            return item["key"]
    return "other"


def _slot_is_past(booking_date: date, start: time) -> bool:
    now = datetime.now()
    slot_dt = datetime.combine(booking_date, start)
    return slot_dt <= now


def _get_user_info(name: str) -> Optional[dict]:
    n = (name or "").strip()
    if not n:
        return None
    rows = db.execute_query(
        "SELECT TRIM(name) AS name, TRIM(lsys) AS lsys, COALESCE(zaizhi,0) AS zaizhi "
        "FROM yggl WHERE TRIM(name)=%s LIMIT 1",
        (n,),
    )
    return rows[0] if rows else None


def _assert_active_user(name: str) -> dict:
    user = _get_user_info(name)
    if not user:
        raise HTTPException(status_code=403, detail="用户不存在或未在员工库中登记")
    if int(user.get("zaizhi") or 0) != 0:
        raise HTTPException(status_code=403, detail="仅在职员工可预约按摩椅")
    return user


class BookRequest(BaseModel):
    current_user: str = Field(..., description="当前登录用户姓名")
    booking_date: str = Field(..., description="预约日期 YYYY-MM-DD")
    start_time: str = Field(..., description="开始时间 HH:MM")


class CancelRequest(BaseModel):
    current_user: str = Field(..., description="当前登录用户姓名")
    booking_id: int = Field(..., description="预约记录 ID")


@router.get("/config")
async def get_config():
    """返回预约规则与时段配置（前端展示用）"""
    _ensure_table()
    return {
        "success": True,
        "slotMinutes": SLOT_MINUTES,
        "maxSlotsPerDay": MAX_SLOTS_PER_DAY,
        "periods": PERIOD_LABELS,
        "usageNotice": [
            "本系统为部门公共按摩椅唯一预约渠道，请严格按预约时段到场使用，先到先享，超时须让位。",
            "每人每个自然日最多预约 2 个时段（合计 30 分钟），预约成功后请准时使用，不得占而不用。",
            "可预约时段：早间 5:00–8:00、上午工间操 10:00–10:30、午休 12:00–13:00、下午工间操 15:00–15:30、晚间 17:00–22:00；其余上班工作时间一律禁止使用。",
            "严禁未预约擅自使用；严禁代他人预约后转借他人；严禁连续占用超出预约时长。",
            "使用完毕请关闭电源、整理坐垫，保持设备与周围环境整洁，发现故障请及时反馈科室管理员。",
            "多次违规（未预约使用、占而不用、超时占用等）将暂停预约权限，并通报科室。",
        ],
    }


@router.get("/slots")
async def get_slots(
    booking_date: str = Query(..., description="预约日期 YYYY-MM-DD"),
    current_user: str = Query(..., description="当前登录用户"),
):
    """查询某日全部 15 分钟时段及占用情况"""
    _ensure_table()
    _assert_active_user(current_user)
    try:
        bdate = datetime.strptime(booking_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")

    if bdate < date.today():
        raise HTTPException(status_code=400, detail="不能查询已过期日期")

    booked_rows = db.execute_query(
        "SELECT id, booker, department, start_time, end_time "
        "FROM massage_chair_booking "
        "WHERE booking_date=%s AND status=1",
        (booking_date,),
    )
    booked_map = {}
    for row in booked_rows:
        st = row["start_time"]
        if isinstance(st, timedelta):
            total_sec = int(st.total_seconds())
            st_time = time(total_sec // 3600, (total_sec % 3600) // 60)
        elif isinstance(st, datetime):
            st_time = st.time()
        else:
            st_time = st
        booked_map[_time_to_str(st_time)] = {
            "id": row["id"],
            "booker": row["booker"],
            "department": row.get("department") or "",
            "startTime": _time_to_str(st_time),
        }

    my_count = db.execute_query(
        "SELECT COUNT(*) AS cnt FROM massage_chair_booking "
        "WHERE booking_date=%s AND booker=%s AND status=1",
        (booking_date, current_user.strip()),
    )
    my_booked_today = int((my_count[0]["cnt"] if my_count else 0) or 0)

    my_bookings = db.execute_query(
        "SELECT id, booker, department, start_time, end_time, created_at "
        "FROM massage_chair_booking "
        "WHERE booking_date=%s AND booker=%s AND status=1 "
        "ORDER BY start_time",
        (booking_date, current_user.strip()),
    )

    def _fmt_row(row):
        st = row["start_time"]
        et = row["end_time"]
        if isinstance(st, timedelta):
            total_sec = int(st.total_seconds())
            st_time = time(total_sec // 3600, (total_sec % 3600) // 60)
        elif isinstance(st, datetime):
            st_time = st.time()
        else:
            st_time = st
        if isinstance(et, timedelta):
            total_sec = int(et.total_seconds())
            et_time = time(total_sec // 3600, (total_sec % 3600) // 60)
        elif isinstance(et, datetime):
            et_time = et.time()
        else:
            et_time = et
        return {
            "id": row["id"],
            "booker": row["booker"],
            "department": row.get("department") or "",
            "startTime": _time_to_str(st_time),
            "endTime": _time_to_str(et_time),
            "createdAt": str(row.get("created_at") or ""),
        }

    slots = []
    for slot_start, slot_end in _generate_all_slots():
        key = _time_to_str(slot_start)
        booked = booked_map.get(key)
        is_past = _slot_is_past(bdate, slot_start)
        is_mine = booked and booked["booker"] == current_user.strip()
        slots.append({
            "startTime": key,
            "endTime": _time_to_str(slot_end),
            "period": _period_key_for_time(slot_start),
            "booked": bool(booked),
            "booker": booked["booker"] if booked else "",
            "department": booked["department"] if booked else "",
            "bookingId": booked["id"] if booked else None,
            "isMine": is_mine,
            "isPast": is_past,
            "canBook": not booked and not is_past and my_booked_today < MAX_SLOTS_PER_DAY,
        })

    return {
        "success": True,
        "date": booking_date,
        "slots": slots,
        "myBookedCount": my_booked_today,
        "maxSlotsPerDay": MAX_SLOTS_PER_DAY,
        "myBookings": [_fmt_row(r) for r in my_bookings],
        "periods": PERIOD_LABELS,
    }


@router.post("/book")
async def book_slot(body: BookRequest):
    """预约一个 15 分钟时段"""
    _ensure_table()
    user = _assert_active_user(body.current_user)
    booker = (body.current_user or "").strip()
    try:
        bdate = datetime.strptime(body.booking_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")

    if bdate < date.today():
        raise HTTPException(status_code=400, detail="不能预约已过期日期")

    try:
        start_t = _parse_time(body.start_time)
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="开始时间格式应为 HH:MM")

    valid_starts = {_time_to_str(s[0]) for s in _generate_all_slots()}
    if body.start_time not in valid_starts:
        raise HTTPException(status_code=400, detail="该时段不在可预约范围内")

    if _slot_is_past(bdate, start_t):
        raise HTTPException(status_code=400, detail="不能预约已开始的时段")

    cnt_rows = db.execute_query(
        "SELECT COUNT(*) AS cnt FROM massage_chair_booking "
        "WHERE booking_date=%s AND booker=%s AND status=1",
        (body.booking_date, booker),
    )
    if int((cnt_rows[0]["cnt"] if cnt_rows else 0) or 0) >= MAX_SLOTS_PER_DAY:
        raise HTTPException(status_code=400, detail=f"每人每天最多预约 {MAX_SLOTS_PER_DAY} 个时段（30 分钟）")

    exists = db.execute_query(
        "SELECT id FROM massage_chair_booking "
        "WHERE booking_date=%s AND TIME_FORMAT(start_time, '%%H:%%i')=%s AND status=1 LIMIT 1",
        (body.booking_date, body.start_time),
    )
    if exists:
        raise HTTPException(status_code=409, detail="该时段已被预约")

    end_dt = datetime.combine(date.today(), start_t) + timedelta(minutes=SLOT_MINUTES)
    end_t = end_dt.time()
    department = (user.get("lsys") or "").strip()

    db.execute_update(
        "INSERT INTO massage_chair_booking (booker, department, booking_date, start_time, end_time, status) "
        "VALUES (%s, %s, %s, %s, %s, 1)",
        (booker, department, body.booking_date, body.start_time + ":00", _time_to_str(end_t) + ":00"),
    )

    return {"success": True, "message": f"预约成功：{body.booking_date} {body.start_time}–{_time_to_str(end_t)}"}


@router.post("/cancel")
async def cancel_booking(body: CancelRequest):
    """取消本人预约"""
    _ensure_table()
    booker = (body.current_user or "").strip()
    _assert_active_user(booker)

    rows = db.execute_query(
        "SELECT id, booker, booking_date, start_time, status FROM massage_chair_booking WHERE id=%s LIMIT 1",
        (body.booking_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    row = rows[0]
    if (row.get("booker") or "").strip() != booker:
        raise HTTPException(status_code=403, detail="仅可取消本人的预约")
    if int(row.get("status") or 0) != 1:
        raise HTTPException(status_code=400, detail="该预约已取消")

    st = row["start_time"]
    bdate = row["booking_date"]
    if isinstance(bdate, str):
        bdate = datetime.strptime(bdate[:10], "%Y-%m-%d").date()
    if isinstance(st, timedelta):
        total_sec = int(st.total_seconds())
        st_time = time(total_sec // 3600, (total_sec % 3600) // 60)
    elif isinstance(st, datetime):
        st_time = st.time()
    else:
        st_time = st

    if _slot_is_past(bdate, st_time):
        raise HTTPException(status_code=400, detail="已开始的预约不可取消")

    db.execute_update(
        "UPDATE massage_chair_booking SET status=0 WHERE id=%s",
        (body.booking_id,),
    )
    return {"success": True, "message": "预约已取消"}
