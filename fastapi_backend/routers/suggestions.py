# -*- coding: utf-8 -*-
"""
智能建议API路由
使用新的 SQLite 数据库
"""
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from models import SuggestionResponse, Suggestion
from attendance_db import attendance_db
from database import db
from utils.helpers import normalize_date_str, time_to_decimal, format_time
from utils.holiday_loader import load_holidays_dict
from datetime import datetime, timedelta, date
import math
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suggestions", tags=["智能建议"])


def _floor_half_hours(h: float) -> float:
    """按 0.5 小时向下取整，不满 0.5 舍去。如 4.4 -> 4.0"""
    return math.floor(h * 2) / 2


def _format_hours_display(h: float) -> str:
    """格式化加班小时显示：先按 0.5 向下取整，整数显示为「4小时」，否则「4.5小时」"""
    h = _floor_half_hours(h)
    if h == int(h):
        return f"{int(h)}小时"
    return f"{h:.1f}小时"


def _to_comparable_dt(val: Any) -> Optional[str]:
    """将 DB 返回的 datetime/date 转为可比较的字符串 YYYY-MM-DD HH:MM:SS"""
    if val is None:
        return None
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d %H:%M:%S") if hasattr(val, "hour") else val.strftime("%Y-%m-%d") + " 00:00:00"
    s = str(val).strip()
    if "." in s:
        s = s.split(".")[0]
    return s[:19] if len(s) >= 19 else (s + " 00:00:00" if len(s) == 10 else s)


def _interval_covered(
    s_start: str,
    s_end: str,
    rows: List[Dict],
    get_start_end,
) -> bool:
    """通用：建议区间 [s_start, s_end] 是否被 rows 中某条记录的区间包含。get_start_end(r) -> (start, end)。"""
    for r in rows:
        r_start, r_end = get_start_end(r)
        r_start = _to_comparable_dt(r_start)
        r_end = _to_comparable_dt(r_end)
        if r_start and r_end and r_start <= s_start and s_end <= r_end:
            return True
    return False


def _suggestion_handled(
    start_time: Any,
    end_time: Any,
    status: int,
    jiaban_rows: List[Dict],
    qj_rows: List[Dict],
    gcsqb_rows: List[Dict],
) -> bool:
    """
    判断建议时间区间 [start_time, end_time] 是否已处理完成。
    status=0(加班): 建议区间被某条 jiaban(已通过) 的 [timefrom,timeto] 包含或相等；
    status=1(缺勤): 建议区间被某条 qj(已通过) 或 gcsqb(已通过且含 gcsj/sjfhtime) 的区间包含或相等。
    """
    s_start = _to_comparable_dt(start_time)
    s_end = _to_comparable_dt(end_time)
    if not s_start or not s_end:
        return False
    if status == 0:
        return _interval_covered(s_start, s_end, jiaban_rows, lambda r: (r.get("timefrom"), r.get("timeto")))
    if status == 1:
        if _interval_covered(s_start, s_end, qj_rows, lambda r: (r.get("timefrom"), r.get("timeto"))):
            return True
        return _interval_covered(s_start, s_end, gcsqb_rows, lambda r: (r.get("gcsj"), r.get("sjfhtime") or r.get("yjfhsj")))
    return False


def _suggestion_under_review(
    start_time: Any,
    end_time: Any,
    status: int,
    jiaban_pending: List[Dict],
    qj_pending: List[Dict],
    gcsqb_pending: List[Dict],
) -> bool:
    """
    判断建议时间区间是否已被「已提交但未审批通过」的记录覆盖（正在审核）。
    status=0: 被 jiaban(jiabanzt in 0,1,3) 覆盖；
    status=1: 被 qj(qjzt in 0,1,3) 或 gcsqb(未双审通过) 覆盖。
    """
    s_start = _to_comparable_dt(start_time)
    s_end = _to_comparable_dt(end_time)
    if not s_start or not s_end:
        return False
    if status == 0:
        return _interval_covered(s_start, s_end, jiaban_pending, lambda r: (r.get("timefrom"), r.get("timeto")))
    if status == 1:
        if _interval_covered(s_start, s_end, qj_pending, lambda r: (r.get("timefrom"), r.get("timeto"))):
            return True
        return _interval_covered(s_start, s_end, gcsqb_pending, lambda r: (r.get("gcsj"), r.get("sjfhtime") or r.get("yjfhsj")))
    return False


def get_attendance_exception_keys(year: int, month: int) -> List[tuple]:
    """
    计算指定年月下所有「考勤异常」的 (employee_name, department, date_str)。
    异常定义：智能建议中 status=1（需请假/缺勤）且既未完成请假/公出，也未在审核中覆盖。
    返回列表用于过滤考勤记录，仅展示异常日的打卡数据。
    """
    try:
        attendance_db.ensure_suggestions_table()
        employees = attendance_db.get_distinct_employees_for_suggestions(year, month)
        exception_keys = []
        for emp in employees:
            name = emp.get("employee_name")
            dept = (emp.get("department") or "").strip()
            if not name or not dept:
                continue
            # 部办为领导，不纳入考勤异常管理
            if dept == "部办":
                continue
            rows = attendance_db.get_suggestions(name, dept, year, month)
            jiaban_rows, qj_rows, gcsqb_rows = [], [], []
            jiaban_pending, qj_pending, gcsqb_pending = [], [], []
            try:
                jiaban_rows = db.execute_query(
                    "SELECT timefrom, timeto FROM jiaban WHERE xm = %s AND jiabanzt = 4 AND YEAR(timefrom) = %s AND MONTH(timefrom) = %s",
                    (name, year, month),
                )
                qj_rows = db.execute_query(
                    "SELECT timefrom, timeto FROM qj WHERE xm = %s AND qjzt = 4 AND YEAR(timefrom) = %s AND MONTH(timefrom) = %s",
                    (name, year, month),
                )
                gcsqb_rows = db.execute_query(
                    "SELECT gcsj, sjfhtime, yjfhsj FROM gcsqb WHERE gcr = %s AND bldzt = 2 AND szrzt = 2 AND gcsj IS NOT NULL AND YEAR(gcsj) = %s AND MONTH(gcsj) = %s",
                    (name, year, month),
                )
                jiaban_pending = db.execute_query(
                    "SELECT timefrom, timeto FROM jiaban WHERE xm = %s AND jiabanzt IN (0, 1, 3, 5) AND YEAR(timefrom) = %s AND MONTH(timefrom) = %s",
                    (name, year, month),
                )
                qj_pending = db.execute_query(
                    "SELECT timefrom, timeto FROM qj WHERE xm = %s AND qjzt IN (0, 1, 3) AND YEAR(timefrom) = %s AND MONTH(timefrom) = %s",
                    (name, year, month),
                )
                gcsqb_pending = db.execute_query(
                    "SELECT gcsj, sjfhtime, yjfhsj FROM gcsqb WHERE gcr = %s AND (bldzt != 2 OR szrzt != 2) AND bldzt != 22 AND szrzt != 22 AND gcsj IS NOT NULL AND YEAR(gcsj) = %s AND MONTH(gcsj) = %s",
                    (name, year, month),
                )
            except Exception as e:
                logger.warning(f"查询已处理/审核中区间失败 name=%s: %s", name, e)
            for r in rows:
                st = r.get("status") if r.get("status") is not None else 0
                if st != 1:
                    continue
                handled = _suggestion_handled(
                    r.get("start_time"), r.get("end_time"), st,
                    jiaban_rows, qj_rows, gcsqb_rows,
                )
                under_review = not handled and _suggestion_under_review(
                    r.get("start_time"), r.get("end_time"), st,
                    jiaban_pending, qj_pending, gcsqb_pending,
                )
                if not handled and not under_review:
                    date_str = r.get("date") or ""
                    if date_str:
                        exception_keys.append((name, dept, date_str))
        return exception_keys
    except Exception as e:
        logger.error(f"计算考勤异常键失败: {str(e)}")
        return []


def load_holidays(year: str = None) -> Dict[str, str]:
    """加载假期数据（日期 -> 类型）。数据来自数据库 holiday 表。"""
    return load_holidays_dict(year)


def is_workday(date_obj: datetime, holidays: Dict[str, str]) -> tuple:
    """
    判断是否为工作日
    返回: (是否工作日, 是否周末, 是否假期, 假期类型)
    """
    date_str = date_obj.strftime("%Y-%m-%d")
    weekday = date_obj.weekday()  # 0=周一, 6=周日
    
    # 判断是否为假期
    is_holiday = False
    holiday_type = ""
    if date_str in holidays:
        holiday_type = holidays[date_str]
        if "假" in holiday_type or "休" in holiday_type:
            is_holiday = True
    
    # 判断是否为周末 (周六或周日)
    is_weekend = weekday in [5, 6]
    
    # 如果是调休日，则不算周末和假期
    if date_str in holidays and "班" in holidays[date_str]:
        is_weekend = False
        is_holiday = False
    
    is_work = not is_weekend and not is_holiday
    
    return is_work, is_weekend, is_holiday, holiday_type


def collect_valid_times(record: dict) -> List[datetime]:
    """收集所有有效的打卡时间"""
    times = []
    # 新数据库使用 time_1 到 time_10 的字段名
    for i in range(1, 11):
        time_val = record.get(f"time_{i}")
        if time_val and time_val != "":
            if isinstance(time_val, datetime):
                times.append(time_val)
            elif isinstance(time_val, str):
                try:
                    # 尝试解析时间字符串
                    parsed_time = datetime.strptime(time_val, "%H:%M:%S")
                    times.append(parsed_time)
                except:
                    pass
    return times


def _sugg(start_time: str, end_time: str, status: int, message: str) -> dict:
    """构造一条建议（含开始/结束时间与状态码 0=加班 1=缺勤）"""
    return {"start_time": start_time, "end_time": end_time, "status": status, "message": message}


def _time_to_datetime(date_str: str, time_str: str) -> str:
    """将日期 YYYY-MM-DD 与时间 HH:MM 或 HH:MM:SS 拼成 YYYY-MM-DD HH:MM:SS，供 DATETIME(0) 写入"""
    if not date_str or not time_str:
        return ""
    t = time_str.strip()
    if len(t) == 5 and ":" in t:  # HH:MM
        t = t + ":00"
    return f"{date_str.strip()[:10]} {t}"


def analyze_workday(record: dict, date_obj: datetime) -> List[dict]:
    """分析工作日打卡记录，生成建议（按刷入/刷离区间逻辑）。返回 List[dict] 含 start_time, end_time, status, message。"""
    suggestions: List[dict] = []

    # 1. 收集并排序所有有效打卡时间
    times = collect_valid_times(record)
    if not times:
        return suggestions

    times.sort()

    # 工作时间与加班时间常量
    WORK_AM_START = 8      # 上午上班开始
    WORK_AM_END = 12       # 上午下班
    WORK_PM_START = 13     # 下午上班开始
    WORK_PM_END = 17       # 正常下班
    OVERTIME_START = 17    # 工作日加班起点
    OVERTIME_END = 24      # 统计到 24:00
    OVERTIME_MIN_HOURS = 1 # 加班至少 1 小时

    def decimal_to_dt(base_date: datetime, h: float) -> datetime:
        """将小时时间(如 17.5) 转为 datetime，用于 format_time"""
        hour = int(h)
        minute = int(round((h - hour) * 60))
        if minute == 60:
            hour += 1
            minute = 0
        return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # -------------------------------------------------
    # 2. 迟到检测（仅检测迟到，早退由缺勤逻辑处理）
    # -------------------------------------------------
    first_time = times[0]
    first_val = time_to_decimal(first_time)

    # 迟到：第一次打卡在 8:00 之后且在 12:00 之前
    if WORK_AM_START < first_val < WORK_AM_END:
        suggestions.append(_sugg(
            "08:00:00", format_time(first_time), 1,
            f"【考勤建议】检测到迟到，建议补录 08:00 到 {format_time(first_time)} 的考勤"
        ))

    # -------------------------------------------------
    # 3. 构造（刷入，刷离）区间：第1次视为刷入，第2次为刷离……
    # -------------------------------------------------
    intervals: List[tuple[datetime, datetime]] = []
    for i in range(0, len(times), 2):
        if i + 1 < len(times):
            t_in = times[i]
            t_out = times[i + 1]
            if t_out > t_in:
                intervals.append((t_in, t_out))

    # 如果是奇数个打卡（最后一个没有配对），目前忽略最后一个

    # -------------------------------------------------
    # 4. 缺勤检查逻辑：
    #    规则：如果刷离时间在工作时间区间内（8–12 或 13–17），
    #          则 "刷离时间 → 下次刷入时间" 为缺勤；
    #          如果已是最后一个区间，则补到 17:00。
    # -------------------------------------------------
    for idx, (t_in, t_out) in enumerate(intervals):
        out_val = time_to_decimal(t_out)

        in_am = WORK_AM_START <= out_val <= WORK_AM_END
        in_pm = WORK_PM_START <= out_val <= WORK_PM_END

        if not (in_am or in_pm):
            continue  # 刷离不在工作时间内，不视为工作时段缺勤起点

        # 情况 A：有下一次刷入
        if idx + 1 < len(intervals):
            next_in = intervals[idx + 1][0]
            if next_in > t_out:
                suggestions.append(_sugg(
                    format_time(t_out), format_time(next_in), 1,
                    f"【考勤建议】检测到缺勤，建议补录 {format_time(t_out)} 到 {format_time(next_in)} 的考勤"
                ))
        else:
            # 情况 B：这是最后一个区间，且刷离早于 17:00，则从刷离到 17:00 视为缺勤
            if out_val < WORK_PM_END:
                end_dt = date_obj.replace(hour=17, minute=0, second=0, microsecond=0)
                suggestions.append(_sugg(
                    format_time(t_out), format_time(end_dt), 1,
                    f"【考勤建议】检测到缺勤，建议补录 {format_time(t_out)} 到 {format_time(end_dt)} 的考勤"
                ))

    # -------------------------------------------------
    # 5. 工作日加班检测：
    #    检查每个（刷入，刷离）区间与 [17:00, 24:00] 的交集，
    #    交集时长 ≥ 1 小时则提示加班。
    #    （工作日加班都在 17:00 之后，因此无需处理中午 12–13）
    # -------------------------------------------------
    for t_in, t_out in intervals:
        a = time_to_decimal(t_in)
        b = time_to_decimal(t_out)

        # 区间与 [17, 24] 求交集
        inter_start = max(a, OVERTIME_START)
        inter_end = min(b, OVERTIME_END)

        if inter_end <= inter_start:
            continue  # 没有加班交集

        duration = inter_end - inter_start
        if duration < OVERTIME_MIN_HOURS:
            continue  # 未达到 1 小时，不提示

        start_dt = decimal_to_dt(date_obj, inter_start)
        end_dt = decimal_to_dt(date_obj, inter_end)
        st_str, et_str = format_time(start_dt), format_time(end_dt)
        suggestions.append(_sugg(
            st_str, et_str, 0,
            f"【加班建议】检测到 {st_str} 到 {et_str} 的加班（约{_format_hours_display(duration)}）"
        ))

    return suggestions


def analyze_restday(record: dict, date_obj: datetime) -> List[dict]:
    """
    分析休息日/假期打卡记录，生成建议。返回 List[dict] 含 start_time, end_time, status=0, message。
    逻辑：
    - 打卡按 (time_1,time_2)、(time_3,time_4)... 成对为进出段。
    - 若某段结束 <12:00 且下一段开始 >12:00（午休前离岗、午休后返岗，有跨越午休的离岗即分段），则必须按两段分别建议，不能合并，否则会多算。
    - 否则（未在午休时段离岗）可合并为一段，跨午休时扣除 1 小时。
    """
    suggestions: List[dict] = []

    times = collect_valid_times(record)
    if not times:
        return suggestions

    times.sort()
    NOON_START = 12
    NOON_END = 13
    OT_START_HOUR = 8  # 加班开始时间不早于 8:00，8:00 之前不计入加班
    RESTDAY_OVERTIME_MIN_HOURS = 1.0

    # 按进出对划分：(times[0],times[1]), (times[2],times[3]), ...
    pairs: List[tuple] = []
    for i in range(0, len(times) - 1, 2):
        pairs.append((times[i], times[i + 1]))

    if not pairs:
        return suggestions

    # 判断是否存在「午休前离岗、午休后返岗」：某对结束 <12:00 且下一对开始 >12:00（有跨越午休的离岗即分段，否则会多算）
    has_lunch_leave = False
    for j in range(len(pairs) - 1):
        end_val = time_to_decimal(pairs[j][1])
        next_start_val = time_to_decimal(pairs[j + 1][0])
        if end_val < NOON_START and next_start_val > NOON_START:
            has_lunch_leave = True
            break

    if has_lunch_leave:
        # 必须按段填报，每段单独一条建议；开始时间不早于 8:00；下午段若在 12:00-13:00 之间开始则建议从 13:00 起算
        for s_time, e_time in pairs:
            s_val = time_to_decimal(s_time)
            e_val = time_to_decimal(e_time)
            if s_val >= e_val:
                continue
            effective_start = max(s_val, OT_START_HOUR)
            if NOON_START <= effective_start < NOON_END:
                effective_start = NOON_END
            if effective_start >= e_val:
                continue
            duration = e_val - effective_start
            if duration < RESTDAY_OVERTIME_MIN_HOURS:
                continue
            if s_val < OT_START_HOUR:
                start_str = "08:00:00"
            elif NOON_START <= s_val < NOON_END:
                start_str = "13:00:00"
            else:
                start_str = format_time(s_time)
            end_str = format_time(e_time)
            suggestions.append(_sugg(
                start_str, end_str, 0,
                f"【加班建议】休息日加班，建议补录 {start_str} 到 {end_str} 的加班（约{_format_hours_display(duration)}）"
            ))
        return suggestions

    # 未在午休离岗：可合并为一段，跨午休时扣 1 小时；开始时间不早于 8:00
    first_time = times[0]
    last_time = times[-1]
    start_val = time_to_decimal(first_time)
    end_val = time_to_decimal(last_time)

    if start_val >= end_val:
        return suggestions

    effective_start = max(start_val, OT_START_HOUR)
    if NOON_START <= effective_start < NOON_END:
        effective_start = NOON_END

    effective_end = end_val
    if NOON_START < end_val <= NOON_END:
        effective_end = NOON_START

    if effective_start >= effective_end:
        return suggestions

    cross_noon = effective_start < NOON_START and effective_end > NOON_END
    if cross_noon:
        total_hours = (effective_end - effective_start) - (NOON_END - NOON_START)
    else:
        total_hours = effective_end - effective_start

    if total_hours < RESTDAY_OVERTIME_MIN_HOURS:
        return suggestions

    start_str = "08:00:00" if start_val < OT_START_HOUR else format_time(first_time)
    end_str = format_time(last_time)
    suggestions.append(_sugg(
        start_str, end_str, 0,
        f"【加班建议】休息日加班，建议补录 {start_str} 到 {end_str} 的加班（约{_format_hours_display(total_hours)}）"
    ))

    return suggestions


def _parse_record_date(date_obj):
    """将记录中的 attendance_date 转为 datetime"""
    if not date_obj:
        return None
    try:
        if isinstance(date_obj, datetime):
            return date_obj
        if isinstance(date_obj, date):
            return datetime.combine(date_obj, datetime.min.time())
        if isinstance(date_obj, str):
            if "/" in date_obj:
                return datetime.strptime(date_obj, "%Y/%m/%d")
            if "-" in date_obj:
                return datetime.strptime(date_obj[:10], "%Y-%m-%d")
    except Exception:
        pass
    return None


def generate_suggestions_for_month_with_records(
        name: str, dept: str, year: int, month: int,
        records: List[Dict], holidays: Dict[str, str]) -> List[Dict]:
    """同 generate_suggestions_for_month，但直接接受已查好的 records 和 holidays，避免重复查库。"""
    start_date = f"{year}-{month:02d}-01"
    existing_dates = set()
    for record in records:
        dt = _parse_record_date(record.get("attendance_date"))
        if dt:
            existing_dates.add(dt.strftime("%Y-%m-%d"))
    first_day_of_month = datetime(year, month, 1)
    if month == 12:
        last_day_of_month = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day_of_month = datetime(year, month + 1, 1) - timedelta(days=1)
    today = datetime.now()
    check_end_date = today if (year == today.year and month == today.month) else last_day_of_month
    suggestions_list = []
    check_date = first_day_of_month
    while check_date <= check_end_date:
        check_date_str = check_date.strftime("%Y-%m-%d")
        is_work, is_weekend, is_hol, holiday_type = is_workday(check_date, holidays)
        if is_work and check_date_str not in existing_dates:
            suggestions_list.append({
                "date": check_date_str, "dayType": "工作日",
                "suggestion": "【考勤建议】检测到全天缺勤，建议补录 8:00 到 17:00 的考勤（全天）",
                "start_time": _time_to_datetime(check_date_str, "08:00"),
                "end_time": _time_to_datetime(check_date_str, "17:00"),
                "status": 1,
            })
        check_date += timedelta(days=1)
    for record in records:
        date_obj = _parse_record_date(record.get("attendance_date"))
        if not date_obj:
            continue
        is_work, is_weekend, is_hol, holiday_type = is_workday(date_obj, holidays)
        record_suggestions = analyze_workday(record, date_obj) if is_work else analyze_restday(record, date_obj)
        day_type = "工作日" if is_work else ("周末" if is_weekend else "假期日")
        date_str = date_obj.strftime("%Y-%m-%d")
        for item in record_suggestions:
            st = item.get("start_time") or ""
            et = item.get("end_time") or ""
            suggestions_list.append({
                "date": date_str, "dayType": day_type,
                "suggestion": item.get("message") or "",
                "start_time": _time_to_datetime(date_str, st),
                "end_time": _time_to_datetime(date_str, et),
                "status": item.get("status", 0),
            })
    return suggestions_list


def generate_suggestions_for_month(name: str, dept: str, year: int, month: int,
                                   holidays_cache: Dict[str, Dict] = None) -> List[Dict]:
    """
    为指定人、指定年月生成智能建议（供上传后写入表或离线使用）。
    holidays_cache: 可选，{year_str: holidays_dict}，避免同年重复查库。
    返回 list of dict: { "date": "YYYY-MM-DD", "dayType": "工作日|周末|假期日", "suggestion": "..." }
    """
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year}-12-31"
    else:
        last = (date(year, month + 1, 1) - timedelta(days=1))
        end_date = last.strftime("%Y-%m-%d")
    records = attendance_db.query_by_date_range(start_date, end_date, name=name, dept=dept)
    existing_dates = set()
    for record in records:
        dt = _parse_record_date(record.get("attendance_date"))
        if dt:
            existing_dates.add(dt.strftime("%Y-%m-%d"))
    year_str = str(year)
    if holidays_cache is not None and year_str in holidays_cache:
        holidays = holidays_cache[year_str]
    else:
        holidays = load_holidays(year_str)
        if holidays_cache is not None:
            holidays_cache[year_str] = holidays
    data_year, data_month = year, month
    first_day_of_month = datetime(data_year, data_month, 1)
    if data_month == 12:
        last_day_of_month = datetime(data_year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day_of_month = datetime(data_year, data_month + 1, 1) - timedelta(days=1)
    today = datetime.now()
    if data_year == today.year and data_month == today.month:
        check_end_date = today
    else:
        check_end_date = last_day_of_month
    suggestions_list = []
    check_date = first_day_of_month
    while check_date <= check_end_date:
        check_date_str = check_date.strftime("%Y-%m-%d")
        is_work, is_weekend, is_holiday, holiday_type = is_workday(check_date, holidays)
        if is_work and check_date_str not in existing_dates:
            suggestions_list.append({
                "date": check_date_str,
                "dayType": "工作日",
                "suggestion": "【考勤建议】检测到全天缺勤，建议补录 8:00 到 17:00 的考勤（全天）",
                "start_time": _time_to_datetime(check_date_str, "08:00"),
                "end_time": _time_to_datetime(check_date_str, "17:00"),
                "status": 1,
            })
        check_date += timedelta(days=1)
    for record in records:
        date_obj = _parse_record_date(record.get("attendance_date"))
        if not date_obj:
            continue
        is_work, is_weekend, is_holiday, holiday_type = is_workday(date_obj, holidays)
        record_suggestions = analyze_workday(record, date_obj) if is_work else analyze_restday(record, date_obj)
        day_type = "工作日" if is_work else ("周末" if is_weekend else "假期日")
        date_str = date_obj.strftime("%Y-%m-%d")
        for item in record_suggestions:
            st = item.get("start_time") or ""
            et = item.get("end_time") or ""
            suggestions_list.append({
                "date": date_str,
                "dayType": day_type,
                "suggestion": item.get("message") or "",
                "start_time": _time_to_datetime(date_str, st),
                "end_time": _time_to_datetime(date_str, et),
                "status": item.get("status", 0),
            })
    return suggestions_list


@router.get("", response_model=SuggestionResponse)
async def get_suggestions(
    name: Optional[str] = Query(None, description="用户姓名"),
    dept: Optional[str] = Query(None, description="用户部门"),
    year: Optional[int] = Query(None, description="年份，与 month 一起传入时从表读取"),
    month: Optional[int] = Query(None, description="月份 1-12，与 year 一起传入时从表读取")
):
    """
    获取智能建议。优先从表 attendance_suggestions 按年月读取（上传打卡后已预生成）；
    若未传 year/month 则退回按当月计算（兼容旧逻辑）。
    """
    if not name or not dept:
        return SuggestionResponse(success=False, suggestions=[])

    try:
        if year is not None and month is not None and 1 <= month <= 12:
            attendance_db.ensure_suggestions_table()
            rows = attendance_db.get_suggestions(name, dept, year, month)
            jiaban_rows, qj_rows, gcsqb_rows = [], [], []
            jiaban_pending, qj_pending, gcsqb_pending = [], [], []
            try:
                jiaban_rows = db.execute_query(
                    "SELECT timefrom, timeto FROM jiaban WHERE xm = %s AND jiabanzt = 4 AND YEAR(timefrom) = %s AND MONTH(timefrom) = %s",
                    (name, year, month),
                )
                qj_rows = db.execute_query(
                    "SELECT timefrom, timeto FROM qj WHERE xm = %s AND qjzt = 4 AND YEAR(timefrom) = %s AND MONTH(timefrom) = %s",
                    (name, year, month),
                )
                gcsqb_rows = db.execute_query(
                    "SELECT gcsj, sjfhtime, yjfhsj FROM gcsqb WHERE gcr = %s AND bldzt = 2 AND szrzt = 2 AND gcsj IS NOT NULL AND YEAR(gcsj) = %s AND MONTH(gcsj) = %s",
                    (name, year, month),
                )
                jiaban_pending = db.execute_query(
                    "SELECT timefrom, timeto FROM jiaban WHERE xm = %s AND jiabanzt IN (0, 1, 3, 5) AND YEAR(timefrom) = %s AND MONTH(timefrom) = %s",
                    (name, year, month),
                )
                qj_pending = db.execute_query(
                    "SELECT timefrom, timeto FROM qj WHERE xm = %s AND qjzt IN (0, 1, 3) AND YEAR(timefrom) = %s AND MONTH(timefrom) = %s",
                    (name, year, month),
                )
                gcsqb_pending = db.execute_query(
                    "SELECT gcsj, sjfhtime, yjfhsj FROM gcsqb WHERE gcr = %s AND (bldzt != 2 OR szrzt != 2) AND bldzt != 22 AND szrzt != 22 AND gcsj IS NOT NULL AND YEAR(gcsj) = %s AND MONTH(gcsj) = %s",
                    (name, year, month),
                )
            except Exception as e:
                logger.warning(f"查询已处理/审核中区间失败: {e}")
            suggestions_list = []
            for r in rows:
                st = r.get("status") if r.get("status") is not None else 0
                handled = _suggestion_handled(
                    r.get("start_time"), r.get("end_time"), st,
                    jiaban_rows, qj_rows, gcsqb_rows,
                )
                under_review = not handled and _suggestion_under_review(
                    r.get("start_time"), r.get("end_time"), st,
                    jiaban_pending, qj_pending, gcsqb_pending,
                )
                suggestions_list.append(Suggestion(
                    date=r["date"],
                    dayType=r.get("dayType") or "",
                    suggestion=r.get("suggestion") or "",
                    status=st,
                    handled=handled,
                    under_review=under_review,
                ))
            return SuggestionResponse(success=True, suggestions=suggestions_list)
        # 兼容：未传年月时按当月计算（旧逻辑，仅用于无表数据时）
        now = datetime.now()
        suggestions_list = generate_suggestions_for_month(name, dept, now.year, now.month)
        jiaban_rows, qj_rows, gcsqb_rows = [], [], []
        jiaban_pending, qj_pending, gcsqb_pending = [], [], []
        try:
            jiaban_rows = db.execute_query(
                "SELECT timefrom, timeto FROM jiaban WHERE xm = %s AND jiabanzt = 4 AND YEAR(timefrom) = %s AND MONTH(timefrom) = %s",
                (name, now.year, now.month),
            )
            qj_rows = db.execute_query(
                "SELECT timefrom, timeto FROM qj WHERE xm = %s AND qjzt = 4 AND YEAR(timefrom) = %s AND MONTH(timefrom) = %s",
                (name, now.year, now.month),
            )
            gcsqb_rows = db.execute_query(
                "SELECT gcsj, sjfhtime, yjfhsj FROM gcsqb WHERE gcr = %s AND bldzt = 2 AND szrzt = 2 AND gcsj IS NOT NULL AND YEAR(gcsj) = %s AND MONTH(gcsj) = %s",
                (name, now.year, now.month),
            )
            jiaban_pending = db.execute_query(
                "SELECT timefrom, timeto FROM jiaban WHERE xm = %s AND jiabanzt IN (0, 1, 3, 5) AND YEAR(timefrom) = %s AND MONTH(timefrom) = %s",
                (name, now.year, now.month),
            )
            qj_pending = db.execute_query(
                "SELECT timefrom, timeto FROM qj WHERE xm = %s AND qjzt IN (0, 1, 3) AND YEAR(timefrom) = %s AND MONTH(timefrom) = %s",
                (name, now.year, now.month),
            )
            gcsqb_pending = db.execute_query(
                "SELECT gcsj, sjfhtime, yjfhsj FROM gcsqb WHERE gcr = %s AND (bldzt != 2 OR szrzt != 2) AND bldzt != 22 AND szrzt != 22 AND gcsj IS NOT NULL AND YEAR(gcsj) = %s AND MONTH(gcsj) = %s",
                (name, now.year, now.month),
            )
        except Exception as e:
            logger.warning(f"查询已处理/审核中区间失败: {e}")
        out = []
        for s in suggestions_list:
            st = s.get("status", 0)
            handled = _suggestion_handled(
                s.get("start_time"), s.get("end_time"), st,
                jiaban_rows, qj_rows, gcsqb_rows,
            )
            under_review = not handled and _suggestion_under_review(
                s.get("start_time"), s.get("end_time"), st,
                jiaban_pending, qj_pending, gcsqb_pending,
            )
            out.append(Suggestion(
                date=s["date"],
                dayType=s.get("dayType") or "",
                suggestion=s.get("suggestion") or "",
                status=st,
                handled=handled,
                under_review=under_review,
            ))
        return SuggestionResponse(success=True, suggestions=out)
    except Exception as e:
        logger.error(f"获取智能建议失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return SuggestionResponse(success=False, suggestions=[])

