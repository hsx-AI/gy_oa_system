# -*- coding: utf-8 -*-
"""
排班管理 API
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from database import db
from utils.holiday_loader import load_holidays_dict

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/shift", tags=["排班管理"])


def _ensure_tables():
    """首次调用时自动建表"""
    try:
        db.execute_query("SELECT 1 FROM shift_config LIMIT 1")
    except Exception:
        db.execute_update("""
            CREATE TABLE IF NOT EXISTS shift_config (
              id INT AUTO_INCREMENT PRIMARY KEY,
              department VARCHAR(100) NOT NULL,
              workday_night INT NOT NULL DEFAULT 2,
              weekend_day INT NOT NULL DEFAULT 2,
              weekend_night INT NOT NULL DEFAULT 2,
              updated_by VARCHAR(50) NULL,
              updated_at DATETIME NULL,
              UNIQUE KEY uk_dept (department)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    try:
        db.execute_query("SELECT 1 FROM shift_schedule LIMIT 1")
    except Exception:
        db.execute_update("""
            CREATE TABLE IF NOT EXISTS shift_schedule (
              id INT AUTO_INCREMENT PRIMARY KEY,
              department VARCHAR(100) NOT NULL,
              employee_name VARCHAR(50) NOT NULL,
              shift_date DATE NOT NULL,
              shift_type VARCHAR(10) NOT NULL DEFAULT '',
              year INT NOT NULL,
              month INT NOT NULL,
              updated_by VARCHAR(50) NULL,
              updated_at DATETIME NULL,
              UNIQUE KEY uk_emp_date (employee_name, shift_date),
              INDEX idx_dept_ym (department, year, month)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)


def _get_dept_employees(department: str) -> List[str]:
    """获取该科室在职员工列表（排除名字末尾为1的测试账号）"""
    rows = db.execute_query(
        "SELECT name FROM yggl WHERE lsys = %s AND COALESCE(zaizhi,0) = 0 "
        "AND RIGHT(TRIM(name),1) != '1' ORDER BY gh",
        (department,),
    )
    return [(r.get("name") or "").strip() for r in rows if (r.get("name") or "").strip()]


def _month_dates(year: int, month: int) -> List[date]:
    """返回指定月份的所有日期列表"""
    d = date(year, month, 1)
    dates = []
    while d.month == month:
        dates.append(d)
        d += timedelta(days=1)
    return dates


def _is_workday(d: date, holidays: dict) -> bool:
    """判断是否工作日（考虑假期调休）"""
    ds = d.strftime("%Y-%m-%d")
    if ds in holidays:
        ht = holidays[ds]
        if "班" in ht:
            return True
        if "假" in ht or "休" in ht:
            return False
    return d.weekday() < 5


# ==================== 配置 ====================

class ShiftConfigRequest(BaseModel):
    department: str
    workday_night: int = 2
    weekend_day: int = 2
    weekend_night: int = 2
    current_user: str = ""


@router.get("/config")
async def get_shift_config(department: str = Query(...)):
    """获取科室排班配置"""
    _ensure_tables()
    rows = db.execute_query(
        "SELECT workday_night, weekend_day, weekend_night FROM shift_config WHERE department = %s LIMIT 1",
        (department,),
    )
    if rows:
        return {"success": True, "data": rows[0]}
    return {"success": True, "data": {"workday_night": 2, "weekend_day": 2, "weekend_night": 2}}


@router.post("/config")
async def save_shift_config(req: ShiftConfigRequest):
    """保存科室排班配置"""
    _ensure_tables()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = db.execute_query(
        "SELECT id FROM shift_config WHERE department = %s LIMIT 1", (req.department,)
    )
    if existing:
        db.execute_update(
            "UPDATE shift_config SET workday_night=%s, weekend_day=%s, weekend_night=%s, updated_by=%s, updated_at=%s WHERE department=%s",
            (req.workday_night, req.weekend_day, req.weekend_night, req.current_user, now, req.department),
        )
    else:
        db.execute_update(
            "INSERT INTO shift_config (department, workday_night, weekend_day, weekend_night, updated_by, updated_at) VALUES (%s,%s,%s,%s,%s,%s)",
            (req.department, req.workday_night, req.weekend_day, req.weekend_night, req.current_user, now),
        )
    return {"success": True, "message": "配置已保存"}


# ==================== 排班数据 ====================

@router.get("/schedule")
async def get_schedule(
    department: str = Query(...),
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
):
    """获取科室某月排班数据（含员工列表 + 每人每天班次）"""
    _ensure_tables()
    employees = _get_dept_employees(department)
    if not employees:
        return {"success": True, "employees": [], "schedule": {}, "dates": []}
    dates = _month_dates(year, month)
    holidays = load_holidays_dict(str(year))
    date_info = []
    for d in dates:
        ds = d.strftime("%Y-%m-%d")
        wd = _is_workday(d, holidays)
        date_info.append({
            "date": ds,
            "weekday": d.weekday(),
            "isWorkday": wd,
            "label": ["一", "二", "三", "四", "五", "六", "日"][d.weekday()],
        })

    ph = ",".join(["%s"] * len(employees))
    rows = db.execute_query(
        f"SELECT employee_name, shift_date, shift_type FROM shift_schedule "
        f"WHERE department = %s AND year = %s AND month = %s AND employee_name IN ({ph})",
        (department, year, month) + tuple(employees),
    )
    schedule = {}
    for r in rows:
        name = (r.get("employee_name") or "").strip()
        sd = r.get("shift_date")
        if hasattr(sd, "strftime"):
            sd = sd.strftime("%Y-%m-%d")
        else:
            sd = str(sd)[:10] if sd else ""
        st = (r.get("shift_type") or "").strip()
        if name and sd:
            schedule.setdefault(name, {})[sd] = st

    return {"success": True, "employees": employees, "schedule": schedule, "dates": date_info}


class SaveScheduleRequest(BaseModel):
    department: str
    year: int
    month: int
    schedule: dict  # { "张三": { "2026-03-01": "白班", ... }, ... }
    current_user: str = ""


@router.post("/schedule")
async def save_schedule(req: SaveScheduleRequest):
    """保存排班数据（全量覆盖该科室该月）"""
    _ensure_tables()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    params_list = []
    for emp_name, day_map in req.schedule.items():
        for date_str, shift_type in day_map.items():
            params_list.append((
                req.department, emp_name, date_str, shift_type,
                req.year, req.month, req.current_user, now,
                shift_type, req.current_user, now,
            ))
    if not params_list:
        return {"success": True, "message": "无排班数据"}
    sql = (
        "INSERT INTO shift_schedule (department, employee_name, shift_date, shift_type, year, month, updated_by, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE shift_type = %s, updated_by = %s, updated_at = %s"
    )
    try:
        db.execute_many(sql, params_list)
    except Exception as e:
        logger.error("保存排班失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, "message": f"已保存 {len(params_list)} 条排班记录"}


# ==================== 自动排班 ====================

class AutoScheduleRequest(BaseModel):
    department: str
    year: int
    month: int
    current_user: str = ""


@router.post("/auto-schedule")
async def auto_schedule(req: AutoScheduleRequest):
    """
    自动排班：按配置的人数轮流安排夜班和周末班。
    工作日：全员白班，workday_night 人安排夜班（轮流）。
    周末：weekend_day 人白班，weekend_night 人夜班（轮流），其余休息。
    """
    _ensure_tables()
    employees = _get_dept_employees(req.department)
    if not employees:
        return {"success": False, "message": "该科室无在职员工"}
    cfg_rows = db.execute_query(
        "SELECT workday_night, weekend_day, weekend_night FROM shift_config WHERE department = %s LIMIT 1",
        (req.department,),
    )
    cfg = cfg_rows[0] if cfg_rows else {}
    workday_night = int(cfg.get("workday_night") or 2)
    weekend_day = int(cfg.get("weekend_day") or 2)
    weekend_night = int(cfg.get("weekend_night") or 2)

    dates = _month_dates(req.year, req.month)
    holidays = load_holidays_dict(str(req.year))
    n = len(employees)

    schedule = {emp: {} for emp in employees}
    night_idx = 0       # 夜班轮转指针
    weekend_day_idx = 0 # 周末白班轮转指针
    weekend_night_idx = 0  # 周末夜班轮转指针（独立）

    for d in dates:
        ds = d.strftime("%Y-%m-%d")
        wd = _is_workday(d, holidays)
        if wd:
            for emp in employees:
                schedule[emp][ds] = "白班"
            for i in range(min(workday_night, n)):
                emp = employees[(night_idx + i) % n]
                schedule[emp][ds] = "夜班"
            night_idx = (night_idx + workday_night) % n
        else:
            day_count = min(weekend_day, n)
            night_count = min(weekend_night, n)
            day_set = set()
            for i in range(day_count):
                emp = employees[(weekend_day_idx + i) % n]
                schedule[emp][ds] = "白班"
                day_set.add(emp)
            weekend_day_idx = (weekend_day_idx + day_count) % n
            for i in range(night_count):
                emp = employees[(weekend_night_idx + i) % n]
                if emp not in day_set:
                    schedule[emp][ds] = "夜班"
                else:
                    # 如果已安排白班，找下一个没安排的人
                    for j in range(n):
                        candidate = employees[(weekend_night_idx + i + j) % n]
                        if candidate not in day_set and schedule[candidate].get(ds, "休息") != "夜班":
                            schedule[candidate][ds] = "夜班"
                            break
            weekend_night_idx = (weekend_night_idx + night_count) % n
            for emp in employees:
                if ds not in schedule[emp]:
                    schedule[emp][ds] = "休息"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    params_list = []
    for emp_name, day_map in schedule.items():
        for date_str, shift_type in day_map.items():
            params_list.append((
                req.department, emp_name, date_str, shift_type,
                req.year, req.month, req.current_user, now,
                shift_type, req.current_user, now,
            ))
    sql = (
        "INSERT INTO shift_schedule (department, employee_name, shift_date, shift_type, year, month, updated_by, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE shift_type = %s, updated_by = %s, updated_at = %s"
    )
    try:
        db.execute_many(sql, params_list)
    except Exception as e:
        logger.error("自动排班写入失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, "message": f"已自动生成 {len(employees)} 人 {len(dates)} 天排班", "schedule": schedule}


# ==================== 复制上月排班 ====================

class CopyScheduleRequest(BaseModel):
    department: str
    year: int
    month: int
    current_user: str = ""


@router.post("/copy-last-month")
async def copy_last_month(req: CopyScheduleRequest):
    """复制上月排班到本月"""
    _ensure_tables()
    if req.month == 1:
        src_year, src_month = req.year - 1, 12
    else:
        src_year, src_month = req.year, req.month - 1

    rows = db.execute_query(
        "SELECT employee_name, shift_date, shift_type FROM shift_schedule "
        "WHERE department = %s AND year = %s AND month = %s",
        (req.department, src_year, src_month),
    )
    if not rows:
        return {"success": False, "message": "上月无排班记录"}

    src_dates = _month_dates(src_year, src_month)
    dst_dates = _month_dates(req.year, req.month)
    day_count = min(len(src_dates), len(dst_dates))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    src_map = {}
    for r in rows:
        name = (r.get("employee_name") or "").strip()
        sd = r.get("shift_date")
        if hasattr(sd, "strftime"):
            sd = sd.strftime("%Y-%m-%d")
        else:
            sd = str(sd)[:10]
        src_map.setdefault(name, {})[sd] = (r.get("shift_type") or "").strip()

    params_list = []
    for name, day_map in src_map.items():
        for i, src_d in enumerate(src_dates[:day_count]):
            src_ds = src_d.strftime("%Y-%m-%d")
            st = day_map.get(src_ds, "")
            if not st:
                continue
            dst_ds = dst_dates[i].strftime("%Y-%m-%d")
            params_list.append((
                req.department, name, dst_ds, st,
                req.year, req.month, req.current_user, now,
                st, req.current_user, now,
            ))
    if not params_list:
        return {"success": False, "message": "上月排班记录为空"}
    sql = (
        "INSERT INTO shift_schedule (department, employee_name, shift_date, shift_type, year, month, updated_by, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE shift_type = %s, updated_by = %s, updated_at = %s"
    )
    db.execute_many(sql, params_list)
    return {"success": True, "message": f"已复制上月 {len(params_list)} 条排班记录"}


# ==================== 科室列表 ====================

@router.get("/departments")
async def get_departments():
    """获取所有科室列表"""
    rows = db.execute_query(
        "SELECT DISTINCT lsys FROM yggl WHERE lsys IS NOT NULL AND lsys != '' "
        "AND RIGHT(TRIM(lsys),1) != '1' AND TRIM(lsys) != '部办' "
        "AND COALESCE(zaizhi,0) = 0 ORDER BY lsys"
    )
    depts = [(r.get("lsys") or "").strip() for r in rows if (r.get("lsys") or "").strip()]
    return {"success": True, "departments": depts}
