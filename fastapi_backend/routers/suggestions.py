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
from datetime import datetime, timedelta, date, time as dt_time
import math
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suggestions", tags=["智能建议"])



def _is_female_employee(name: str) -> bool:
    """
    根据 yggl.xbie 判断是否为女性员工。包含「女」字即视为女性。
    """
    name = (name or "").strip()
    if not name:
        return False
    try:
        rows = db.execute_query(
            "SELECT xbie FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1",
            (name,),
        )
        if rows and rows[0].get("xbie") is not None:
            xbie = (rows[0]["xbie"] or "").strip()
            return "女" in xbie
    except Exception as e:
        logger.debug(f"查询员工性别失败 name={name}: {e}")
    return False


def _is_march8_pm_interval(date_str: Any, start_time: Any, end_time: Any) -> bool:
    """
    是否为 3 月 8 日下午 13:00-17:00 内的缺勤区间。
    仅当 date 为任意年份的 03-08 且 [start,end] 完全落在 13:00-17:00 才返回 True。
    """
    if not date_str:
        return False
    s = str(date_str).strip()
    if len(s) < 10:
        return False
    # 任意年份的 03-08
    try:
        md = s[5:10]
    except Exception:
        return False
    if md != "03-08":
        return False
    s_start = _to_comparable_dt(start_time)
    s_end = _to_comparable_dt(end_time)
    if not s_start or not s_end or len(s_start) < 16 or len(s_end) < 16:
        return False
    try:
        sh = int(s_start[11:13])
        sm = int(s_start[14:16])
        eh = int(s_end[11:13])
        em = int(s_end[14:16])
    except Exception:
        return False
    s_dec = sh + sm / 60.0
    e_dec = eh + em / 60.0
    # 完全落在 13:00-17:00 之间
    return s_dec >= 13.0 and e_dec <= 17.0


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
    """将 DB 返回的 datetime/date 转为可比较的字符串，统一为 19 位 YYYY-MM-DD HH:MM:SS（闭区间比较，与历史请假/加班数据一致）"""
    if val is None:
        return None
    if hasattr(val, "strftime"):
        out = val.strftime("%Y-%m-%d %H:%M:%S") if hasattr(val, "hour") else val.strftime("%Y-%m-%d") + " 00:00:00"
        return out[:19]
    s = str(val).strip()
    if "." in s:
        s = s.split(".")[0]
    if len(s) >= 19:
        return s[:19]
    if len(s) == 10:
        return s + " 00:00:00"
    # 历史数据可能为 YYYY-MM-DD HH:MM（16 位），补全为 HH:MM:00 再比较，避免与建议的 19 位不一致导致“已申报”不匹配
    if len(s) == 16 and s[10] == " " and ":" in s[11:]:
        return s + ":00"
    return s


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


def _interval_overlaps(
    s_start: str,
    s_end: str,
    rows: List[Dict],
    get_start_end,
) -> bool:
    """建议区间 [s_start, s_end] 与 rows 中任一条 [r_start, r_end] 存在交集（闭区间，端点相接也算）。"""
    for r in rows:
        r_start, r_end = get_start_end(r)
        r_start = _to_comparable_dt(r_start)
        r_end = _to_comparable_dt(r_end)
        if not r_start or not r_end or r_start > r_end:
            continue
        if s_start <= r_end and r_start <= s_end:
            return True
    return False


def _work_time_segments_excluding_lunch(s_start: str, s_end: str) -> List[tuple[str, str]]:
    """
    将建议区间按自然日切开，并在每个工作日内去掉 12:00–13:00 午休（不计考勤）。
    返回若干闭区间 [a,b]（字符串可比较），用于判断「有效工作时段」是否被请假/公出覆盖。
    """
    try:
        t0 = datetime.strptime(s_start[:19], "%Y-%m-%d %H:%M:%S")
        t1 = datetime.strptime(s_end[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return []
    if t1 < t0:
        return []
    out: List[tuple[str, str]] = []
    d = t0.date()
    end_d = t1.date()
    while d <= end_d:
        day_lo = datetime.combine(d, dt_time(0, 0, 0))
        day_hi = datetime.combine(d, dt_time(23, 59, 59))
        seg_lo = max(t0, day_lo)
        seg_hi = min(t1, day_hi)
        if seg_lo <= seg_hi:
            am_end = datetime.combine(d, dt_time(12, 0, 0))
            pm_start = datetime.combine(d, dt_time(13, 0, 0))
            m0 = seg_lo
            m1 = min(seg_hi, am_end)
            if m0 <= m1:
                out.append((m0.strftime("%Y-%m-%d %H:%M:%S"), m1.strftime("%Y-%m-%d %H:%M:%S")))
            a0 = max(seg_lo, pm_start)
            a1 = seg_hi
            if a0 <= a1:
                out.append((a0.strftime("%Y-%m-%d %H:%M:%S"), a1.strftime("%Y-%m-%d %H:%M:%S")))
        d += timedelta(days=1)
    return out


def _merge_interval_str_pairs(pairs: List[tuple[str, str]]) -> List[tuple[str, str]]:
    """合并重叠或端点相接的区间，返回按起点排序的不相交列表。"""
    norm: List[tuple[str, str]] = []
    for a, b in pairs:
        ca = _to_comparable_dt(a)
        cb = _to_comparable_dt(b)
        if not ca or not cb or ca > cb:
            continue
        norm.append((ca, cb))
    norm.sort(key=lambda x: x[0])
    if not norm:
        return []
    merged: List[tuple[str, str]] = [norm[0]]
    for a, b in norm[1:]:
        la, lb = merged[-1]
        if a <= lb:
            nb = b if b > lb else lb
            merged[-1] = (la, nb)
        else:
            merged.append((a, b))
    return merged


def _inclusive_segment_covered_by_merged(need_lo: str, need_hi: str, merged: List[tuple[str, str]]) -> bool:
    """闭区间 [need_lo, need_hi] 的每一时刻是否都落在 merged 区间的并集内。"""
    if not merged:
        return False
    try:
        a = datetime.strptime(need_lo[:19], "%Y-%m-%d %H:%M:%S")
        b = datetime.strptime(need_hi[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return False
    if a > b:
        return True
    need = a
    while need <= b:
        found = False
        for ms, me in merged:
            msv = datetime.strptime(ms[:19], "%Y-%m-%d %H:%M:%S")
            mev = datetime.strptime(me[:19], "%Y-%m-%d %H:%M:%S")
            if msv <= need <= mev:
                need = mev + timedelta(seconds=1)
                found = True
                break
        if not found:
            return False
        if need > b:
            return True
    return True


def _absence_covered_by_qj_and_gcsqb_patched(
    s_start: str,
    s_end: str,
    qj_rows: List[Dict],
    gcsqb_rows: List[Dict],
) -> bool:
    """
    status=1 缺勤建议：请假 + 公出可拼凑覆盖；按工作日扣除 12:00–13:00 后再判断。
    任一「有效工作子区间」未被并集盖住则未处理完成。
    """
    required = _work_time_segments_excluding_lunch(s_start, s_end)
    if not required:
        return False
    raw_pairs: List[tuple[str, str]] = []
    for r in qj_rows or []:
        raw_pairs.append((r.get("timefrom"), r.get("timeto")))
    for r in gcsqb_rows or []:
        raw_pairs.append(
            (r.get("yjcfsj") or r.get("gcsj"), r.get("yjfhsj") or r.get("sjfhtime"))
        )
    merged = _merge_interval_str_pairs(raw_pairs)
    if not merged:
        return False
    for seg_lo, seg_hi in required:
        if not _inclusive_segment_covered_by_merged(seg_lo, seg_hi, merged):
            return False
    return True


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
    status=0(加班): 与某条 jiaban(已通过) 的 [timefrom,timeto] 有交集即可（含手动填报区间短于建议区间的情况）；
    status=1(缺勤): 单条 qj / gcsqb 整段包含建议区间，或多条请假+公出拼凑覆盖；
                   覆盖判定按自然日扣除 12:00–13:00 午休后再比较（与 8 小时工作制一致）。
                   公出优先 yjcfsj/yjfhsj，缺省回退 gcsj/sjfhtime。
    """
    s_start = _to_comparable_dt(start_time)
    s_end = _to_comparable_dt(end_time)
    if not s_start or not s_end:
        return False
    if status == 0:
        return _interval_overlaps(s_start, s_end, jiaban_rows, lambda r: (r.get("timefrom"), r.get("timeto")))
    if status == 1:
        # 单条整段覆盖（兼容旧数据）
        if _interval_covered(s_start, s_end, qj_rows, lambda r: (r.get("timefrom"), r.get("timeto"))):
            return True
        if _interval_covered(
            s_start,
            s_end,
            gcsqb_rows,
            lambda r: (r.get("yjcfsj") or r.get("gcsj"), r.get("yjfhsj") or r.get("sjfhtime")),
        ):
            return True
        # 多段请假/公出拼凑 + 扣除午休 12:00–13:00
        return _absence_covered_by_qj_and_gcsqb_patched(s_start, s_end, qj_rows, gcsqb_rows)
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
    status=0: 与 jiaban(jiabanzt in 0,1,3) 的时间段有交集即可；
    status=1: 单条覆盖或多条 qj+gcsqb 拼凑覆盖（扣除 12:00–13:00 午休），规则同 _suggestion_handled。
    """
    s_start = _to_comparable_dt(start_time)
    s_end = _to_comparable_dt(end_time)
    if not s_start or not s_end:
        return False
    if status == 0:
        return _interval_overlaps(s_start, s_end, jiaban_pending, lambda r: (r.get("timefrom"), r.get("timeto")))
    if status == 1:
        if _interval_covered(s_start, s_end, qj_pending, lambda r: (r.get("timefrom"), r.get("timeto"))):
            return True
        if _interval_covered(
            s_start,
            s_end,
            gcsqb_pending,
            lambda r: (r.get("yjcfsj") or r.get("gcsj"), r.get("yjfhsj") or r.get("sjfhtime")),
        ):
            return True
        return _absence_covered_by_qj_and_gcsqb_patched(s_start, s_end, qj_pending, gcsqb_pending)
    return False


def get_attendance_exception_keys(year: int, month: int, include_buban: bool = False) -> List[tuple]:
    """
    计算指定年月下所有「考勤异常」的 (employee_name, department, date_str)。
    异常定义：智能建议中 status=1（需请假/缺勤）且既未完成请假/公出，也未在审核中覆盖。
    include_buban=True 时包含部办人员（供打卡管理员使用）。

    性能优化：使用批量查询替代逐人查询（6 条 SQL 代替 N×6 条）。
    """
    try:
        attendance_db.ensure_suggestions_table()
        employees = attendance_db.get_distinct_employees_for_suggestions(year, month)
        emp_list = []
        for emp in employees:
            name = emp.get("employee_name")
            dept = (emp.get("department") or "").strip()
            if not name or not dept:
                continue
            if dept == "部办" and not include_buban:
                continue
            emp_list.append((name, dept))

        if not emp_list:
            return []

        names = list({n for n, _ in emp_list})

        # ---------- 批量查询性别 ----------
        female_set = set()
        try:
            ph = ",".join(["%s"] * len(names))
            gender_rows = db.execute_query(
                f"SELECT name, xbie FROM yggl WHERE name IN ({ph}) AND COALESCE(zaizhi,0)=0",
                tuple(names),
            )
            for r in gender_rows:
                if "女" in (r.get("xbie") or ""):
                    female_set.add((r.get("name") or "").strip())
        except Exception:
            pass

        # ---------- 批量查询所有建议 ----------
        all_suggestions = {}
        try:
            sugg_sql = """
                SELECT employee_name, department, DATE(start_time) AS date,
                       day_type AS dayType, message AS suggestion,
                       start_time, end_time, status
                FROM attendance_suggestions
                WHERE year = %s AND month = %s AND status = 1
                ORDER BY start_time
            """
            sugg_rows = db.execute_query(sugg_sql, (year, month))
            for r in sugg_rows:
                key = ((r.get("employee_name") or "").strip(), (r.get("department") or "").strip())
                all_suggestions.setdefault(key, []).append({
                    "date": str(r.get("date") or ""),
                    "start_time": r.get("start_time"),
                    "end_time": r.get("end_time"),
                    "status": r.get("status") if r.get("status") is not None else 0,
                })
        except Exception as e:
            logger.error(f"批量查询建议失败: {e}")
            return []

        # ---------- 批量查询已通过/审核中记录 ----------
        # 用区间重叠：timefrom < month_end AND timeto >= month_start，匹配跨月记录
        batch_month_start = f"{year}-{month:02d}-01"
        batch_month_end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"

        def _batch_by_name(rows, name_field="xm"):
            m = {}
            for r in rows:
                n = (r.get(name_field) or "").strip()
                if n:
                    m.setdefault(n, []).append(r)
            return m

        jiaban_approved_map, jiaban_pending_map = {}, {}
        qj_approved_map, qj_pending_map = {}, {}
        gcsqb_approved_map, gcsqb_pending_map = {}, {}

        try:
            ph = ",".join(["%s"] * len(names))
            jiaban_approved_map = _batch_by_name(db.execute_query(
                f"SELECT xm, timefrom, timeto FROM jiaban WHERE xm IN ({ph}) AND jiabanzt = 4 AND timefrom < %s AND timeto >= %s",
                tuple(names) + (batch_month_end, batch_month_start),
            ))
            qj_approved_map = _batch_by_name(db.execute_query(
                f"SELECT xm, timefrom, timeto FROM qj WHERE xm IN ({ph}) AND qjzt = 4 AND timefrom < %s AND timeto >= %s",
                tuple(names) + (batch_month_end, batch_month_start),
            ))
            gcsqb_approved_map = _batch_by_name(db.execute_query(
                f"SELECT gcr AS xm, yjcfsj, yjfhsj, gcsj, sjfhtime FROM gcsqb "
                f"WHERE gcr IN ({ph}) AND bldzt = 2 AND szrzt = 2 "
                f"AND (yjcfsj IS NOT NULL OR yjfhsj IS NOT NULL) "
                f"AND COALESCE(yjcfsj, gcsj) < %s AND COALESCE(yjfhsj, sjfhtime, yjcfsj, gcsj) >= %s",
                tuple(names) + (batch_month_end, batch_month_start),
            ))
            jiaban_pending_map = _batch_by_name(db.execute_query(
                f"SELECT xm, timefrom, timeto FROM jiaban WHERE xm IN ({ph}) AND jiabanzt IN (0,1,3,5) AND timefrom < %s AND timeto >= %s",
                tuple(names) + (batch_month_end, batch_month_start),
            ))
            qj_pending_map = _batch_by_name(db.execute_query(
                f"SELECT xm, timefrom, timeto FROM qj WHERE xm IN ({ph}) AND qjzt IN (0,1,3) AND timefrom < %s AND timeto >= %s",
                tuple(names) + (batch_month_end, batch_month_start),
            ))
            gcsqb_pending_map = _batch_by_name(db.execute_query(
                f"SELECT gcr AS xm, yjcfsj, yjfhsj, gcsj, sjfhtime FROM gcsqb "
                f"WHERE gcr IN ({ph}) AND (bldzt != 2 OR szrzt != 2) AND bldzt != 22 AND szrzt != 22 "
                f"AND (yjcfsj IS NOT NULL OR yjfhsj IS NOT NULL) "
                f"AND COALESCE(yjcfsj, gcsj) < %s AND COALESCE(yjfhsj, sjfhtime, yjcfsj, gcsj) >= %s",
                tuple(names) + (batch_month_end, batch_month_start),
            ))
        except Exception as e:
            logger.warning(f"批量查询已处理/审核中区间失败: {e}")

        # ---------- 逐人判定异常 ----------
        exception_keys = []
        for name, dept in emp_list:
            key = (name, dept)
            rows = all_suggestions.get(key, [])
            if not rows:
                continue
            is_female = name in female_set
            jiaban_rows = jiaban_approved_map.get(name, [])
            qj_rows = qj_approved_map.get(name, [])
            gcsqb_rows = gcsqb_approved_map.get(name, [])
            jiaban_pending = jiaban_pending_map.get(name, [])
            qj_pending = qj_pending_map.get(name, [])
            gcsqb_pending = gcsqb_pending_map.get(name, [])

            for r in rows:
                st = r.get("status") if r.get("status") is not None else 0
                if st != 1:
                    continue
                if is_female and _is_march8_pm_interval(r.get("date"), r.get("start_time"), r.get("end_time")):
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


def _parse_time_val(time_val) -> Optional[datetime]:
    """将数据库中的时间值解析为 datetime，失败返回 None"""
    if not time_val or time_val == "":
        return None
    if isinstance(time_val, datetime):
        return time_val
    if isinstance(time_val, str):
        try:
            return datetime.strptime(time_val, "%H:%M:%S")
        except Exception:
            pass
    return None


def collect_valid_times(record: dict) -> List[datetime]:
    """收集所有有效的打卡时间（向后兼容接口）"""
    times = []
    for i in range(1, 11):
        t = _parse_time_val(record.get(f"time_{i}"))
        if t is not None:
            times.append(t)
    return times


def collect_valid_times_with_marks(record: dict) -> List[tuple]:
    """
    收集所有有效的 (time, mark) 对。
    mark: 0=进, 1=出, None=未知。返回按时间排序的列表。
    """
    pairs = []
    for i in range(1, 11):
        t = _parse_time_val(record.get(f"time_{i}"))
        if t is None:
            continue
        raw_mark = record.get(f"time_{i}_mark")
        mark = int(raw_mark) if raw_mark is not None and str(raw_mark).strip() != "" else None
        pairs.append((t, mark))
    pairs.sort(key=lambda x: x[0])
    return pairs


def build_intervals_from_marks(time_mark_pairs: List[tuple]) -> List[tuple]:
    """
    根据进(0)/出(1)标记构建进出区间。
    - 遇到「进」时记录为区间起点（连续多次「进」取第一次）
    - 遇到「出」时与最近的「进」配对形成区间（无配对的「出」忽略）
    - 若所有 mark 都为 None，回退到按下标两两配对的旧逻辑
    """
    if not time_mark_pairs:
        return []

    has_any_mark = any(m is not None for _, m in time_mark_pairs)

    if not has_any_mark:
        intervals = []
        for i in range(0, len(time_mark_pairs) - 1, 2):
            t_in = time_mark_pairs[i][0]
            t_out = time_mark_pairs[i + 1][0]
            if t_out > t_in:
                intervals.append((t_in, t_out))
        return intervals

    intervals = []
    current_in = None

    for t, mark in time_mark_pairs:
        if mark == 0:  # 进
            if current_in is None:
                current_in = t
        elif mark == 1:  # 出
            if current_in is not None:
                if t > current_in:
                    intervals.append((current_in, t))
                current_in = None
        else:
            # mark 为 None：根据上下文推断——如果没有待配对的入，视为进；否则视为出
            if current_in is None:
                current_in = t
            else:
                if t > current_in:
                    intervals.append((current_in, t))
                current_in = None

    return intervals


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
    """分析工作日打卡记录，生成建议（按进/出标记配对区间）。返回 List[dict] 含 start_time, end_time, status, message。"""
    suggestions: List[dict] = []

    # 1. 收集带进出标记的打卡时间，并构建区间
    time_mark_pairs = collect_valid_times_with_marks(record)
    if not time_mark_pairs:
        return suggestions

    # 工作时间与加班时间常量
    WORK_AM_START = 8      # 上午上班开始
    WORK_AM_END = 12       # 上午下班
    WORK_PM_START = 13     # 下午上班开始
    WORK_PM_END = 17       # 正常下班
    OVERTIME_START = 17    # 工作日加班起点
    OVERTIME_END = 24      # 统计到 24:00
    OVERTIME_MIN_HOURS = 1 # 加班至少 1 小时

    def decimal_to_dt(base_date: datetime, h: float) -> datetime:
        """将小时时间(如 17.5) 转为 datetime，含秒，与 time_to_decimal 精度一致"""
        hour = int(h)
        rest_sec = (h - hour) * 3600
        minute = int(rest_sec // 60)
        second = int(round(rest_sec - minute * 60))
        if second >= 60:
            second = 0
            minute += 1
        if minute >= 60:
            minute = 0
            hour += 1
        return base_date.replace(hour=hour, minute=minute, second=second, microsecond=0)

    # -------------------------------------------------
    # 2. 迟到 / 缺勤检测（基于当天第一次「进」的时间，不按午休分段）
    #    8 < first < 12   → 迟到：8:00 → first
    #    12 <= first < 17 → 缺勤：8:00 → first（含午休，请假时系统自动扣除）
    #    first >= 17      → 全天缺勤：8:00 → 17:00
    # -------------------------------------------------
    first_in_time = None
    for t, m in time_mark_pairs:
        if m == 0 or m is None:
            first_in_time = t
            break
    if first_in_time is None:
        first_in_time = time_mark_pairs[0][0]

    first_val = time_to_decimal(first_in_time)

    if WORK_AM_START < first_val < WORK_AM_END:
        suggestions.append(_sugg(
            "08:00:00", format_time(first_in_time), 1,
            f"【考勤建议】检测到迟到，建议补录 08:00 到 {format_time(first_in_time)} 的考勤"
        ))
    elif WORK_AM_END <= first_val < WORK_PM_END:
        suggestions.append(_sugg(
            "08:00:00", format_time(first_in_time), 1,
            f"【考勤建议】检测到缺勤，建议补录 08:00 到 {format_time(first_in_time)} 的考勤"
        ))
    elif first_val >= WORK_PM_END:
        suggestions.append(_sugg(
            "08:00:00", "17:00:00", 1,
            "【考勤建议】检测到全天缺勤，建议补录 8:00 到 17:00 的考勤（全天）"
        ))

    # -------------------------------------------------
    # 3. 根据进/出标记构建（刷入，刷离）区间
    # -------------------------------------------------
    intervals = build_intervals_from_marks(time_mark_pairs)

    # -------------------------------------------------
    # 3b. 早班前到岗但未待到工作时段的补充检测
    #     当 first_val <= 8 时，step 2 不会触发任何分支（视为"准时到岗"），
    #     但实际可能在 8:00 前就离开了。需要通过区间判断真正覆盖工作时段的"有效首次到岗时间"。
    # -------------------------------------------------
    if first_val <= WORK_AM_START and intervals:
        eff_work_start = None
        for t_in, t_out in intervals:
            iv_in = time_to_decimal(t_in)
            iv_out = time_to_decimal(t_out)
            if iv_out <= WORK_AM_START:
                continue
            if iv_in <= WORK_AM_START:
                eff_work_start = WORK_AM_START
                break
            else:
                eff_work_start = iv_in
                break

        if eff_work_start is None:
            suggestions.append(_sugg(
                "08:00:00", "17:00:00", 1,
                "【考勤建议】检测到全天缺勤，建议补录 8:00 到 17:00 的考勤（全天）"
            ))
        elif eff_work_start > WORK_AM_START:
            eff_dt = decimal_to_dt(date_obj, eff_work_start)
            if eff_work_start < WORK_AM_END:
                suggestions.append(_sugg(
                    "08:00:00", format_time(eff_dt), 1,
                    f"【考勤建议】检测到迟到，建议补录 08:00 到 {format_time(eff_dt)} 的考勤"
                ))
            elif WORK_AM_END <= eff_work_start < WORK_PM_END:
                suggestions.append(_sugg(
                    "08:00:00", format_time(eff_dt), 1,
                    f"【考勤建议】检测到缺勤，建议补录 08:00 到 {format_time(eff_dt)} 的考勤"
                ))
            elif eff_work_start >= WORK_PM_END:
                suggestions.append(_sugg(
                    "08:00:00", "17:00:00", 1,
                    "【考勤建议】检测到全天缺勤，建议补录 8:00 到 17:00 的考勤（全天）"
                ))

    # -------------------------------------------------
    # 4. 缺勤检查逻辑：
    #    规则：如果刷离时间在工作时段（8:00–17:00 开区间）内，则 "刷离时间 → 下次刷入时间" 为缺勤。
    #    午休 12:00–13:00 不再分段——请假时系统会自动扣除午休，无需拆成两条建议。
    # -------------------------------------------------
    for idx, (t_in, t_out) in enumerate(intervals):
        out_val = time_to_decimal(t_out)

        if not (WORK_AM_START < out_val < WORK_PM_END):
            continue

        gap_start = t_out
        gap_start_val = out_val

        if idx + 1 < len(intervals):
            next_in = intervals[idx + 1][0]
            next_in_val = time_to_decimal(next_in)

            if next_in_val > WORK_PM_END:
                gap_end = gap_start.replace(hour=WORK_PM_END, minute=0, second=0, microsecond=0)
            else:
                gap_end = next_in

            if gap_end > gap_start:
                suggestions.append(_sugg(
                    format_time(gap_start), format_time(gap_end), 1,
                    f"【考勤建议】检测到缺勤，建议补录 {format_time(gap_start)} 到 {format_time(gap_end)} 的考勤"
                ))
        else:
            if gap_start_val < WORK_PM_END:
                end_dt = gap_start.replace(hour=WORK_PM_END, minute=0, second=0, microsecond=0)
                suggestions.append(_sugg(
                    format_time(gap_start), format_time(end_dt), 1,
                    f"【考勤建议】检测到缺勤，建议补录 {format_time(gap_start)} 到 {format_time(end_dt)} 的考勤"
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


def _generate_segment_suggestion(
    segment_pairs: List[tuple],
    date_obj: datetime,
    noon_start: float,
    noon_end: float,
    ot_start_hour: float,
    min_hours: float,
) -> Optional[dict]:
    """
    对一组连续的进出对（已确认间隔紧密），判断是否需要分段或合并，
    生成一条加班建议。返回 None 表示该段不够最小时长。
    """
    has_lunch_leave = False
    for k in range(len(segment_pairs) - 1):
        end_val = time_to_decimal(segment_pairs[k][1])
        next_start = time_to_decimal(segment_pairs[k + 1][0])
        if end_val < noon_start and next_start > noon_start:
            has_lunch_leave = True
            break

    results: List[dict] = []
    if has_lunch_leave:
        for s_time, e_time in segment_pairs:
            s_val = time_to_decimal(s_time)
            e_val = time_to_decimal(e_time)
            if s_val >= e_val:
                continue
            eff_start = max(s_val, ot_start_hour)
            if noon_start <= eff_start < noon_end:
                eff_start = noon_end
            if eff_start >= e_val:
                continue
            duration = e_val - eff_start
            if duration < min_hours:
                continue
            if s_val < ot_start_hour:
                start_str = "08:00:00"
            elif noon_start <= s_val < noon_end:
                start_str = "13:00:00"
            else:
                start_str = format_time(s_time)
            end_str = format_time(e_time)
            results.append(_sugg(
                start_str, end_str, 0,
                f"【加班建议】休息日加班，建议补录 {start_str} 到 {end_str} 的加班（约{_format_hours_display(duration)}）"
            ))
    else:
        first_time = segment_pairs[0][0]
        last_time = segment_pairs[-1][1]
        start_val = time_to_decimal(first_time)
        end_val = time_to_decimal(last_time)
        if start_val >= end_val:
            return results

        eff_start = max(start_val, ot_start_hour)
        if noon_start <= eff_start < noon_end:
            eff_start = noon_end
        eff_end = end_val
        if noon_start < end_val <= noon_end:
            eff_end = noon_start
        if eff_start >= eff_end:
            return results

        if eff_start < noon_start and eff_end > noon_end:
            total_hours = (eff_end - eff_start) - (noon_end - noon_start)
        else:
            overlap = max(0, min(eff_end, noon_end) - max(eff_start, noon_start))
            total_hours = (eff_end - eff_start) - overlap

        if total_hours < min_hours:
            return results
        start_str = "08:00:00" if start_val < ot_start_hour else format_time(first_time)
        end_str = format_time(last_time)
        results.append(_sugg(
            start_str, end_str, 0,
            f"【加班建议】休息日加班，建议补录 {start_str} 到 {end_str} 的加班（约{_format_hours_display(total_hours)}）"
        ))
    return results


def analyze_restday(record: dict, date_obj: datetime) -> List[dict]:
    """
    分析休息日/假期打卡记录，生成建议。返回 List[dict] 含 start_time, end_time, status=0, message。
    逻辑：
    - 根据进/出标记配对构建进出区间。
    - 各区间独立生成建议。
    - 段内若存在「午休前离岗、午休后返岗」则按子段分别建议；否则合并为一段，跨午休扣除实际重叠。
    """
    suggestions: List[dict] = []

    time_mark_pairs = collect_valid_times_with_marks(record)
    if not time_mark_pairs:
        return suggestions

    NOON_START = 12
    NOON_END = 13
    OT_START_HOUR = 8
    RESTDAY_OVERTIME_MIN_HOURS = 1.0

    intervals = build_intervals_from_marks(time_mark_pairs)

    pairs: List[tuple] = []
    for t_in, t_out in intervals:
        dur = time_to_decimal(t_out) - time_to_decimal(t_in)
        if dur >= RESTDAY_OVERTIME_MIN_HOURS:
            pairs.append((t_in, t_out))

    if not pairs:
        return suggestions

    for pair in pairs:
        seg_results = _generate_segment_suggestion(
            [pair], date_obj, NOON_START, NOON_END, OT_START_HOUR, RESTDAY_OVERTIME_MIN_HOURS
        )
        if seg_results:
            suggestions.extend(seg_results)

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
        records: List[Dict], holidays: Dict[str, str],
        cutoff_date_str: Optional[str] = None) -> List[Dict]:
    """同 generate_suggestions_for_month，但直接接受已查好的 records 和 holidays，避免重复查库。
    cutoff_date_str: 形如 'YYYY-MM-DD'，当月仅生成截止到此日期的建议；为 None 时用 today。"""
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
    if year == today.year and month == today.month:
        check_end_date = today
        if cutoff_date_str:
            try:
                cutoff_dt = datetime.strptime(cutoff_date_str, "%Y-%m-%d")
                if cutoff_dt < check_end_date:
                    check_end_date = cutoff_dt
            except ValueError:
                pass
    else:
        check_end_date = last_day_of_month
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
        if date_obj > check_end_date:
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
                                   holidays_cache: Dict[str, Dict] = None,
                                   cutoff_date_str: Optional[str] = None) -> List[Dict]:
    """
    为指定人、指定年月生成智能建议（供上传后写入表或离线使用）。
    holidays_cache: 可选，{year_str: holidays_dict}，避免同年重复查库。
    cutoff_date_str: 形如 'YYYY-MM-DD'，当月仅生成截止到此日期的建议；为 None 时用 today。
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
        if cutoff_date_str:
            try:
                cutoff_dt = datetime.strptime(cutoff_date_str, "%Y-%m-%d")
                if cutoff_dt < check_end_date:
                    check_end_date = cutoff_dt
            except ValueError:
                pass
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
        if date_obj > check_end_date:
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
        is_female = _is_female_employee(name)
        if year is not None and month is not None and 1 <= month <= 12:
            attendance_db.ensure_suggestions_table()
            rows = attendance_db.get_suggestions(name, dept, year, month)
            jiaban_rows, qj_rows, gcsqb_rows = [], [], []
            jiaban_pending, qj_pending, gcsqb_pending = [], [], []
            # 用区间重叠查询，解决跨月请假/加班匹配不到的问题
            month_start = f"{year}-{month:02d}-01"
            month_end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
            try:
                jiaban_rows = db.execute_query(
                    "SELECT timefrom, timeto FROM jiaban WHERE xm = %s AND jiabanzt = 4 AND timefrom < %s AND timeto >= %s",
                    (name, month_end, month_start),
                )
                qj_rows = db.execute_query(
                    "SELECT timefrom, timeto FROM qj WHERE xm = %s AND qjzt = 4 AND timefrom < %s AND timeto >= %s",
                    (name, month_end, month_start),
                )
                gcsqb_rows = db.execute_query(
                    "SELECT yjcfsj, yjfhsj, gcsj, sjfhtime FROM gcsqb "
                    "WHERE gcr = %s AND bldzt = 2 AND szrzt = 2 "
                    "AND (yjcfsj IS NOT NULL OR yjfhsj IS NOT NULL) "
                    "AND COALESCE(yjcfsj, gcsj) < %s AND COALESCE(yjfhsj, sjfhtime, yjcfsj, gcsj) >= %s",
                    (name, month_end, month_start),
                )
                jiaban_pending = db.execute_query(
                    "SELECT timefrom, timeto FROM jiaban WHERE xm = %s AND jiabanzt IN (0, 1, 3, 5) AND timefrom < %s AND timeto >= %s",
                    (name, month_end, month_start),
                )
                qj_pending = db.execute_query(
                    "SELECT timefrom, timeto FROM qj WHERE xm = %s AND qjzt IN (0, 1, 3) AND timefrom < %s AND timeto >= %s",
                    (name, month_end, month_start),
                )
                gcsqb_pending = db.execute_query(
                    "SELECT yjcfsj, yjfhsj, gcsj, sjfhtime FROM gcsqb "
                    "WHERE gcr = %s AND (bldzt != 2 OR szrzt != 2) AND bldzt != 22 AND szrzt != 22 "
                    "AND (yjcfsj IS NOT NULL OR yjfhsj IS NOT NULL) "
                    "AND COALESCE(yjcfsj, gcsj) < %s AND COALESCE(yjfhsj, sjfhtime, yjcfsj, gcsj) >= %s",
                    (name, month_end, month_start),
                )
            except Exception as e:
                logger.warning(f"查询已处理/审核中区间失败: {e}")
            suggestions_list = []
            for r in rows:
                st = r.get("status") if r.get("status") is not None else 0
                # 每年 3 月 8 日下午 13:00-17:00，女性员工不提示缺勤/请假建议
                if is_female and st == 1 and _is_march8_pm_interval(r.get("date"), r.get("start_time"), r.get("end_time")):
                    continue
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
        fb_month_start = f"{now.year}-{now.month:02d}-01"
        fb_month_end = f"{now.year + 1}-01-01" if now.month == 12 else f"{now.year}-{now.month + 1:02d}-01"
        try:
            jiaban_rows = db.execute_query(
                "SELECT timefrom, timeto FROM jiaban WHERE xm = %s AND jiabanzt = 4 AND timefrom < %s AND timeto >= %s",
                (name, fb_month_end, fb_month_start),
            )
            qj_rows = db.execute_query(
                "SELECT timefrom, timeto FROM qj WHERE xm = %s AND qjzt = 4 AND timefrom < %s AND timeto >= %s",
                (name, fb_month_end, fb_month_start),
            )
            gcsqb_rows = db.execute_query(
                "SELECT yjcfsj, yjfhsj, gcsj, sjfhtime FROM gcsqb "
                "WHERE gcr = %s AND bldzt = 2 AND szrzt = 2 "
                "AND (yjcfsj IS NOT NULL OR yjfhsj IS NOT NULL) "
                "AND COALESCE(yjcfsj, gcsj) < %s AND COALESCE(yjfhsj, sjfhtime, yjcfsj, gcsj) >= %s",
                (name, fb_month_end, fb_month_start),
            )
            jiaban_pending = db.execute_query(
                "SELECT timefrom, timeto FROM jiaban WHERE xm = %s AND jiabanzt IN (0, 1, 3, 5) AND timefrom < %s AND timeto >= %s",
                (name, fb_month_end, fb_month_start),
            )
            qj_pending = db.execute_query(
                "SELECT timefrom, timeto FROM qj WHERE xm = %s AND qjzt IN (0, 1, 3) AND timefrom < %s AND timeto >= %s",
                (name, fb_month_end, fb_month_start),
            )
            gcsqb_pending = db.execute_query(
                "SELECT yjcfsj, yjfhsj, gcsj, sjfhtime FROM gcsqb "
                "WHERE gcr = %s AND (bldzt != 2 OR szrzt != 2) AND bldzt != 22 AND szrzt != 22 "
                "AND (yjcfsj IS NOT NULL OR yjfhsj IS NOT NULL) "
                "AND COALESCE(yjcfsj, gcsj) < %s AND COALESCE(yjfhsj, sjfhtime, yjcfsj, gcsj) >= %s",
                (name, fb_month_end, fb_month_start),
            )
        except Exception as e:
            logger.warning(f"查询已处理/审核中区间失败: {e}")
        out = []
        for s in suggestions_list:
            st = s.get("status", 0)
            # 每年 3 月 8 日下午 13:00-17:00，女性员工不提示缺勤/请假建议
            if is_female and st == 1 and _is_march8_pm_interval(s.get("date"), s.get("start_time"), s.get("end_time")):
                continue
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

