# -*- coding: utf-8 -*-
"""
排班管理 API
"""
import calendar
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Set
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from database import db
from utils.holiday_loader import load_holidays_for_year

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/shift", tags=["排班管理"])


def _ensure_tables():
    """确保排班相关表存在。

    注意：database.execute_query 在表不存在时内部吞掉异常并返回 []，不会向外抛，
    因此不能用「先 SELECT 再 CREATE」的 try/except 判断；应直接 CREATE TABLE IF NOT EXISTS。
    """
    db.execute_update("""
        CREATE TABLE IF NOT EXISTS shift_config (
          id INT AUTO_INCREMENT PRIMARY KEY,
          department VARCHAR(100) NOT NULL,
          workday_day INT NOT NULL DEFAULT 2,
          workday_night INT NOT NULL DEFAULT 2,
          weekend_day INT NOT NULL DEFAULT 2,
          weekend_night INT NOT NULL DEFAULT 2,
          updated_by VARCHAR(50) NULL,
          updated_at DATETIME NULL,
          UNIQUE KEY uk_dept (department)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    # 极旧库在增加 workday_day 前已建过 shift_config 时补列
    col_rows = db.execute_query(
        "SELECT 1 FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'shift_config' AND COLUMN_NAME = 'workday_day' "
        "LIMIT 1"
    )
    if not col_rows:
        db.execute_update(
            "ALTER TABLE shift_config ADD COLUMN workday_day INT NOT NULL DEFAULT 2 AFTER department"
        )
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
    db.execute_update("""
        CREATE TABLE IF NOT EXISTS shift_day_plan (
          id INT AUTO_INCREMENT PRIMARY KEY,
          department VARCHAR(100) NOT NULL,
          plan_date DATE NOT NULL,
          content TEXT NULL,
          updated_by VARCHAR(50) NULL,
          updated_at DATETIME NULL,
          UNIQUE KEY uk_dept_plan_date (department, plan_date),
          INDEX idx_dept_date (department, plan_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    db.execute_update("""
        CREATE TABLE IF NOT EXISTS shift_day_lock (
          id INT AUTO_INCREMENT PRIMARY KEY,
          department VARCHAR(100) NOT NULL,
          lock_date DATE NOT NULL,
          is_open TINYINT(1) NOT NULL DEFAULT 0,
          opened_by VARCHAR(50) NULL,
          opened_at DATETIME NULL,
          UNIQUE KEY uk_dept_lock_date (department, lock_date)
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


def _parse_iso_date(s: str) -> Optional[date]:
    if not s:
        return None
    s = str(s).strip()[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _daterange(start: date, end: date) -> List[date]:
    out = []
    d = start
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def _prev_month_same_day(d: date) -> date:
    """目标日在上月同一天（上月无该日则取上月最后一天）"""
    if d.month == 1:
        y, m = d.year - 1, 12
    else:
        y, m = d.year, d.month - 1
    last = calendar.monthrange(y, m)[1]
    day = min(d.day, last)
    return date(y, m, day)


def _holiday_map_for_years(years: Set[int]) -> dict:
    holiday_by_date = {}
    for y in years:
        for r in load_holidays_for_year(str(y)):
            nk = _normalize_date_key(r.get("date"))
            if nk:
                holiday_by_date[nk] = {
                    "type": (r.get("type") or "").strip(),
                    "festival": (r.get("festival") or "").strip() if r.get("festival") is not None else "",
                }
    return holiday_by_date


def _normalize_date_key(val) -> str:
    """将 holiday 表 date 字段规范为 YYYY-MM-DD，便于与排班日期对齐"""
    if val is None:
        return ""
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip().replace("/", "-").split()[0]
    if not s:
        return ""
    parts = [p for p in s.split("-") if p != ""]
    if len(parts) >= 3:
        try:
            y, mo, da = int(parts[0]), int(parts[1]), int(parts[2])
            return date(y, mo, da).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    return s[:10]


def _holiday_header_mark(holiday_type: str, festival: str) -> str:
    """表头短标记：调休上班 / 节假日"""
    ht = (holiday_type or "").strip()
    fest = (festival or "").strip()
    if "班" in ht:
        return "班"
    if fest:
        return fest[:4] if len(fest) > 4 else fest
    if "假" in ht or "休" in ht:
        return "休"
    return ht[:3] if ht else ""


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


def _is_manager_of_dept(name: str, department: str) -> bool:
    """判断用户是否为指定科室的管理人员（组长/主任/副主任）"""
    if not name or not department:
        return False
    rows = db.execute_query(
        "SELECT jb, lsys FROM yggl WHERE TRIM(name) = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
        (name.strip(),),
    )
    if not rows:
        return False
    jb = (rows[0].get("jb") or "").strip()
    dept = (rows[0].get("lsys") or "").strip()
    return ("组长" in jb or "主任" in jb) and dept == department


def _is_dept_member(name: str, department: str) -> bool:
    """是否为该科室在职员工（含管理人员）"""
    if not name or not department:
        return False
    rows = db.execute_query(
        "SELECT 1 FROM yggl WHERE TRIM(name) = %s AND TRIM(lsys) = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
        (name.strip(), department.strip()),
    )
    return bool(rows)


# ==================== 日期开放 / 锁定 ====================

class SetDayLocksRequest(BaseModel):
    department: str
    dates: List[str]
    is_open: bool
    current_user: str = ""


@router.post("/day-locks")
async def set_day_locks(req: SetDayLocksRequest):
    """管理人员设置日期开放/锁定"""
    _ensure_tables()
    if not _is_manager_of_dept(req.current_user, req.department):
        raise HTTPException(status_code=403, detail="仅本科室管理人员可操作排班开放权限")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cnt = 0
    for date_str in req.dates:
        d = _parse_iso_date(date_str)
        if not d:
            continue
        ds = d.strftime("%Y-%m-%d")
        if req.is_open:
            db.execute_update(
                "INSERT INTO shift_day_lock (department, lock_date, is_open, opened_by, opened_at) "
                "VALUES (%s, %s, 1, %s, %s) "
                "ON DUPLICATE KEY UPDATE is_open = 1, opened_by = %s, opened_at = %s",
                (req.department, ds, req.current_user, now, req.current_user, now),
            )
        else:
            db.execute_update(
                "UPDATE shift_day_lock SET is_open = 0, opened_by = %s, opened_at = %s "
                "WHERE department = %s AND lock_date = %s",
                (req.current_user, now, req.department, ds),
            )
        cnt += 1
    action = "解锁" if req.is_open else "锁定"
    return {"success": True, "message": f"已{action} {cnt} 天排班权限"}


# ==================== 配置 ====================

class ShiftConfigRequest(BaseModel):
    department: str
    workday_day: int = 2
    workday_night: int = 2
    weekend_day: int = 2
    weekend_night: int = 2
    current_user: str = ""


@router.get("/config")
async def get_shift_config(department: str = Query(...)):
    """获取科室排班配置"""
    _ensure_tables()
    rows = db.execute_query(
        "SELECT workday_day, workday_night, weekend_day, weekend_night FROM shift_config WHERE department = %s LIMIT 1",
        (department,),
    )
    if rows:
        return {"success": True, "data": rows[0]}
    return {"success": True, "data": {"workday_day": 2, "workday_night": 2, "weekend_day": 2, "weekend_night": 2}}


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
            "UPDATE shift_config SET workday_day=%s, workday_night=%s, weekend_day=%s, weekend_night=%s, updated_by=%s, updated_at=%s WHERE department=%s",
            (req.workday_day, req.workday_night, req.weekend_day, req.weekend_night, req.current_user, now, req.department),
        )
    else:
        db.execute_update(
            "INSERT INTO shift_config (department, workday_day, workday_night, weekend_day, weekend_night, updated_by, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (req.department, req.workday_day, req.workday_night, req.weekend_day, req.weekend_night, req.current_user, now),
        )
    return {"success": True, "message": "配置已保存"}


# ==================== 排班数据 ====================

@router.get("/schedule")
async def get_schedule(
    department: str = Query(...),
    start_date: Optional[str] = Query(None, description="起始日 YYYY-MM-DD，与 end_date 成对使用"),
    end_date: Optional[str] = Query(None, description="结束日 YYYY-MM-DD，含当日"),
    year: Optional[int] = Query(None, description="与 month 成对，整月模式（兼容旧接口）"),
    month: Optional[int] = Query(None, ge=1, le=12),
):
    """获取科室排班：按日期区间（推荐）或整月。"""
    _ensure_tables()
    employees = _get_dept_employees(department)
    if not employees:
        return {"success": True, "employees": [], "schedule": {}, "dates": [], "dayPlans": {}}

    d0 = _parse_iso_date(start_date) if start_date else None
    d1 = _parse_iso_date(end_date) if end_date else None
    if d0 and d1:
        if d1 < d0:
            raise HTTPException(status_code=400, detail="结束日期不能早于起始日期")
        if (d1 - d0).days > 62:
            raise HTTPException(status_code=400, detail="查询区间最多 63 天")
        dates = _daterange(d0, d1)
        years_set = {d.year for d in dates}
    elif year is not None and month is not None:
        dates = _month_dates(year, month)
        years_set = {year}
    else:
        raise HTTPException(status_code=400, detail="请提供 start_date 与 end_date，或 year 与 month")

    holiday_by_date = _holiday_map_for_years(years_set)
    holidays = {k: v["type"] for k, v in holiday_by_date.items()}
    date_info = []
    for d in dates:
        ds = d.strftime("%Y-%m-%d")
        wd = _is_workday(d, holidays)
        h = holiday_by_date.get(ds)
        ht = h["type"] if h else ""
        fest = h["festival"] if h else ""
        mark = _holiday_header_mark(ht, fest) if h else ""
        date_info.append({
            "date": ds,
            "weekday": d.weekday(),
            "isWorkday": wd,
            "label": ["一", "二", "三", "四", "五", "六", "日"][d.weekday()],
            "holidayType": ht,
            "holidayFestival": fest,
            "holidayMark": mark,
        })

    ph = ",".join(["%s"] * len(employees))
    ds_lo = dates[0].strftime("%Y-%m-%d")
    ds_hi = dates[-1].strftime("%Y-%m-%d")
    rows = db.execute_query(
        f"SELECT employee_name, shift_date, shift_type FROM shift_schedule "
        f"WHERE department = %s AND shift_date >= %s AND shift_date <= %s AND employee_name IN ({ph})",
        (department, ds_lo, ds_hi) + tuple(employees),
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

    day_plans = {}
    try:
        plan_rows = db.execute_query(
            "SELECT plan_date, content FROM shift_day_plan "
            "WHERE department = %s AND plan_date >= %s AND plan_date <= %s",
            (department, ds_lo, ds_hi),
        )
        for pr in plan_rows or []:
            pd = pr.get("plan_date")
            if hasattr(pd, "strftime"):
                pds = pd.strftime("%Y-%m-%d")
            else:
                pds = str(pd)[:10] if pd else ""
            if pds:
                day_plans[pds] = (pr.get("content") or "").strip()
    except Exception as e:
        logger.warning("读取 shift_day_plan 失败: %s", e)

    open_dates = []
    try:
        lock_rows = db.execute_query(
            "SELECT lock_date FROM shift_day_lock "
            "WHERE department = %s AND lock_date >= %s AND lock_date <= %s AND is_open = 1",
            (department, ds_lo, ds_hi),
        )
        for lr in lock_rows or []:
            ld = lr.get("lock_date")
            if hasattr(ld, "strftime"):
                open_dates.append(ld.strftime("%Y-%m-%d"))
            else:
                lds = str(ld)[:10] if ld else ""
                if lds:
                    open_dates.append(lds)
    except Exception as e:
        logger.warning("读取 shift_day_lock 失败: %s", e)

    return {
        "success": True,
        "employees": employees,
        "schedule": schedule,
        "dates": date_info,
        "dayPlans": day_plans,
        "openDates": open_dates,
    }


class SaveScheduleRequest(BaseModel):
    department: str
    year: int = 0  # 兼容旧前端；实际以每条 date 解析年月写入
    month: int = 0
    schedule: dict  # { "张三": { "2026-03-01": "白班", ... }, ... }
    current_user: str = ""


@router.post("/schedule")
async def save_schedule(req: SaveScheduleRequest):
    """保存排班数据（每条记录的 year/month 按 shift_date 解析，支持跨月区间）"""
    _ensure_tables()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_mgr = _is_manager_of_dept(req.current_user, req.department)
    today_d = date.today()
    caller = (req.current_user or "").strip()
    if not is_mgr and not _is_dept_member(req.current_user, req.department):
        raise HTTPException(status_code=403, detail="仅本科室成员可保存排班")

    open_set = None
    if not is_mgr:
        all_dates = sorted({str(ds)[:10] for _, dm in req.schedule.items() for ds in dm.keys()})
        if all_dates:
            rows = db.execute_query(
                "SELECT lock_date FROM shift_day_lock "
                "WHERE department = %s AND is_open = 1 AND lock_date >= %s AND lock_date <= %s",
                (req.department, all_dates[0], all_dates[-1]),
            )
            open_set = set()
            for r in rows:
                ld = r.get("lock_date")
                open_set.add(ld.strftime("%Y-%m-%d") if hasattr(ld, "strftime") else str(ld)[:10])
        else:
            open_set = set()

    params_list = []
    for emp_name, day_map in req.schedule.items():
        en = (emp_name or "").strip()
        if not is_mgr:
            if not caller or en != caller:
                continue
        for date_str, shift_type in day_map.items():
            d = _parse_iso_date(str(date_str))
            if not d:
                continue
            ds = d.strftime("%Y-%m-%d")
            if open_set is not None and ds not in open_set:
                continue
            if not is_mgr and d < today_d:
                continue
            y, m = d.year, d.month
            params_list.append((
                req.department, en, ds, shift_type,
                y, m, req.current_user, now,
                shift_type, req.current_user, now,
            ))
    if not params_list:
        return {"success": True, "message": "无排班数据"}
    sql = (
        "INSERT INTO shift_schedule (department, employee_name, shift_date, shift_type, year, month, updated_by, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE shift_type = %s, updated_by = %s, updated_at = %s"
    )
    n = db.execute_many(sql, params_list)
    if n < 0:
        raise HTTPException(status_code=500, detail="保存排班失败，请稍后重试")
    return {"success": True, "message": f"已保存 {len(params_list)} 条排班记录"}


MAX_DAY_PLAN_LEN = 2000


class SaveDayPlansRequest(BaseModel):
    department: str
    current_user: str = ""
    plans: dict  # {"2026-03-01": "值班工作计划…"}


@router.post("/day-plans")
async def save_day_plans(req: SaveDayPlansRequest):
    """按科室、按日保存值班工作计划（协同编辑，与排班表头下计划行对应）"""
    _ensure_tables()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_mgr = _is_manager_of_dept(req.current_user, req.department)
    open_set = None
    if not is_mgr:
        if not _is_dept_member(req.current_user, req.department):
            raise HTTPException(status_code=403, detail="仅本科室成员可保存工作计划")
        parsed = []
        for date_str in (req.plans or {}).keys():
            d = _parse_iso_date(str(date_str))
            if d:
                parsed.append(d.strftime("%Y-%m-%d"))
        parsed.sort()
        open_set = set()
        if parsed:
            rows = db.execute_query(
                "SELECT lock_date FROM shift_day_lock "
                "WHERE department = %s AND is_open = 1 AND lock_date >= %s AND lock_date <= %s",
                (req.department, parsed[0], parsed[-1]),
            )
            for r in rows or []:
                ld = r.get("lock_date")
                open_set.add(ld.strftime("%Y-%m-%d") if hasattr(ld, "strftime") else str(ld)[:10])

    sql_ins = (
        "INSERT INTO shift_day_plan (department, plan_date, content, updated_by, updated_at) "
        "VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE "
        "content=%s, updated_by=%s, updated_at=%s"
    )
    for date_str, raw in (req.plans or {}).items():
        d = _parse_iso_date(str(date_str))
        if not d:
            continue
        ds = d.strftime("%Y-%m-%d")
        if open_set is not None and ds not in open_set:
            continue
        text = (str(raw) if raw is not None else "").strip()
        if len(text) > MAX_DAY_PLAN_LEN:
            text = text[:MAX_DAY_PLAN_LEN]
        if not text:
            db.execute_update(
                "DELETE FROM shift_day_plan WHERE department=%s AND plan_date=%s",
                (req.department, ds),
            )
        else:
            db.execute_update(
                sql_ins,
                (req.department, ds, text, req.current_user, now, text, req.current_user, now),
            )
    return {"success": True, "message": "工作计划已保存"}


# ==================== 自动排班 ====================

class AutoScheduleRequest(BaseModel):
    department: str
    year: Optional[int] = None
    month: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    current_user: str = ""
    workday_day: Optional[int] = None
    workday_night: Optional[int] = None
    weekend_day: Optional[int] = None
    weekend_night: Optional[int] = None


@router.post("/auto-schedule")
async def auto_schedule(req: AutoScheduleRequest):
    """
    自动排班：严格按配置人数安排，配置几人就排几人，其余留空。
    工作日：workday_day 人白班，workday_night 人夜班。
    周末：weekend_day 人白班，weekend_night 人夜班。
    今天之前的日期不写入、不覆盖；轮转仍按整段日期推进，使「今天起」的排班与连续排满时一致。
    """
    _ensure_tables()
    employees = _get_dept_employees(req.department)
    if not employees:
        return {"success": False, "message": "该科室无在职员工"}
    cfg_rows = db.execute_query(
        "SELECT workday_day, workday_night, weekend_day, weekend_night FROM shift_config WHERE department = %s LIMIT 1",
        (req.department,),
    )
    cfg = cfg_rows[0] if cfg_rows else {}

    def _pick(req_val, cfg_key, fallback=2):
        return max(0, int(req_val) if req_val is not None else int(cfg.get(cfg_key) or fallback))

    workday_day = _pick(req.workday_day, "workday_day")
    workday_night = _pick(req.workday_night, "workday_night")
    weekend_day = _pick(req.weekend_day, "weekend_day")
    weekend_night = _pick(req.weekend_night, "weekend_night")

    d0 = _parse_iso_date(req.start_date) if req.start_date else None
    d1 = _parse_iso_date(req.end_date) if req.end_date else None
    if d0 and d1:
        if d1 < d0:
            raise HTTPException(status_code=400, detail="结束日期不能早于起始日期")
        if (d1 - d0).days > 62:
            raise HTTPException(status_code=400, detail="自动排班区间最多 63 天")
        dates = _daterange(d0, d1)
        years_set = {d.year for d in dates}
    elif req.year is not None and req.month is not None:
        dates = _month_dates(req.year, req.month)
        years_set = {req.year}
    else:
        raise HTTPException(status_code=400, detail="请提供 start_date 与 end_date，或 year 与 month")

    holidays = {}
    for y in years_set:
        for r in load_holidays_for_year(str(y)):
            nk = _normalize_date_key(r.get("date"))
            if nk:
                holidays[nk] = (r.get("type") or "").strip()
    n = len(employees)
    today_d = date.today()

    schedule = {emp: {} for emp in employees}
    wd_day_idx = 0
    wd_night_idx = 0
    we_day_idx = 0
    we_night_idx = 0

    for d in dates:
        ds = d.strftime("%Y-%m-%d")
        is_wd = _is_workday(d, holidays)
        if is_wd:
            d_count = min(workday_day, n)
            n_count = min(workday_night, n)
        else:
            d_count = min(weekend_day, n)
            n_count = min(weekend_night, n)

        day_set = set()
        night_set = set()
        day_idx = wd_day_idx if is_wd else we_day_idx
        night_idx = wd_night_idx if is_wd else we_night_idx

        if d >= today_d:
            for i in range(d_count):
                emp = employees[(day_idx + i) % n]
                schedule[emp][ds] = "白班"
                day_set.add(emp)

            for i in range(n_count):
                emp = employees[(night_idx + i) % n]
                if emp not in day_set:
                    schedule[emp][ds] = "夜班"
                    night_set.add(emp)
                else:
                    for j in range(1, n):
                        candidate = employees[(night_idx + i + j) % n]
                        if candidate not in day_set and candidate not in night_set:
                            schedule[candidate][ds] = "夜班"
                            night_set.add(candidate)
                            break

        if is_wd:
            wd_day_idx = (wd_day_idx + d_count) % n if d_count else wd_day_idx
            wd_night_idx = (wd_night_idx + n_count) % n if n_count else wd_night_idx
        else:
            we_day_idx = (we_day_idx + d_count) % n if d_count else we_day_idx
            we_night_idx = (we_night_idx + n_count) % n if n_count else we_night_idx

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    params_list = []
    for emp_name, day_map in schedule.items():
        for date_str, shift_type in day_map.items():
            if not shift_type:
                continue
            d = _parse_iso_date(date_str)
            if not d:
                continue
            params_list.append((
                req.department, emp_name, date_str, shift_type,
                d.year, d.month, req.current_user, now,
                shift_type, req.current_user, now,
            ))
    ds_first = dates[0].strftime("%Y-%m-%d")
    ds_last = dates[-1].strftime("%Y-%m-%d")
    today_str = today_d.strftime("%Y-%m-%d")
    del_from = ds_first if ds_first > today_str else today_str
    if del_from <= ds_last:
        db.execute_update(
            "DELETE FROM shift_schedule WHERE department = %s AND shift_date >= %s AND shift_date <= %s",
            (req.department, del_from, ds_last),
        )
    if params_list:
        sql = (
            "INSERT INTO shift_schedule (department, employee_name, shift_date, shift_type, year, month, updated_by, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE shift_type = %s, updated_by = %s, updated_at = %s"
        )
        rc = db.execute_many(sql, params_list)
        if rc < 0:
            raise HTTPException(status_code=500, detail="自动排班写入失败，请稍后重试")
    sched_days = sum(1 for d in dates if d >= today_d)
    return {
        "success": True,
        "message": f"已自动排班：{len(employees)} 人，本段共 {len(dates)} 天（其中 {sched_days} 天为今天及之后已写入）",
        "schedule": schedule,
    }


# ==================== 复制上月排班 ====================

class CopyScheduleRequest(BaseModel):
    department: str
    year: Optional[int] = None
    month: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    current_user: str = ""


@router.post("/copy-last-month")
async def copy_last_month(req: CopyScheduleRequest):
    """复制上月对应日期的排班：按日期区间（当前屏）或整月。"""
    _ensure_tables()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    d0 = _parse_iso_date(req.start_date) if req.start_date else None
    d1 = _parse_iso_date(req.end_date) if req.end_date else None

    if d0 and d1:
        if d1 < d0:
            raise HTTPException(status_code=400, detail="结束日期不能早于起始日期")
        dst_dates = _daterange(d0, d1)
        src_dates_list = [_prev_month_same_day(d) for d in dst_dates]
        src_set = sorted({s.strftime("%Y-%m-%d") for s in src_dates_list})
        ph_s = ",".join(["%s"] * len(src_set))
        rows = db.execute_query(
            f"SELECT employee_name, shift_date, shift_type FROM shift_schedule "
            f"WHERE department = %s AND shift_date IN ({ph_s})",
            (req.department,) + tuple(src_set),
        )
        if not rows:
            return {"success": False, "message": "对应上月日期无排班记录"}
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
            for dst_d, src_d in zip(dst_dates, src_dates_list):
                src_ds = src_d.strftime("%Y-%m-%d")
                st = day_map.get(src_ds, "")
                if not st:
                    continue
                dst_ds = dst_d.strftime("%Y-%m-%d")
                params_list.append((
                    req.department, name, dst_ds, st,
                    dst_d.year, dst_d.month, req.current_user, now,
                    st, req.current_user, now,
                ))
    elif req.year is not None and req.month is not None:
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
                dst_d = dst_dates[i]
                dst_ds = dst_d.strftime("%Y-%m-%d")
                params_list.append((
                    req.department, name, dst_ds, st,
                    dst_d.year, dst_d.month, req.current_user, now,
                    st, req.current_user, now,
                ))
    else:
        raise HTTPException(status_code=400, detail="请提供 start_date 与 end_date，或 year 与 month")

    if not params_list:
        return {"success": False, "message": "上月排班记录为空"}
    sql = (
        "INSERT INTO shift_schedule (department, employee_name, shift_date, shift_type, year, month, updated_by, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE shift_type = %s, updated_by = %s, updated_at = %s"
    )
    n = db.execute_many(sql, params_list)
    if n < 0:
        raise HTTPException(status_code=500, detail="复制上月排班失败，请稍后重试")
    return {"success": True, "message": f"已复制 {len(params_list)} 条排班记录"}


# ==================== 清空当月排班 ====================

class ClearScheduleRequest(BaseModel):
    department: str
    year: Optional[int] = None
    month: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.post("/clear-schedule")
async def clear_schedule(req: ClearScheduleRequest):
    """清空该科室排班：按日期区间或整月"""
    _ensure_tables()
    d0 = _parse_iso_date(req.start_date) if req.start_date else None
    d1 = _parse_iso_date(req.end_date) if req.end_date else None
    if d0 and d1:
        if d1 < d0:
            raise HTTPException(status_code=400, detail="结束日期不能早于起始日期")
        n = db.execute_update(
            "DELETE FROM shift_schedule WHERE department = %s AND shift_date >= %s AND shift_date <= %s",
            (req.department, d0.strftime("%Y-%m-%d"), d1.strftime("%Y-%m-%d")),
        )
    elif req.year is not None and req.month is not None:
        n = db.execute_update(
            "DELETE FROM shift_schedule WHERE department = %s AND year = %s AND month = %s",
            (req.department, req.year, req.month),
        )
    else:
        raise HTTPException(status_code=400, detail="请提供 start_date 与 end_date，或 year 与 month")
    if n < 0:
        raise HTTPException(status_code=500, detail="清空排班失败，请稍后重试")
    return {"success": True, "message": f"已清空 {n} 条排班记录"}


# ==================== 科室列表 ====================

@router.get("/departments")
async def get_departments():
    """获取所有科室列表"""
    rows = db.execute_query(
        "SELECT DISTINCT lsys FROM yggl WHERE lsys IS NOT NULL AND lsys != '' "
        "AND RIGHT(TRIM(lsys),1) != '1' AND TRIM(lsys) != '部办' "
        "AND TRIM(lsys) != '其他部门员工' "
        "AND COALESCE(zaizhi,0) = 0 ORDER BY lsys"
    )
    depts = [(r.get("lsys") or "").strip() for r in rows if (r.get("lsys") or "").strip()]
    return {"success": True, "departments": depts}
