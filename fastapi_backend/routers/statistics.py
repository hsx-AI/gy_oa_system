# -*- coding: utf-8 -*-
"""
科室统计 API - 请假/加班/公出按科室汇总
- 请假: qj 表, lsys, 仅已通过 qjzt=4
- 加班: jiaban 表, lsys, 仅已通过 jiabanzt=4
- 公出: gcsqb 表, lsysjm, 仅已批准 bldzt>=2 and szrzt>=2
领导人看板扩展：满勤率、科室横向对比、全员排序
- 统计与筛选中排除：名字末尾为1、科室(lsys)末尾为1（视为已离职人员/组织）
- 领导人看板统计中不参与：科室「部办」
"""
from fastapi import APIRouter, HTTPException, Query

# 领导人看板中不参与统计的科室（不计算人数、不参与排序与横向对比）
LEADER_EXCLUDE_LSYS = "部办"
# 不参与任何考勤/统计的虚拟科室
OTHER_DEPT_NAMES = ("其他部门员工", "其他部门成员")
# SQL 片段：用于 WHERE 条件中排除虚拟科室（拼接在已有 != 部办 之后）
_EXCL_OTHER = "AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') "
_EXCL_OTHER_YGGL = "AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') "
from typing import Optional, List, Tuple, Dict
from datetime import datetime, date
from database import db
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


INCENTIVE_FESTIVALS = {"春节", "国庆节", "高温防暑休假"}


def _load_holiday_festival_map(year: int) -> Dict[str, str]:
    """
    加载某年假期的 日期 -> 节日名称(festival) 映射。
    若 holiday 表中无 festival 或读取失败，则返回空字典。
    """
    try:
        from utils.holiday_loader import load_holidays_for_year

        rows = load_holidays_for_year(str(year))
        mapping: Dict[str, str] = {}
        for r in rows:
            date_str = (r.get("date") or "").strip()
            fest = (r.get("festival") or "").strip()
            if date_str:
                mapping[date_str] = fest
        return mapping
    except Exception:
        return {}


def _aggregate_overtime_with_incentive(
    rows: List[Dict],
    holiday_festival_map: Dict[str, str],
    zhibanfei: float,
):
    """
    对原始加班记录按「人+日期」聚合，并按节日激励规则计算：
    - 春节/国庆节/高温防暑休假 这三类节日当天：若当日加班时长(已扣午休) >= 8 小时，则固定奖励 200 元；
      超过 8 小时的部分按 zhibanfei 元/小时额外计算。
    - 其他日期或不足 8 小时的节日，其他绩效激励按 zhibanfei 元/小时计算。
    返回:
    - per_month: { "YYYY-MM": {"hours": 总小时数, "pay": 总金额} }
    - per_employee: { name: {"hours": 总小时数, "pay": 总金额} }
    """
    # 先按 (name, date_str) 聚合每天的小时数
    per_day: Dict[tuple, float] = defaultdict(float)
    for r in rows or []:
        name = (r.get("emp_name") or r.get("name") or "").strip()
        if not name:
            continue
        timedate = r.get("timedate")
        if timedate is None:
            continue
        date_str = str(timedate)[:10]
        if len(date_str) < 10:
            continue
        try:
            hours = float(r.get("hours") if r.get("hours") is not None else r.get("jbf") or 0)
        except (TypeError, ValueError):
            hours = 0.0
        if hours <= 0:
            continue
        per_day[(name, date_str)] += hours

    per_month: Dict[str, Dict[str, float]] = defaultdict(lambda: {"hours": 0.0, "pay": 0.0})
    per_employee: Dict[str, Dict[str, float]] = defaultdict(lambda: {"hours": 0.0, "pay": 0.0})

    for (name, date_str), day_hours in per_day.items():
        month_key = date_str[:7]
        festival = holiday_festival_map.get(date_str, "")
        is_incentive = festival in INCENTIVE_FESTIVALS

        incentive_pay = 0.0
        normal_hours = 0.0

        if is_incentive and day_hours >= 8.0:
            incentive_pay = 200.0
            normal_hours = day_hours - 8.0
        else:
            normal_hours = day_hours

        day_pay = incentive_pay + normal_hours * zhibanfei

        # 员工维度：小时数依然展示真实加班小时；金额为激励 + 普通小时费
        per_employee[name]["hours"] += day_hours
        per_employee[name]["pay"] += day_pay

        # 月维度：同样累计真实小时和金额
        per_month[month_key]["hours"] += day_hours
        per_month[month_key]["pay"] += day_pay

    return per_month, per_employee


def _parse_date(v) -> Optional[date]:
    """将 DB 返回的 datetime/str 转为 date"""
    if v is None:
        return None
    if hasattr(v, "date"):
        return v.date()
    s = str(v)[:10]
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def _merge_intervals_days(intervals: List[Tuple[date, date]]) -> float:
    """
    将多个 [start, end] 区间做并集后计算总天数（去重）。
    区间为闭区间，同一天算 1 天。
    """
    if not intervals:
        return 0.0
    sorted_list = sorted([(s, e) for s, e in intervals if s and e])
    if not sorted_list:
        return 0.0
    merged = []
    cur_s, cur_e = sorted_list[0]
    for s, e in sorted_list[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))
    return sum((e - s).days + 1 for s, e in merged)


def _qj_leave_date_bounds(row: Dict) -> Tuple[Optional[date], Optional[date]]:
    """请假记录的起止日期（闭区间）。优先 timefrom/timeto，缺省回退 timefromdate。"""
    start = _parse_date(row.get("timefrom")) or _parse_date(row.get("timefromdate"))
    end = _parse_date(row.get("timeto")) or start
    if start and end and end < start:
        start, end = end, start
    return start, end


def _allocate_leave_tian_to_period(
    tian: float, leave_start: date, leave_end: date, period_start: date, period_end: date
) -> float:
    """
    将整条请假的 tian 按「与统计区间相交的日历天数 / 请假整段日历天数」比例分摊。
    解决跨月/跨年请假只在「开始月」计满全部天数的问题。
    """
    try:
        tian_f = float(tian or 0)
    except (TypeError, ValueError):
        tian_f = 0.0
    if tian_f <= 0 or not leave_start or not leave_end:
        return 0.0
    total_span = (leave_end - leave_start).days + 1
    if total_span <= 0:
        return 0.0
    ov_s = max(leave_start, period_start)
    ov_e = min(leave_end, period_end)
    if ov_e < ov_s:
        return 0.0
    ov_days = (ov_e - ov_s).days + 1
    return tian_f * float(ov_days) / float(total_span)


def _leave_overlap_fraction(
    leave_start: date, leave_end: date, period_start: date, period_end: date
) -> float:
    """请假区间与统计区间日历重叠比例 (0~1]，用于将整笔换休小时分摊到当期。"""
    if not leave_start or not leave_end:
        return 0.0
    total_span = (leave_end - leave_start).days + 1
    if total_span <= 0:
        return 0.0
    ov_s = max(leave_start, period_start)
    ov_e = min(leave_end, period_end)
    if ov_e < ov_s:
        return 0.0
    ov_days = (ov_e - ov_s).days + 1
    return float(ov_days) / float(total_span)


def _qj_hx_row_total_hours(row: Dict) -> float:
    """单条换休类请假的总小时：优先 xiaoshi，否则 tian×8（与申请端一致）。"""
    try:
        xs_raw = row.get("xiaoshi")
        if xs_raw is not None and str(xs_raw).strip() != "":
            xs = float(str(xs_raw).strip().replace(",", "."))
            if xs > 0:
                return xs
    except (TypeError, ValueError):
        pass
    try:
        tian = float(row.get("tian") or 0)
    except (TypeError, ValueError):
        tian = 0.0
    return max(0.0, tian * 8.0)


def _leave_overlap_sql_bounds() -> str:
    """WHERE 片段：请假区间与 [ps, pe] 闭区间有交集（ps/pe 为 'YYYY-MM-DD' 字符串）。"""
    return """
            AND COALESCE(DATE(timefrom), DATE(timefromdate)) <= %s
            AND COALESCE(DATE(timeto), DATE(timefrom), DATE(timefromdate)) >= %s
        """


router = APIRouter(tags=["统计"])


def _count_workdays_in_month(year: int, month: int) -> int:
    """计算某月应出勤工作日数（考虑假期与调休）"""
    try:
        from utils.holiday_loader import load_holidays_dict
        holidays = load_holidays_dict(str(year))
    except Exception:
        holidays = {}
    count = 0
    try:
        import calendar
        _, last = calendar.monthrange(year, month)
        for day in range(1, last + 1):
            d = datetime(year, month, day)
            date_str = d.strftime("%Y-%m-%d")
            weekday = d.weekday()
            is_weekend = weekday in [5, 6]
            is_holiday = False
            if date_str in holidays:
                t = holidays[date_str] or ""
                if "假" in t or "休" in t:
                    is_holiday = True
            if date_str in holidays and "班" in holidays[date_str]:
                is_weekend = False
                is_holiday = False
            if not is_weekend and not is_holiday:
                count += 1
    except Exception as e:
        logger.warning(f"计算工作日失败: {e}, 使用当月天数估算")
        import calendar
        _, last = calendar.monthrange(year, month)
        count = min(last, 22)
    return count


def _get_lsysjm_list(lsys: str) -> List[str]:
    """根据 lsys 获取对应的 lsysjm 列表（用于公出表）"""
    if not lsys:
        return []
    rows = db.execute_query(
        "SELECT DISTINCT lsysjm FROM yggl WHERE lsys = %s AND lsysjm IS NOT NULL AND lsysjm != '' AND (COALESCE(zaizhi,0)=0)",
        (lsys,)
    )
    result = [r["lsysjm"].strip() for r in rows if r.get("lsysjm")]
    if not result and lsys:
        result = [lsys]  # 若无映射则用 lsys 本身
    return result


# ==================== 科室列表（部长/副部长可选任意科室） ====================

@router.get("/dept/lsys-list")
async def get_dept_lsys_list():
    """
    获取全部隶属科室列表（用于领导人看板：部长/副部长可下拉选择任意科室）
    返回: { success, list: ["部办", "科室A", ...] }
    """
    try:
        rows = db.execute_query(
            "SELECT DISTINCT lsys FROM yggl WHERE lsys IS NOT NULL AND lsys != '' "
            "AND RIGHT(TRIM(lsys), 1) != '1' "
            "AND TRIM(lsys) != %s "
            "AND TRIM(lsys) NOT IN ('其他部门员工', '其他部门成员') "
            "AND (COALESCE(zaizhi,0)=0) ORDER BY lsys",
            (LEADER_EXCLUDE_LSYS,)
        )
        list_data = [r["lsys"].strip() for r in rows if r.get("lsys")]
        return {"success": True, "list": list_data}
    except Exception as e:
        logger.error(f"科室列表查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 请假科室统计 ====================

@router.get("/dept/leave")
async def get_dept_leave_stats(
    lsys: Optional[str] = Query(None, description="隶属于室，不传或空为全员"),
    year: Optional[int] = None,
    month: Optional[int] = None,
    quarter: Optional[str] = None,
    hx_only: Optional[bool] = Query(False, description="为 true 时仅统计请假类型为换休、员工换休票的记录"),
):
    """
    科室请假统计（按人汇总天数）。不传 lsys 时为全员（排除部办）。
    返回: { totalDays, personCount, list: [{ name, days }] }
    仅统计 qjzt=4 已通过。
    hx_only=true 时仅 qjfs 为换休/员工换休票（TRIM 后匹配）。
    跨月/跨季请假按日历重叠比例将 tian 分摊到各统计区间（与领导人看板月份/季度/全年一致）。
    """
    try:
        import calendar

        if year is None:
            year = datetime.now().year
        all_staff = not (lsys and lsys.strip())

        if month:
            period_start = date(year, int(month), 1)
            period_end = date(year, int(month), calendar.monthrange(year, int(month))[1])
        elif quarter:
            q = str(quarter).strip()
            q_map = {"1": (1, 3), "2": (4, 6), "3": (7, 9), "4": (10, 12)}
            lo, hi = q_map.get(q, (1, 12))
            period_start = date(year, lo, 1)
            period_end = date(year, hi, calendar.monthrange(year, hi)[1])
        else:
            period_start = date(year, 1, 1)
            period_end = date(year, 12, 31)

        pe_str = period_end.strftime("%Y-%m-%d")
        ps_str = period_start.strftime("%Y-%m-%d")
        ov = _leave_overlap_sql_bounds()
        hx_filter = " AND TRIM(qjfs) IN ('换休','员工换休票')" if hx_only else ""

        if all_staff:
            query = f"""
                SELECT xm AS name, timefrom, timeto, timefromdate, CAST(tian AS DECIMAL(10,2)) AS tian
                FROM qj
                WHERE qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s
                {hx_filter}
                {ov}
            """
            rows = db.execute_query(query, (LEADER_EXCLUDE_LSYS, pe_str, ps_str))
        else:
            query = f"""
                SELECT xm AS name, timefrom, timeto, timefromdate, CAST(tian AS DECIMAL(10,2)) AS tian
                FROM qj
                WHERE lsys = %s AND qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1'
                {hx_filter}
                {ov}
            """
            rows = db.execute_query(query, (lsys, pe_str, ps_str))

        by_name: Dict[str, float] = defaultdict(float)
        for r in rows or []:
            name = (r.get("name") or "").strip()
            if not name:
                continue
            ls_d, le_d = _qj_leave_date_bounds(r)
            if not ls_d or not le_d:
                continue
            try:
                tian_f = float(r.get("tian") or 0)
            except (TypeError, ValueError):
                tian_f = 0.0
            alloc = _allocate_leave_tian_to_period(tian_f, ls_d, le_d, period_start, period_end)
            if alloc > 0:
                by_name[name] += alloc

        list_data = [{"name": n, "days": round(v, 2)} for n, v in sorted(by_name.items(), key=lambda x: -x[1])]
        total_days = sum(by_name.values())

        return {
            "success": True,
            "totalDays": round(total_days, 2),
            "personCount": len(list_data),
            "list": list_data
        }
    except Exception as e:
        logger.error(f"请假科室统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 加班科室统计 ====================


def _query_hx_hours_all(
    year: int,
    month: Optional[int] = None,
    quarter: Optional[str] = None,
    lsys: Optional[str] = None,
    all_staff: bool = True,
) -> Dict[str, float]:
    """
    统计期内每人应扣换休小时：qjzt=4 且 qjfs 为换休/员工换休票；
    与请假统计一致，按请假区间与统计期日历重叠比例分摊整笔小时；
    小时优先 xiaoshi，缺省按 tian×8。净加班 = 该人加班小时 − 该值。
    """
    import calendar

    if month:
        period_start = date(year, int(month), 1)
        period_end = date(year, int(month), calendar.monthrange(year, int(month))[1])
    elif quarter:
        q = str(quarter).strip()
        q_map = {"1": (1, 3), "2": (4, 6), "3": (7, 9), "4": (10, 12)}
        lo, hi = q_map.get(q, (1, 12))
        period_start = date(year, lo, 1)
        period_end = date(year, hi, calendar.monthrange(year, hi)[1])
    else:
        period_start = date(year, 1, 1)
        period_end = date(year, 12, 31)

    pe_str = period_end.strftime("%Y-%m-%d")
    ps_str = period_start.strftime("%Y-%m-%d")
    ov = _leave_overlap_sql_bounds()

    if all_staff:
        query = f"""
            SELECT TRIM(qj.xm) AS name, qj.timefrom, qj.timeto, qj.timefromdate,
                CAST(qj.tian AS DECIMAL(10,2)) AS tian, qj.xiaoshi
            FROM qj INNER JOIN yggl ON qj.xm = yggl.name
                AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1'
                AND TRIM(yggl.lsys) != %s AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)
            WHERE qj.qjzt = 4 AND TRIM(qj.qjfs) IN ('换休','员工换休票') AND RIGHT(TRIM(qj.xm), 1) != '1'
            {ov}
        """
        rows = db.execute_query(query, (LEADER_EXCLUDE_LSYS, pe_str, ps_str))
    else:
        query = f"""
            SELECT TRIM(qj.xm) AS name, qj.timefrom, qj.timeto, qj.timefromdate,
                CAST(qj.tian AS DECIMAL(10,2)) AS tian, qj.xiaoshi
            FROM qj INNER JOIN yggl ON qj.xm = yggl.name AND yggl.lsys = %s
                AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1'
                AND (COALESCE(yggl.zaizhi,0)=0)
            WHERE qj.qjzt = 4 AND TRIM(qj.qjfs) IN ('换休','员工换休票') AND RIGHT(TRIM(qj.xm), 1) != '1'
            {ov}
        """
        rows = db.execute_query(query, (lsys, pe_str, ps_str))

    by_name: Dict[str, float] = defaultdict(float)
    for r in rows or []:
        name = (r.get("name") or "").strip()
        if not name:
            continue
        ls_d, le_d = _qj_leave_date_bounds(r)
        if not ls_d or not le_d:
            continue
        h_full = _qj_hx_row_total_hours(r)
        if h_full <= 0:
            continue
        frac = _leave_overlap_fraction(ls_d, le_d, period_start, period_end)
        if frac <= 0:
            continue
        by_name[name] += h_full * frac

    return dict(by_name)


@router.get("/dept/overtime")
async def get_dept_overtime_stats(
    lsys: Optional[str] = Query(None, description="隶属于室，不传或空为全员"),
    year: Optional[int] = None,
    month: Optional[int] = None,
    quarter: Optional[str] = None,
    net: Optional[bool] = Query(False, description="true 时返回净加班（加班小时 - 换休请假小时）"),
):
    """
    科室加班统计（按人汇总小时）。不传 lsys 时为全员（排除部办）。
    net=true 时，每人加班小时减去该人在同期换休类请假（换休/员工换休票）应扣小时，
    与请假统计一致按日历重叠比例分摊；小时优先取 xiaoshi，缺省按 tian×8。
    返回: { totalHours, personCount, list: [{ name, hours }] }
    仅统计 jiabanzt=4 已通过
    """
    try:
        if year is None:
            year = __import__("datetime").datetime.now().year
        all_staff = not (lsys and lsys.strip())

        if all_staff:
            join_cond = "INNER JOIN yggl ON jiaban.xm = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) != %s AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)"
            join_param = (LEADER_EXCLUDE_LSYS,)
        else:
            join_cond = "INNER JOIN yggl ON jiaban.xm = yggl.name AND yggl.lsys = %s AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND (COALESCE(yggl.zaizhi,0)=0)"
            join_param = (lsys,)
        if month:
            month_str = f"{year}-{month:02d}"
            query = f"""
                SELECT TRIM(jiaban.xm) AS name, SUM(CAST(COALESCE(jiaban.tian1, 0) AS DECIMAL(10,2))) AS hours
                FROM jiaban {join_cond}
                WHERE jiaban.jiabanzt = 4
                AND (jiaban.timedate LIKE %s OR SUBSTRING(jiaban.timedate, 1, 7) = %s)
                GROUP BY TRIM(jiaban.xm)
                ORDER BY hours DESC
            """
            rows = db.execute_query(query, join_param + (f"{month_str}%", month_str))
        else:
            if quarter:
                if quarter == "1":
                    mon_cond = "MONTH(jiaban.timedate) BETWEEN 1 AND 3"
                elif quarter == "2":
                    mon_cond = "MONTH(jiaban.timedate) BETWEEN 4 AND 6"
                elif quarter == "3":
                    mon_cond = "MONTH(jiaban.timedate) BETWEEN 7 AND 9"
                else:
                    mon_cond = "MONTH(jiaban.timedate) BETWEEN 10 AND 12"
                query = f"""
                    SELECT TRIM(jiaban.xm) AS name, SUM(CAST(COALESCE(jiaban.tian1, 0) AS DECIMAL(10,2))) AS hours
                    FROM jiaban {join_cond}
                    WHERE jiaban.jiabanzt = 4
                    AND YEAR(jiaban.timedate) = %s AND {mon_cond}
                    GROUP BY TRIM(jiaban.xm)
                    ORDER BY hours DESC
                """
                rows = db.execute_query(query, join_param + (year,))
            else:
                query = f"""
                    SELECT TRIM(jiaban.xm) AS name, SUM(CAST(COALESCE(jiaban.tian1, 0) AS DECIMAL(10,2))) AS hours
                    FROM jiaban {join_cond}
                    WHERE jiaban.jiabanzt = 4
                    AND (jiaban.timedate LIKE %s OR YEAR(jiaban.timedate) = %s)
                    GROUP BY TRIM(jiaban.xm)
                    ORDER BY hours DESC
                """
                rows = db.execute_query(query, join_param + (f"{year}%", year))

        ot_map = {}
        for r in rows:
            n = (r.get("name") or "").strip()
            if n:
                ot_map[n] = float(r.get("hours") or 0)

        hx_map: Dict[str, float] = {}
        if net:
            hx_map = _query_hx_hours_all(year, month, quarter, lsys, all_staff)
            for n in hx_map:
                if n not in ot_map:
                    ot_map[n] = 0

        if net:
            all_names = sorted(ot_map, key=lambda k: -(ot_map[k] - hx_map.get(k, 0)))
        else:
            all_names = sorted(ot_map, key=lambda k: -ot_map[k])

        list_data = []
        total_hours = 0
        for n in all_names:
            h = round(ot_map[n] - hx_map.get(n, 0), 2) if net else round(ot_map[n], 2)
            list_data.append({"name": n, "hours": h})
            total_hours += h

        return {
            "success": True,
            "totalHours": round(total_hours, 2),
            "personCount": len(list_data),
            "list": list_data
        }
    except Exception as e:
        logger.error(f"加班科室统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _apply_overtime_pay_scope(
    scope: Optional[str],
    current_user: Optional[str],
    scope_lsys: Optional[str],
    lsys: Optional[str],
    name: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """按其他绩效激励统计页权限 scope 强制修正 lsys/name。返回 (lsys, name)。"""
    if not current_user or not scope:
        return lsys, name
    if scope == "self":
        return None, (current_user or "").strip()
    if scope == "lsys" and scope_lsys:
        return (scope_lsys or "").strip(), None
    return lsys, name


@router.get("/dept/overtime-pay-by-month")
async def get_dept_overtime_pay_by_month(
    lsys: Optional[str] = Query(None, description="隶属于室，不传或空为全员"),
    year: Optional[int] = None,
    month: Optional[int] = Query(None, ge=1, le=12, description="筛选月份，不传为全年"),
    name: Optional[str] = Query(None, description="仅查某人（如普通员工查本人）"),
    current_user: Optional[str] = Query(None, description="当前登录用户，与 scope 配合做权限过滤"),
    scope: Optional[str] = Query(None, description="可见范围：self=本人, lsys=本室, all=全部门"),
    scope_lsys: Optional[str] = Query(None, description="scope=lsys 时本室名称"),
):
    """
    其他绩效激励按月份统计。仅统计 jiaban 审核完成(jiabanzt=4)、换休票为否(hx 非「是」)，
    激励规则：
    - 若某天是假期表中节日为 春节/国庆节/高温防暑休假，且当天加班时长(已扣午休) >= 8 小时，则固定奖励 200 元，
      超出 8 小时部分按 zhibanfei 元/小时额外计算；
    - 其他日期或不足 8 小时部分，按 webconfig.zhibanfei（默认 15 元/小时）计算；
    支持 name=某人 仅查本人；month=1~12 仅查该月。
    当传入 current_user+scope 时按权限强制过滤：self 仅本人，lsys 仅本室，all 不限制。
    返回: { success, zhibanfei, list: [{ month, monthLabel, hours, pay }] }
    """
    try:
        lsys, name = _apply_overtime_pay_scope(scope, current_user, scope_lsys, lsys, name)
        if year is None:
            year = datetime.now().year
        zhibanfei = 15.0
        try:
            wc = db.execute_query("SELECT zhibanfei FROM webconfig WHERE id = 1 LIMIT 1")
            if wc and wc[0].get("zhibanfei") is not None:
                zhibanfei = float(wc[0]["zhibanfei"])
        except Exception:
            pass

        only_person = name and name.strip()
        month_cond = ""
        month_params = ()
        if month is not None:
            month_cond = " AND (MONTH(jiaban.timedate) = %s OR SUBSTRING(jiaban.timedate, 1, 7) = %s)"
            month_params = (month, f"{year}-{month:02d}")

        if only_person:
            join_cond = "INNER JOIN yggl ON jiaban.xm = yggl.name AND jiaban.xm = %s AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND (COALESCE(yggl.zaizhi,0)=0)"
            join_param = (name.strip(),)
        else:
            all_staff = not (lsys and lsys.strip())
            if all_staff:
                join_cond = "INNER JOIN yggl ON jiaban.xm = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) != %s AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)"
                join_param = (LEADER_EXCLUDE_LSYS,)
            else:
                join_cond = "INNER JOIN yggl ON jiaban.xm = yggl.name AND yggl.lsys = %s AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND (COALESCE(yggl.zaizhi,0)=0)"
                join_param = (lsys,)

        # 拉取原始加班记录（逐条），后续在 Python 中按人+日期聚合并应用激励规则
        query = f"""
            SELECT jiaban.xm AS emp_name,
                   jiaban.timedate,
                   CAST(COALESCE(jiaban.jbf, 0) AS DECIMAL(10,2)) AS hours
            FROM jiaban {join_cond}
            WHERE jiaban.jiabanzt = 4
              AND (jiaban.hx IS NULL OR TRIM(jiaban.hx) != '是')
              AND (jiaban.timedate LIKE %s OR YEAR(jiaban.timedate) = %s){month_cond}
        """
        rows = db.execute_query(query, join_param + (f"{year}%", year) + month_params)

        holiday_map = _load_holiday_festival_map(year)
        per_month, _ = _aggregate_overtime_with_incentive(rows, holiday_map, zhibanfei)

        list_data = []
        # 若指定 month，仅返回该月；否则返回所有已出现的月份
        for month_key, agg in sorted(per_month.items()):
            if month is not None and month_key != f"{year}-{month:02d}":
                continue
            hours = round(agg["hours"], 2)
            pay = round(agg["pay"], 2)
            if month_key and len(month_key) == 7:
                month_label = f"{int(month_key.split('-')[1])}月"
            else:
                month_label = month_key or "-"
            list_data.append({"month": month_key, "monthLabel": month_label, "hours": hours, "pay": pay})

        return {"success": True, "zhibanfei": zhibanfei, "list": list_data}
    except Exception as e:
        logger.error(f"其他绩效激励按月考勤失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dept/overtime-pay-by-employee")
async def get_dept_overtime_pay_by_employee(
    lsys: Optional[str] = Query(None, description="隶属于室，不传或空返回空列表（传 name 时可为空）"),
    year: Optional[int] = None,
    month: Optional[int] = Query(None, ge=1, le=12, description="筛选月份，不传为全年"),
    name: Optional[str] = Query(None, description="仅查某人（如普通员工查本人）"),
    current_user: Optional[str] = Query(None, description="当前登录用户，与 scope 配合做权限过滤"),
    scope: Optional[str] = Query(None, description="可见范围：self=本人, lsys=本室, all=全部门"),
    scope_lsys: Optional[str] = Query(None, description="scope=lsys 时本室名称"),
):
    """
    科室员工其他绩效激励明细：指定科室、年份，按人汇总（审核通过且换休票为否）。
    激励规则与 /dept/overtime-pay-by-month 相同。
    支持 name=某人 仅查本人；month=1~12 仅查该月。
    当传入 current_user+scope 时按权限强制过滤。
    返回: { success, zhibanfei, list: [{ name, hours, pay }] }
    """
    try:
        lsys, name = _apply_overtime_pay_scope(scope, current_user, scope_lsys, lsys, name)
        if year is None:
            year = datetime.now().year
        zhibanfei = 15.0
        try:
            wc = db.execute_query("SELECT zhibanfei FROM webconfig WHERE id = 1 LIMIT 1")
            if wc and wc[0].get("zhibanfei") is not None:
                zhibanfei = float(wc[0]["zhibanfei"])
        except Exception:
            pass

        only_person = name and name.strip()
        month_cond = ""
        month_params = ()
        if month is not None:
            month_cond = " AND (MONTH(jiaban.timedate) = %s OR SUBSTRING(jiaban.timedate, 1, 7) = %s)"
            month_params = (month, f"{year}-{month:02d}")

        if only_person:
            join_cond = "INNER JOIN yggl ON jiaban.xm = yggl.name AND jiaban.xm = %s AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND (COALESCE(yggl.zaizhi,0)=0)"
            params = (name.strip(), f"{year}%", year) + month_params
        else:
            if not lsys or not lsys.strip():
                return {"success": True, "zhibanfei": zhibanfei, "list": []}
            join_cond = "INNER JOIN yggl ON jiaban.xm = yggl.name AND yggl.lsys = %s AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND (COALESCE(yggl.zaizhi,0)=0)"
            params = (lsys.strip(), f"{year}%", year) + month_params

        query = f"""
            SELECT jiaban.xm AS emp_name,
                   jiaban.timedate,
                   CAST(COALESCE(jiaban.jbf, 0) AS DECIMAL(10,2)) AS hours
            FROM jiaban {join_cond}
            WHERE jiaban.jiabanzt = 4
              AND (jiaban.hx IS NULL OR TRIM(jiaban.hx) != '是')
              AND (jiaban.timedate LIKE %s OR YEAR(jiaban.timedate) = %s){month_cond}
        """
        rows = db.execute_query(query, params)

        holiday_map = _load_holiday_festival_map(year)
        _, per_employee = _aggregate_overtime_with_incentive(rows, holiday_map, zhibanfei)

        list_data = []
        for emp_name, agg in per_employee.items():
            total_hours = round(agg["hours"], 2)
            pay = round(agg["pay"], 2)
            list_data.append({"name": emp_name, "hours": total_hours, "pay": pay})

        # 按加班小时降序、姓名排序
        list_data.sort(key=lambda x: (-x["hours"], x["name"]))

        return {"success": True, "zhibanfei": zhibanfei, "list": list_data}
    except Exception as e:
        logger.error(f"其他绩效激励按员工统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dept/overtime-pay-export")
async def get_overtime_pay_export(
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份（必选，用于按月工资报表）"),
    current_user: Optional[str] = Query(None, description="当前登录用户，与 scope 配合做权限过滤"),
    scope: Optional[str] = Query(None, description="可见范围：self=本人, lsys=本室, all=全部门"),
    scope_lsys: Optional[str] = Query(None, description="scope=lsys 时本室名称"),
):
    """
    按月导出其他绩效激励工资报表数据：全员 + 各科室。
    以 yggl 名单为准，当月无加班记录者本月其他绩效激励为 0，保证科室人全。
    当传入 current_user+scope 时按权限过滤：self 仅导出本人，lsys 仅本室，all 不限制。
    返回: { success, zhibanfei, all: [{ name, pay }], byDept: [{ lsys, list: [{ name, pay }] }] }
    """
    try:
        zhibanfei = 15.0
        try:
            wc = db.execute_query("SELECT zhibanfei FROM webconfig WHERE id = 1 LIMIT 1")
            if wc and wc[0].get("zhibanfei") is not None:
                zhibanfei = float(wc[0]["zhibanfei"])
        except Exception:
            pass

        # 本月所有加班记录（不区分科室），用于计算激励与普通其他绩效激励
        q_rows = """
            SELECT jiaban.xm AS emp_name,
                   jiaban.timedate,
                   CAST(COALESCE(jiaban.jbf, 0) AS DECIMAL(10,2)) AS hours
            FROM jiaban
            INNER JOIN yggl ON jiaban.xm = yggl.name
            WHERE jiaban.jiabanzt = 4
              AND (jiaban.hx IS NULL OR TRIM(jiaban.hx) != '是')
              AND (YEAR(jiaban.timedate) = %s AND (MONTH(jiaban.timedate) = %s OR SUBSTRING(jiaban.timedate, 1, 7) = %s))
              AND RIGHT(TRIM(yggl.name), 1) != '1'
              AND RIGHT(TRIM(yggl.lsys), 1) != '1'
              AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员')
              AND (COALESCE(yggl.zaizhi,0)=0)
        """
        month_key = f"{year}-{month:02d}"
        rows = db.execute_query(q_rows, (year, month, month_key))

        holiday_map = _load_holiday_festival_map(year)
        _, per_employee = _aggregate_overtime_with_incentive(rows, holiday_map, zhibanfei)

        # 先准备全员名单（排除部办），再按 per_employee 中的 pay 填值，保证人全
        yggl_rows = db.execute_query(
            "SELECT name, lsys FROM yggl WHERE lsys IS NOT NULL AND lsys != '' AND RIGHT(TRIM(lsys), 1) != '1' "
            "AND TRIM(lsys) != %s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND RIGHT(TRIM(name), 1) != '1' AND (COALESCE(zaizhi,0)=0)",
            (LEADER_EXCLUDE_LSYS,),
        )

        list_all = []
        for r in (yggl_rows or []):
            emp_name = (r.get("name") or "").strip()
            if not emp_name:
                continue
            agg = per_employee.get(emp_name, {"pay": 0.0, "hours": 0.0})
            pay = round(agg["pay"], 2)
            list_all.append({"name": emp_name, "pay": pay})

        # 科室列表（与 lsys-list 一致，排除部办）
        lsys_list = sorted({(r.get("lsys") or "").strip() for r in (yggl_rows or []) if r.get("lsys")})

        # 各科室：从全员名单中按 lsys 划分，同样用 per_employee 中的 pay
        by_dept = []
        for lsys in lsys_list:
            dept_list = []
            for r in (yggl_rows or []):
                emp_name = (r.get("name") or "").strip()
                emp_lsys = (r.get("lsys") or "").strip()
                if not emp_name or emp_lsys != lsys:
                    continue
                agg = per_employee.get(emp_name, {"pay": 0.0, "hours": 0.0})
                pay = round(agg["pay"], 2)
                dept_list.append({"name": emp_name, "pay": pay})
            by_dept.append({"lsys": lsys, "list": dept_list})

        # 按权限 scope 过滤导出结果
        if current_user and scope == "self":
            list_all = [x for x in list_all if (x.get("name") or "").strip() == (current_user or "").strip()]
            by_dept = []
        elif scope == "lsys" and scope_lsys:
            lsys_val = (scope_lsys or "").strip()
            by_dept = [x for x in by_dept if (x.get("lsys") or "").strip() == lsys_val]
            dept_names = {n.get("name") for d in by_dept for n in (d.get("list") or [])}
            list_all = [x for x in list_all if (x.get("name") or "") in dept_names]

        return {"success": True, "zhibanfei": zhibanfei, "all": list_all, "byDept": by_dept}
    except Exception as e:
        logger.error(f"其他绩效激励按月导出失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 公出科室统计 ====================

@router.get("/dept/business-trip")
async def get_dept_business_trip_stats(
    lsys: Optional[str] = Query(None, description="隶属于室，不传或空为全员"),
    year: Optional[int] = None,
    month: Optional[int] = None,
    quarter: Optional[str] = None
):
    """
    科室公出统计（按人汇总人天）。不传 lsys 时为全员（排除部办）。
    与领导人看板「全体员工排序-公出」同一逻辑：仅已批准(bldzt=2, szrzt=2)，按区间并集计天数，不重复累加。
    """
    try:
        import calendar
        if year is None:
            year = __import__("datetime").datetime.now().year
        all_staff = not (lsys and lsys.strip())

        # 与 rankings 公出一致：拉取原始记录，仅已批准，再按区间并集算天数
        if all_staff:
            join_cond = """
                gcsqb INNER JOIN yggl ON gcsqb.gcr = yggl.name
                AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) != %s AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)
            """
            join_param: tuple = (LEADER_EXCLUDE_LSYS,)
        else:
            join_cond = """
                gcsqb INNER JOIN yggl ON gcsqb.gcr = yggl.name
                AND yggl.lsys = %s AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND (COALESCE(yggl.zaizhi,0)=0)
            """
            join_param = (lsys,)

        month_start = date(year, month, 1) if month else None
        month_end = date(year, month, calendar.monthrange(year, month)[1]) if month else None
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        q_start, q_end = None, None
        if quarter:
            if quarter == "1":
                q_start, q_end = date(year, 1, 1), date(year, 3, 31)
            elif quarter == "2":
                q_start, q_end = date(year, 4, 1), date(year, 6, 30)
            elif quarter == "3":
                q_start, q_end = date(year, 7, 1), date(year, 9, 30)
            else:
                q_start, q_end = date(year, 10, 1), date(year, 12, 31)

        if month:
            trip_raw_query = f"""
                SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.yjcfsj
                FROM {join_cond}
                WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                  AND COALESCE(gcsqb.gcsj, gcsqb.yjcfsj) <= %s AND COALESCE(gcsqb.sjfhtime, gcsqb.yjfhsj) >= %s
            """
            trip_rows = db.execute_query(trip_raw_query, join_param + (month_end.strftime("%Y-%m-%d"), month_start.strftime("%Y-%m-%d")))
        elif quarter and q_start and q_end:
            month_str_s = q_start.strftime("%Y-%m-%d")
            month_str_e = q_end.strftime("%Y-%m-%d")
            trip_raw_query = f"""
                SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.yjcfsj
                FROM {join_cond}
                WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                  AND COALESCE(gcsqb.gcsj, gcsqb.yjcfsj) <= %s AND COALESCE(gcsqb.sjfhtime, gcsqb.yjfhsj) >= %s
            """
            trip_rows = db.execute_query(trip_raw_query, join_param + (month_str_e, month_str_s))
        else:
            month_str = f"{year}%"
            trip_raw_query = f"""
                SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.yjcfsj
                FROM {join_cond}
                WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                  AND YEAR(COALESCE(gcsqb.gcsj, gcsqb.yjcfsj)) = %s
            """
            trip_rows = db.execute_query(trip_raw_query, join_param + (year,))

        by_person: dict = defaultdict(list)
        for row in trip_rows:
            gcr = (row.get("gcr") or "").strip()
            start_d = _parse_date(row.get("gcsj") or row.get("yjcfsj"))
            end_d = _parse_date(row.get("sjfhtime") or row.get("yjfhsj"))
            if start_d and end_d and end_d >= start_d:
                by_person[gcr].append((start_d, end_d))

        list_data = []
        today = date.today()
        effective_year_end = min(year_end, today)
        for gcr, intervals in by_person.items():
            if not intervals:
                continue
            if month and month_start and month_end:
                effective_month_end = min(month_end, today)
                clipped = [(max(s, month_start), min(e, effective_month_end)) for s, e in intervals if s <= effective_month_end and e >= month_start]
            elif quarter and q_start and q_end:
                effective_q_end = min(q_end, today)
                clipped = [(max(s, q_start), min(e, effective_q_end)) for s, e in intervals if s <= effective_q_end and e >= q_start]
            else:
                clipped = [(max(s, year_start), min(e, effective_year_end)) for s, e in intervals if s <= effective_year_end and e >= year_start]
            days = _merge_intervals_days(clipped)
            if days > 0:
                list_data.append({"name": gcr, "days": round(days, 2)})
        list_data.sort(key=lambda x: -x["days"])
        total_days = sum(d["days"] for d in list_data)

        return {
            "success": True,
            "totalDays": round(total_days, 2),
            "personCount": len(list_data),
            "list": list_data
        }
    except Exception as e:
        logger.error(f"公出科室统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 满勤判定辅助 ====================

def _to_comparable_dt(val) -> Optional[str]:
    """将 datetime / date / str 转为 19 位 'YYYY-MM-DD HH:MM:SS' 用于闭区间比较。"""
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
    if len(s) == 16 and s[10] == " " and ":" in s[11:]:
        return s + ":00"
    return s


def _interval_covered_by(s_start: str, s_end: str, rows: list, get_start_end) -> bool:
    """建议区间 [s_start, s_end] 是否被 rows 中某条记录的区间包含。"""
    for r in rows:
        r_start, r_end = get_start_end(r)
        r_start = _to_comparable_dt(r_start)
        r_end = _to_comparable_dt(r_end)
        if r_start and r_end and r_start <= s_start and s_end <= r_end:
            return True
    return False


def _compute_full_attendance_info(names: List[str], year: int, month: Optional[int] = None) -> Tuple[set, Dict[str, int]]:
    """
    计算不满勤的人员姓名集合，以及满勤人员各自的公出天数。

    返回 (abnormal_set, gc_days_by_name):
      - abnormal_set: 不满勤人员姓名集合
      - gc_days_by_name: {姓名: 公出天数}，仅包含满勤且有公出的人员
    """
    empty = (set(), {})
    if not names:
        return empty

    if month:
        sugg_rows = db.execute_query(
            """SELECT employee_name, start_time, end_time
               FROM attendance_suggestions
               WHERE status = 1 AND year = %s AND month = %s""",
            (year, month)
        )
    else:
        sugg_rows = db.execute_query(
            """SELECT employee_name, start_time, end_time
               FROM attendance_suggestions
               WHERE status = 1 AND year = %s""",
            (year,)
        )

    if not sugg_rows:
        return empty

    per_person: Dict[str, list] = defaultdict(list)
    for r in sugg_rows:
        n = (r.get("employee_name") or "").strip()
        if n:
            per_person[n].append(r)

    name_set = set(names)
    relevant = {n: items for n, items in per_person.items() if n in name_set}
    if not relevant:
        return empty

    if month:
        month_start = f"{year}-{month:02d}-01"
        month_end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
    else:
        month_start = f"{year}-01-01"
        month_end = f"{year + 1}-01-01"

    rel_names = list(relevant.keys())
    ph = ",".join(["%s"] * len(rel_names))

    try:
        qj_rows = db.execute_query(
            f"SELECT xm, timefrom, timeto FROM qj "
            f"WHERE xm IN ({ph}) AND qjzt = 4 AND timefrom < %s AND timeto >= %s",
            tuple(rel_names) + (month_end, month_start),
        )
    except Exception:
        qj_rows = []

    try:
        gc_rows = db.execute_query(
            f"SELECT gcr AS xm, yjcfsj, yjfhsj, gcsj, sjfhtime FROM gcsqb "
            f"WHERE gcr IN ({ph}) AND bldzt = 2 AND szrzt = 2 "
            f"AND (yjcfsj IS NOT NULL OR yjfhsj IS NOT NULL) "
            f"AND COALESCE(yjcfsj, gcsj) < %s AND COALESCE(yjfhsj, sjfhtime, yjcfsj, gcsj) >= %s",
            tuple(rel_names) + (month_end, month_start),
        )
    except Exception:
        gc_rows = []

    qj_by_name: Dict[str, list] = defaultdict(list)
    for r in qj_rows:
        n = (r.get("xm") or "").strip()
        if n:
            qj_by_name[n].append(r)

    gc_by_name: Dict[str, list] = defaultdict(list)
    for r in gc_rows:
        n = (r.get("xm") or "").strip()
        if n:
            gc_by_name[n].append(r)

    abnormal = set()
    gc_dates_by_name: Dict[str, set] = defaultdict(set)
    for n, items in relevant.items():
        is_abnormal = False
        for s in items:
            s_start = _to_comparable_dt(s.get("start_time"))
            s_end = _to_comparable_dt(s.get("end_time"))
            if not s_start or not s_end:
                is_abnormal = True
                break
            covered_by_gc = _interval_covered_by(
                s_start, s_end, gc_by_name.get(n, []),
                lambda r: (r.get("yjcfsj") or r.get("gcsj"), r.get("yjfhsj") or r.get("sjfhtime")),
            )
            if covered_by_gc:
                gc_dates_by_name[n].add(s_start[:10])
                continue
            is_abnormal = True
            break
        if is_abnormal:
            abnormal.add(n)

    gc_days_by_name = {n: len(dates) for n, dates in gc_dates_by_name.items() if n not in abnormal}
    return abnormal, gc_days_by_name


def _compute_abnormal_set(names: List[str], year: int, month: Optional[int] = None) -> set:
    """计算不满勤的人员姓名集合（简便包装）。"""
    abnormal, _ = _compute_full_attendance_info(names, year, month)
    return abnormal


# ==================== 个人满勤查询 ====================

@router.get("/person/full-attendance")
async def get_person_full_attendance(
    name: str = Query(..., description="员工姓名"),
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
):
    """
    查询指定员工某月是否满勤。
    满勤 = 当月 status=1 的考勤异常全部由已通过公出覆盖（或无异常）。
    返回: { success, isFull: bool }
    """
    try:
        name = (name or "").strip()
        if not name:
            return {"success": False, "isFull": False}
        abnormal = _compute_abnormal_set([name], year, month)
        return {"success": True, "isFull": name not in abnormal}
    except Exception as e:
        logger.error(f"个人满勤查询失败: {str(e)}")
        return {"success": False, "isFull": False}


# ==================== 领导人看板扩展 API ====================

@router.get("/leader/full-attendance")
async def get_leader_full_attendance(
    year: int = Query(..., description="年份"),
    month: int = Query(..., description="月份"),
    lsys: Optional[str] = Query(None, description="隶属科室，不传则全员")
):
    """
    满勤率：指定月份全员或指定科室的满勤率。
    满勤 = 当月 status=1 的考勤异常全部由已通过公出覆盖（或无异常）；有请假覆盖或未处理则不满勤。
    返回: workdays(当月应出勤工作日，仅作参考), totalPeople, fullCount, rate, fullNames(满勤人员姓名),
    byDept(仅当未传lsys时，各科室明细)
    """
    try:
        workdays = _count_workdays_in_month(year, month)
        month_str = f"{year}-{month:02d}"

        if lsys:
            rows = db.execute_query(
                "SELECT name FROM yggl WHERE lsys = %s AND name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(zaizhi,0)=0)",
                (lsys, LEADER_EXCLUDE_LSYS)
            )
            names = [r["name"].strip() for r in rows if r.get("name")]
        else:
            rows = db.execute_query(
                "SELECT name, lsys FROM yggl WHERE name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(zaizhi,0)=0)",
                (LEADER_EXCLUDE_LSYS,)
            )
            names = [r["name"].strip() for r in rows if r.get("name")]

        if not names:
            return {
                "success": True,
                "workdays": workdays,
                "totalPeople": 0,
                "fullCount": 0,
                "rate": 0,
                "fullNames": [],
                "byDept": []
            }

        abnormal_set = _compute_abnormal_set(names, year, month)
        full_count = sum(1 for n in names if n not in abnormal_set)
        total = len(names)
        rate = round(full_count / total, 4) if total else 0
        full_names_all = sorted(n for n in names if n not in abnormal_set)

        result = {
            "success": True,
            "workdays": workdays,
            "totalPeople": total,
            "fullCount": full_count,
            "rate": rate,
            "fullNames": full_names_all,
            "byDept": []
        }

        if lsys is None and rows and len(rows) > 0 and "lsys" in (rows[0] or {}):
            dept_names = {}
            for r in rows:
                n = (r.get("name") or "").strip()
                d = (r.get("lsys") or "").strip()
                if not n or d == LEADER_EXCLUDE_LSYS:
                    continue
                dept_names.setdefault(d, []).append(n)
            by_dept = []
            for d, nlist in dept_names.items():
                fc = sum(1 for n in nlist if n not in abnormal_set)
                tot = len(nlist)
                full_list = sorted(n for n in nlist if n not in abnormal_set)
                by_dept.append({
                    "lsys": d,
                    "totalPeople": tot,
                    "fullCount": fc,
                    "rate": round(fc / tot, 4) if tot else 0,
                    "fullNames": full_list,
                })
            result["byDept"] = by_dept

        return result
    except Exception as e:
        logger.error(f"满勤率查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leader/full-attendance-export")
async def get_leader_full_attendance_export(
    year: int = Query(..., description="年份"),
    month: Optional[int] = Query(None, description="月份，不传则全年"),
    lsys: Optional[str] = Query(None, description="隶属科室，不传则全员")
):
    """
    满勤名单导出：与领导人看板满勤统计同一逻辑（异常全部由公出覆盖仍算满勤，有请假或未处理则不满勤）。
    返回 byDept 中每项含 fullNames（满勤人员姓名列表），用于 Excel 等导出。
    """
    try:
        if month:
            workdays = _count_workdays_in_month(year, month)
        else:
            workdays = sum(_count_workdays_in_month(year, m) for m in range(1, 13))

        if lsys:
            rows = db.execute_query(
                "SELECT name FROM yggl WHERE lsys = %s AND name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(zaizhi,0)=0)",
                (lsys, LEADER_EXCLUDE_LSYS)
            )
            names = [r["name"].strip() for r in rows if r.get("name")]
        else:
            rows = db.execute_query(
                "SELECT name, lsys FROM yggl WHERE name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(zaizhi,0)=0)",
                (LEADER_EXCLUDE_LSYS,)
            )
            names = [r["name"].strip() for r in rows if r.get("name")]

        if not names:
            return {"success": True, "workdays": workdays, "totalPeople": 0, "fullCount": 0, "rate": 0, "byDept": []}

        abnormal_set, gc_days_map = _compute_full_attendance_info(names, year, month)
        full_count = sum(1 for n in names if n not in abnormal_set)
        total = len(names)
        rate = round(full_count / total, 4) if total else 0

        def _build_details(name_list):
            details = []
            for n in sorted(name_list):
                gc = gc_days_map.get(n, 0)
                details.append({"name": n, "attendDays": workdays - gc, "businessDays": gc})
            return details

        by_dept = []
        if lsys:
            full_list = [n for n in names if n not in abnormal_set]
            by_dept.append({
                "lsys": lsys.strip(),
                "totalPeople": total,
                "fullCount": full_count,
                "rate": rate,
                "fullNames": sorted(full_list),
                "fullDetails": _build_details(full_list),
            })
        elif rows and len(rows) > 0 and "lsys" in (rows[0] or {}):
            dept_names = {}
            for r in rows:
                n = (r.get("name") or "").strip()
                d = (r.get("lsys") or "").strip()
                if not n or d == LEADER_EXCLUDE_LSYS:
                    continue
                dept_names.setdefault(d, []).append(n)
            for d, nlist in sorted(dept_names.items()):
                fc = sum(1 for n in nlist if n not in abnormal_set)
                tot = len(nlist)
                full_list = [n for n in nlist if n not in abnormal_set]
                by_dept.append({
                    "lsys": d,
                    "totalPeople": tot,
                    "fullCount": fc,
                    "rate": round(fc / tot, 4) if tot else 0,
                    "fullNames": sorted(full_list),
                    "fullDetails": _build_details(full_list),
                })

        return {
            "success": True,
            "workdays": workdays,
            "totalPeople": total,
            "fullCount": full_count,
            "rate": rate,
            "byDept": by_dept
        }
    except Exception as e:
        logger.error(f"满勤名单导出失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leader/full-attendance-year")
async def get_leader_full_attendance_year(
    year: int = Query(..., description="年份"),
    lsys: Optional[str] = Query(None, description="隶属科室，不传则全员")
):
    """
    满勤率（全年）：指定年份全员或指定科室的全年满勤率。
    全年满勤 = 该年度内 status=1 异常全部由已通过公出覆盖（或无异常）。
    返回: totalPeople, fullCount, rate, fullNames(满勤人员姓名), byDept(仅当未传lsys时)，无 workdays。
    """
    try:
        year_prefix = f"{year}-"
        if lsys:
            rows = db.execute_query(
                "SELECT name FROM yggl WHERE lsys = %s AND name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(zaizhi,0)=0)",
                (lsys, LEADER_EXCLUDE_LSYS)
            )
            names = [r["name"].strip() for r in rows if r.get("name")]
        else:
            rows = db.execute_query(
                "SELECT name, lsys FROM yggl WHERE name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(zaizhi,0)=0)",
                (LEADER_EXCLUDE_LSYS,)
            )
            names = [r["name"].strip() for r in rows if r.get("name")]

        if not names:
            return {
                "success": True,
                "totalPeople": 0,
                "fullCount": 0,
                "rate": 0,
                "fullNames": [],
                "byDept": []
            }

        abnormal_set = _compute_abnormal_set(names, year)
        full_count = sum(1 for n in names if n not in abnormal_set)
        total = len(names)
        rate = round(full_count / total, 4) if total else 0
        full_names_all = sorted(n for n in names if n not in abnormal_set)

        result = {
            "success": True,
            "totalPeople": total,
            "fullCount": full_count,
            "rate": rate,
            "fullNames": full_names_all,
            "byDept": []
        }

        if lsys is None and rows and len(rows) > 0 and "lsys" in (rows[0] or {}):
            dept_names = {}
            for r in rows:
                n = (r.get("name") or "").strip()
                d = (r.get("lsys") or "").strip()
                if not n or d == LEADER_EXCLUDE_LSYS:
                    continue
                dept_names.setdefault(d, []).append(n)
            by_dept = []
            for d, nlist in dept_names.items():
                fc = sum(1 for n in nlist if n not in abnormal_set)
                tot = len(nlist)
                full_list = sorted(n for n in nlist if n not in abnormal_set)
                by_dept.append({
                    "lsys": d,
                    "totalPeople": tot,
                    "fullCount": fc,
                    "rate": round(fc / tot, 4) if tot else 0,
                    "fullNames": full_list,
                })
            result["byDept"] = by_dept

        return result
    except Exception as e:
        logger.error(f"全年满勤率查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leader/full-attendance-by-month")
async def get_leader_full_attendance_by_month(
    year: int = Query(..., description="年份"),
    lsys: Optional[str] = Query(None, description="隶属科室，不传则全员")
):
    """
    按月考勤满勤人数：横轴月份，纵轴满勤人数，可筛选科室。
    满勤 = 当月异常全部由公出覆盖或无异常。返回 12 个月每月的 fullCount、totalPeople。
    返回: list[{ month, monthLabel, fullCount, totalPeople }]
    """
    try:
        list_data = []
        for month in range(1, 13):
            month_str = f"{year}-{month:02d}"
            if lsys:
                rows = db.execute_query(
                    "SELECT name FROM yggl WHERE lsys = %s AND name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(zaizhi,0)=0)",
                    (lsys, LEADER_EXCLUDE_LSYS)
                )
                names = [r["name"].strip() for r in rows if r.get("name")]
            else:
                rows = db.execute_query(
                    "SELECT name FROM yggl WHERE name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(zaizhi,0)=0)",
                    (LEADER_EXCLUDE_LSYS,)
                )
                names = [r["name"].strip() for r in rows if r.get("name")]

            if not names:
                list_data.append({
                    "month": month,
                    "monthLabel": f"{month}月",
                    "fullCount": 0,
                    "totalPeople": 0
                })
                continue

            abnormal_set = _compute_abnormal_set(names, year, month)
            full_count = sum(1 for n in names if n not in abnormal_set)
            total = len(names)
            list_data.append({
                "month": month,
                "monthLabel": f"{month}月",
                "fullCount": full_count,
                "totalPeople": total
            })
        return {"success": True, "list": list_data}
    except Exception as e:
        logger.error(f"按月满勤人数查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leader/dept-comparison")
async def get_leader_dept_comparison(
    year: int = Query(..., description="年份"),
    month: Optional[int] = Query(None, description="月份，不传则全年")
):
    """
    科室横向对比：各科室加班、请假、公出总数及人均。
    返回: list[{ lsys, personCount, overtimeTotal, leaveTotal, tripTotal, overtimePerCapita, leavePerCapita, tripPerCapita }]
    """
    try:
        import calendar

        month_str = f"{year}-{month:02d}%" if month else f"{year}%"
        month_cond_overtime = "AND (timedate LIKE %s OR SUBSTRING(timedate, 1, 7) = %s)" if month else "AND (timedate LIKE %s OR YEAR(timedate) = %s)"
        params_overtime = (month_str, month_str) if month else (month_str, year)

        if month:
            leave_period_start = date(year, month, 1)
            leave_period_end = date(year, month, calendar.monthrange(year, month)[1])
        else:
            leave_period_start = date(year, 1, 1)
            leave_period_end = date(year, 12, 31)
        leave_pe_str = leave_period_end.strftime("%Y-%m-%d")
        leave_ps_str = leave_period_start.strftime("%Y-%m-%d")
        leave_ov = _leave_overlap_sql_bounds()

        person_rows = db.execute_query(
            "SELECT lsys, COUNT(*) AS cnt FROM yggl WHERE lsys IS NOT NULL AND lsys != '' AND RIGHT(TRIM(lsys), 1) != '1' AND RIGHT(TRIM(name), 1) != '1' AND TRIM(lsys) != %s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(zaizhi,0)=0) GROUP BY lsys ORDER BY lsys",
            (LEADER_EXCLUDE_LSYS,)
        )
        person_by_lsys = {r["lsys"].strip(): int(r.get("cnt") or 0) for r in person_rows if r.get("lsys")}

        leave_raw = f"""
            SELECT lsys, timefrom, timeto, timefromdate, CAST(tian AS DECIMAL(10,2)) AS tian
            FROM qj WHERE qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员')
            {leave_ov}
        """
        leave_rows = db.execute_query(leave_raw, (LEADER_EXCLUDE_LSYS, leave_pe_str, leave_ps_str))
        leave_by_lsys_acc: Dict[str, float] = defaultdict(float)
        for row in leave_rows or []:
            l = (row.get("lsys") or "").strip()
            if not l:
                continue
            ls_d, le_d = _qj_leave_date_bounds(row)
            if not ls_d or not le_d:
                continue
            try:
                tian_f = float(row.get("tian") or 0)
            except (TypeError, ValueError):
                tian_f = 0.0
            alloc = _allocate_leave_tian_to_period(tian_f, ls_d, le_d, leave_period_start, leave_period_end)
            if alloc > 0:
                leave_by_lsys_acc[l] += alloc
        leave_by_lsys = {k: round(v, 2) for k, v in leave_by_lsys_acc.items()}

        overtime_query = f"""
            SELECT yggl.lsys, SUM(CAST(COALESCE(jiaban.tian1, 0) AS DECIMAL(10,2))) AS total
            FROM jiaban INNER JOIN yggl ON jiaban.xm = yggl.name AND yggl.lsys IS NOT NULL AND yggl.lsys != '' AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)
            WHERE jiaban.jiabanzt = 4 {month_cond_overtime}
            GROUP BY yggl.lsys
        """
        ot_rows = db.execute_query(overtime_query, params_overtime)
        overtime_by_lsys = {r["lsys"].strip(): round(float(r.get("total") or 0), 2) for r in ot_rows if r.get("lsys")}

        # 公出与「全体员工排序」一致：仅已批准(bldzt=2, szrzt=2)，按区间并集计天数后按科室汇总
        month_start = date(year, month, 1) if month else None
        month_end = date(year, month, calendar.monthrange(year, month)[1]) if month else None
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        if month:
            trip_raw_query = """
                SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.yjcfsj, yggl.lsys
                FROM gcsqb INNER JOIN yggl ON gcsqb.gcr = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) != %s AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)
                WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                  AND COALESCE(gcsqb.gcsj, gcsqb.yjcfsj) <= %s AND COALESCE(gcsqb.sjfhtime, gcsqb.yjfhsj) >= %s
            """
            trip_rows = db.execute_query(trip_raw_query, (LEADER_EXCLUDE_LSYS, month_end.strftime("%Y-%m-%d"), month_start.strftime("%Y-%m-%d")))
        else:
            trip_raw_query = """
                SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.yjcfsj, yggl.lsys
                FROM gcsqb INNER JOIN yggl ON gcsqb.gcr = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) != %s AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)
                WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                  AND YEAR(COALESCE(gcsqb.gcsj, gcsqb.yjcfsj)) = %s
            """
            trip_rows = db.execute_query(trip_raw_query, (LEADER_EXCLUDE_LSYS, year))
        by_person_trip: dict = defaultdict(list)
        for row in trip_rows:
            gcr = (row.get("gcr") or "").strip()
            lsys = (row.get("lsys") or "").strip()
            if not lsys:
                continue
            start_d = _parse_date(row.get("gcsj") or row.get("yjcfsj"))
            end_d = _parse_date(row.get("sjfhtime") or row.get("yjfhsj"))
            if start_d and end_d and end_d >= start_d:
                by_person_trip[(gcr, lsys)].append((start_d, end_d))
        trip_by_lsys = defaultdict(float)
        today = date.today()
        effective_year_end = min(year_end, today)
        for (gcr, lsys), intervals in by_person_trip.items():
            if not intervals:
                continue
            if month and month_start and month_end:
                effective_month_end = min(month_end, today)
                clipped = [(max(s, month_start), min(e, effective_month_end)) for s, e in intervals if s <= effective_month_end and e >= month_start]
            else:
                clipped = [(max(s, year_start), min(e, effective_year_end)) for s, e in intervals if s <= effective_year_end and e >= year_start]
            days = _merge_intervals_days(clipped)
            if days > 0:
                trip_by_lsys[lsys] += round(days, 2)
        trip_by_lsys = dict(trip_by_lsys)

        # 按科室汇总换休请假小时（与 /dept/overtime net 一致：区间重叠比例 × 小时）
        hx_raw = f"""
            SELECT yggl.lsys, qj.timefrom, qj.timeto, qj.timefromdate, CAST(qj.tian AS DECIMAL(10,2)) AS tian, qj.xiaoshi
            FROM qj INNER JOIN yggl ON qj.xm = yggl.name AND yggl.lsys IS NOT NULL AND yggl.lsys != ''
                AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)
            WHERE qj.qjzt = 4 AND TRIM(qj.qjfs) IN ('换休','员工换休票') AND RIGHT(TRIM(qj.xm), 1) != '1'
                AND TRIM(yggl.lsys) != %s
            {leave_ov}
        """
        hx_rows = db.execute_query(hx_raw, (LEADER_EXCLUDE_LSYS, leave_pe_str, leave_ps_str))
        hx_by_lsys_acc: Dict[str, float] = defaultdict(float)
        for row in hx_rows or []:
            lsys_k = (row.get("lsys") or "").strip()
            if not lsys_k or lsys_k == LEADER_EXCLUDE_LSYS:
                continue
            ls_d, le_d = _qj_leave_date_bounds(row)
            if not ls_d or not le_d:
                continue
            h_full = _qj_hx_row_total_hours(row)
            if h_full <= 0:
                continue
            frac = _leave_overlap_fraction(ls_d, le_d, leave_period_start, leave_period_end)
            if frac <= 0:
                continue
            hx_by_lsys_acc[lsys_k] += h_full * frac
        hx_by_lsys = {k: round(v, 2) for k, v in hx_by_lsys_acc.items()}

        if month:
            workdays = _count_workdays_in_month(year, month)
        else:
            workdays = sum(_count_workdays_in_month(year, m) for m in range(1, 13))

        all_lsys = sorted(person_by_lsys.keys())
        list_data = []
        for l in all_lsys:
            pc = person_by_lsys.get(l, 0)
            ot = overtime_by_lsys.get(l, 0)
            lv = leave_by_lsys.get(l, 0)
            tr = trip_by_lsys.get(l, 0)
            hx = hx_by_lsys.get(l, 0)
            net_ot = round(ot - hx, 2)
            effective_pd = workdays * pc - tr
            list_data.append({
                "lsys": l,
                "personCount": pc,
                "workdays": workdays,
                "overtimeTotal": ot,
                "netOvertimeTotal": net_ot,
                "leaveTotal": lv,
                "tripTotal": tr,
                "overtimePerCapita": round(ot / pc, 2) if pc else 0,
                "netOvertimePerCapita": round(net_ot / pc, 2) if pc else 0,
                "overtimePerWorkday": round(ot / effective_pd, 2) if effective_pd > 0 else 0,
                "netOvertimePerWorkday": round(net_ot / effective_pd, 2) if effective_pd > 0 else 0,
                "leavePerCapita": round(lv / pc, 2) if pc else 0,
                "tripPerCapita": round(tr / pc, 2) if pc else 0
            })
        return {"success": True, "list": list_data}
    except Exception as e:
        logger.error(f"科室对比查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leader/rankings")
async def get_leader_rankings(
    year: int = Query(..., description="年份"),
    month: Optional[int] = Query(None, description="月份，不传则全年"),
    type_: str = Query("overtime", alias="type", description="overtime|leave|trip")
):
    """
    全体员工排序：按加班小时/请假天数/公出天数排序。
    返回: list[{ rank, name, lsys, value, unit }]
    """
    try:
        import calendar

        month_str = f"{year}-{month:02d}%" if month else f"{year}%"
        month_param = (month_str, month_str) if month else (month_str, year)

        rows = []
        unit = ""

        if type_ == "overtime":
            query = """
                SELECT jiaban.xm AS name, yggl.lsys,
                    SUM(CAST(COALESCE(jiaban.tian1, 0) AS DECIMAL(10,2))) AS value
                FROM jiaban INNER JOIN yggl ON jiaban.xm = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)
                WHERE jiaban.jiabanzt = 4 AND RIGHT(TRIM(jiaban.xm), 1) != '1' AND (jiaban.timedate LIKE %s OR YEAR(jiaban.timedate) = %s)
                GROUP BY jiaban.xm, yggl.lsys ORDER BY value DESC
            """
            unit = "小时"
            rows = db.execute_query(query, month_param)
        elif type_ == "leave":
            if month:
                lp_start = date(year, month, 1)
                lp_end = date(year, month, calendar.monthrange(year, month)[1])
            else:
                lp_start = date(year, 1, 1)
                lp_end = date(year, 12, 31)
            pe_str = lp_end.strftime("%Y-%m-%d")
            ps_str = lp_start.strftime("%Y-%m-%d")
            lov = _leave_overlap_sql_bounds()
            leave_raw = f"""
                SELECT qj.xm AS name, qj.lsys, timefrom, timeto, timefromdate, CAST(qj.tian AS DECIMAL(10,2)) AS tian
                FROM qj WHERE qj.qjzt = 4 AND RIGHT(TRIM(qj.xm), 1) != '1' AND RIGHT(TRIM(qj.lsys), 1) != '1' AND TRIM(qj.lsys) NOT IN ('其他部门员工','其他部门成员')
                {lov}
            """
            lrows = db.execute_query(leave_raw, (pe_str, ps_str))
            acc_lv: Dict[Tuple[str, str], float] = defaultdict(float)
            for row in lrows or []:
                nm = (row.get("name") or "").strip()
                ls = (row.get("lsys") or "").strip()
                if not nm:
                    continue
                ls_d, le_d = _qj_leave_date_bounds(row)
                if not ls_d or not le_d:
                    continue
                try:
                    tian_f = float(row.get("tian") or 0)
                except (TypeError, ValueError):
                    tian_f = 0.0
                alloc = _allocate_leave_tian_to_period(tian_f, ls_d, le_d, lp_start, lp_end)
                if alloc > 0:
                    acc_lv[(nm, ls)] += alloc
            rows = [
                {"name": k[0], "lsys": k[1], "value": round(v, 2)}
                for k, v in sorted(acc_lv.items(), key=lambda x: -x[1])
                if v > 0
            ]
            unit = "天"
        elif type_ == "trip":
            # 公出天数按区间并集计算，避免重复申报导致超过 365 天
            month_start = date(year, month, 1) if month else None
            month_end = date(year, month, calendar.monthrange(year, month)[1]) if month else None
            if month:
                trip_raw_query = """
                    SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.yjcfsj, yggl.lsys
                    FROM gcsqb INNER JOIN yggl ON gcsqb.gcr = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)
                    WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                      AND COALESCE(gcsqb.gcsj, gcsqb.yjcfsj) <= %s AND COALESCE(gcsqb.sjfhtime, gcsqb.yjfhsj) >= %s
                """
                trip_rows = db.execute_query(trip_raw_query, (month_end.strftime("%Y-%m-%d"), month_start.strftime("%Y-%m-%d")))
            else:
                trip_raw_query = """
                    SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.yjcfsj, yggl.lsys
                    FROM gcsqb INNER JOIN yggl ON gcsqb.gcr = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)
                    WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                      AND YEAR(COALESCE(gcsqb.gcsj, gcsqb.yjcfsj)) = %s
                """
                trip_rows = db.execute_query(trip_raw_query, (year,))
            # 按 (gcr, lsys) 分组，每人收集 [start, end] 区间后做并集再算天数
            by_person: dict = defaultdict(list)
            for row in trip_rows:
                gcr = (row.get("gcr") or "").strip()
                lsys = (row.get("lsys") or "").strip()
                start_d = _parse_date(row.get("gcsj") or row.get("yjcfsj"))
                end_d = _parse_date(row.get("sjfhtime") or row.get("yjfhsj"))
                if start_d and end_d and end_d >= start_d:
                    by_person[(gcr, lsys)].append((start_d, end_d))
            list_trip = []
            year_start = date(year, 1, 1)
            year_end = date(year, 12, 31)
            today = date.today()
            effective_year_end = min(year_end, today)
            for (gcr, lsys), intervals in by_person.items():
                if not intervals:
                    continue
                if month and month_start and month_end:
                    effective_month_end = min(month_end, today)
                    clipped = [(max(s, month_start), min(e, effective_month_end)) for s, e in intervals if s <= effective_month_end and e >= month_start]
                    days = _merge_intervals_days(clipped)
                else:
                    clipped = [(max(s, year_start), min(e, effective_year_end)) for s, e in intervals if s <= effective_year_end and e >= year_start]
                    days = _merge_intervals_days(clipped)
                if days > 0:
                    list_trip.append({"name": gcr, "lsys": lsys, "value": round(days, 2)})
            list_trip.sort(key=lambda x: -x["value"])
            rows = list_trip
            unit = "天"
        else:
            raise HTTPException(status_code=400, detail="type 须为 overtime|leave|trip")

        list_data = []
        for i, r in enumerate(rows, 1):
            list_data.append({
                "rank": i,
                "name": (r.get("name") or "").strip(),
                "lsys": (r.get("lsys") or "").strip(),
                "value": round(float(r.get("value") or 0), 2),
                "unit": unit
            })
        return {"success": True, "list": list_data, "unit": unit}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"全员排序查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 考勤纪律审查 ====================

def _parse_time_str(val) -> Optional[str]:
    """将 DB 返回的时间字段转为 HH:MM:SS 字符串，兼容 timedelta / datetime / str。"""
    if val is None:
        return None
    if hasattr(val, "total_seconds"):
        total = int(val.total_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    s = str(val).strip()
    if not s:
        return None
    parts = s.split(":")
    if len(parts) >= 3:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
    if len(parts) == 2:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
    return None


def _time_in_range(t_str: str, lo: str, hi: str) -> bool:
    """判断 HH:MM:SS 格式的时间是否在 [lo, hi] 闭区间内（进一原则：超过整分钟的秒数归入下一分钟）。"""
    if len(lo) == 5:
        lo = lo + ":00"
    if len(hi) == 5:
        hi = hi + ":00"
    return lo <= t_str <= hi


def _get_last_time(row: dict) -> Optional[str]:
    """取一行考勤记录中最后一个有效打卡时间（time_10 → time_1 倒序查找）。"""
    for i in range(10, 0, -1):
        val = row.get(f"time_{i}")
        t = _parse_time_str(val)
        if t:
            return t
    return None


def _load_non_workday_set(start_date: str, end_date: str) -> set:
    """
    返回 start_date ~ end_date 之间所有非工作日的日期字符串集合。
    非工作日 = 周末（周六日）+ 法定假日（holiday 表 type 含'假'或'休'），
    但 holiday 表 type 含'班'的调休上班日排除在外（视为工作日）。
    """
    from utils.holiday_loader import load_holidays_dict
    import calendar as _cal

    years = set()
    try:
        years.add(int(start_date[:4]))
        years.add(int(end_date[:4]))
    except (ValueError, IndexError):
        pass

    holidays: dict = {}
    for y in years:
        holidays.update(load_holidays_dict(str(y)))

    non_work = set()
    try:
        from datetime import timedelta
        cur = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        while cur <= end:
            ds = cur.strftime("%Y-%m-%d")
            is_weekend = cur.weekday() in (5, 6)
            ht = holidays.get(ds, "")
            is_holiday_off = ("假" in ht or "休" in ht)
            is_makeup_work = ("班" in ht)
            if is_makeup_work:
                pass
            elif is_weekend or is_holiday_off:
                non_work.add(ds)
            cur += timedelta(days=1)
    except Exception as e:
        logger.warning(f"构建非工作日集合失败: {e}")
    return non_work


@router.get("/discipline/clock-in-stats")
async def get_clock_in_discipline_stats(
    year: int = Query(...),
    month: Optional[int] = Query(None),
    lsys: Optional[str] = Query(None),
    dimension: str = Query("person", description="聚合维度: person / month / dept"),
    clock_in_minutes: int = Query(2, description="踩点上班阈值：8:00 前 N 分钟，2-5"),
    clock_out_minutes: int = Query(2, description="踩点下班阈值：17:00 后 N 分钟，2-5"),
    exclude_holidays: bool = Query(False, description="是否排除节假日（周末+法定假日）"),
):
    """
    打卡纪律大数据检测。
    统计 attendance_records 中踩点上班与踩点下班的情况。
    clock_in_minutes: 8:00前N分钟为踩点上班区间，默认2（即7:58-8:00）
    clock_out_minutes: 17:00后N分钟为踩点下班区间，默认2（即17:00-17:02）
    """
    try:
        ci_min = max(2, min(5, clock_in_minutes))
        co_min = max(2, min(5, clock_out_minutes))

        ci_start_hour, ci_start_min = divmod(60 * 8 - ci_min, 60)
        ci_lo = f"{ci_start_hour:02d}:{ci_start_min:02d}"
        ci_hi = "08:00"
        co_lo = "17:00"
        co_end_hour, co_end_min = divmod(60 * 17 + co_min, 60)
        co_hi = f"{co_end_hour:02d}:{co_end_min:02d}"

        date_lo = f"{year}-01-01"
        date_hi = f"{year}-12-31"
        if month:
            date_lo = f"{year}-{month:02d}-01"
            if month == 12:
                date_hi = f"{year}-12-31"
            else:
                date_hi = f"{year}-{month + 1:02d}-01"

        sql = (
            "SELECT a.employee_name, a.department, a.attendance_date, "
            "a.time_1, a.time_2, a.time_3, a.time_4, a.time_5, "
            "a.time_6, a.time_7, a.time_8, a.time_9, a.time_10 "
            "FROM attendance_records a "
            "WHERE a.attendance_date >= %s AND a.attendance_date < %s "
        )
        params: list = [date_lo, date_hi]
        if lsys:
            sql += "AND a.department = %s "
            params.append(lsys)
        sql += "ORDER BY a.attendance_date, a.employee_name"

        rows = db.execute_query(sql, tuple(params))

        valid_names_rows = db.execute_query(
            "SELECT name, lsys FROM yggl WHERE name IS NOT NULL AND name != '' "
            "AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' "
            "AND TRIM(lsys) != %s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(zaizhi,0)=0)",
            (LEADER_EXCLUDE_LSYS,),
        )
        valid_names = {r["name"].strip() for r in valid_names_rows if r.get("name")}
        name_dept_map = {}
        for r in valid_names_rows:
            n = (r.get("name") or "").strip()
            if n:
                name_dept_map[n] = (r.get("lsys") or "").strip()

        non_workdays = _load_non_workday_set(date_lo, date_hi) if exclude_holidays else set()

        clock_in_data = []
        clock_out_data = []

        for row in rows or []:
            name = (row.get("employee_name") or "").strip()
            if not name or name not in valid_names:
                continue
            dept = name_dept_map.get(name, (row.get("department") or "").strip())
            date_str = str(row.get("attendance_date") or "")[:10]
            if date_str in non_workdays:
                continue
            month_key = date_str[:7]

            first_time = _parse_time_str(row.get("time_1"))
            last_time = _get_last_time(row)

            if first_time and _time_in_range(first_time, ci_lo, ci_hi):
                clock_in_data.append({"name": name, "dept": dept, "date": date_str, "month": month_key, "time": first_time})

            if last_time and _time_in_range(last_time, co_lo, co_hi):
                clock_out_data.append({"name": name, "dept": dept, "date": date_str, "month": month_key, "time": last_time})

        def _aggregate(data_list, dim):
            agg = defaultdict(lambda: {"count": 0, "dates": []})
            for item in data_list:
                if dim == "person":
                    key = item["name"]
                elif dim == "month":
                    key = item["month"]
                else:
                    key = item["dept"]
                agg[key]["count"] += 1
                if len(agg[key]["dates"]) < 50:
                    agg[key]["dates"].append({"date": item["date"], "name": item["name"], "time": item["time"]})
            result = []
            for k, v in agg.items():
                entry = {"key": k, "count": v["count"], "dates": v["dates"]}
                if dim == "person":
                    entry["dept"] = name_dept_map.get(k, "")
                result.append(entry)
            result.sort(key=lambda x: -x["count"])
            return result

        return {
            "success": True,
            "clockIn": _aggregate(clock_in_data, dimension),
            "clockOut": _aggregate(clock_out_data, dimension),
            "clockInTotal": len(clock_in_data),
            "clockOutTotal": len(clock_out_data),
            "clockInRange": f"{ci_lo}-{ci_hi}",
            "clockOutRange": f"{co_lo}-{co_hi}",
        }
    except Exception as e:
        logger.error(f"打卡纪律统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discipline/person-scatter")
async def get_person_scatter(
    name: str = Query(..., description="员工姓名"),
    start_date: str = Query(..., description="起始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    exclude_holidays: bool = Query(False, description="是否排除节假日"),
):
    """
    获取某员工在日期区间内的逐日上班/下班打卡时间，用于散点图展示。
    返回 { success, name, data: [{ date, clockIn, clockOut }] }
    clockIn / clockOut 为小时浮点数（如 7.97 = 7:58:12），null 表示当天无记录。
    """
    try:
        sql = (
            "SELECT attendance_date, "
            "time_1, time_2, time_3, time_4, time_5, "
            "time_6, time_7, time_8, time_9, time_10 "
            "FROM attendance_records "
            "WHERE employee_name = %s AND attendance_date >= %s AND attendance_date <= %s "
            "ORDER BY attendance_date"
        )
        rows = db.execute_query(sql, (name, start_date, end_date))
        non_workdays = _load_non_workday_set(start_date, end_date) if exclude_holidays else set()

        def _to_hours(val):
            t = _parse_time_str(val)
            if not t:
                return None
            parts = t.split(":")
            h = int(parts[0])
            m = int(parts[1])
            s = int(parts[2]) if len(parts) > 2 else 0
            return round(h + m / 60 + s / 3600, 4)

        data = []
        for row in rows or []:
            d = str(row.get("attendance_date") or "")[:10]
            if len(d) < 10:
                continue
            if d in non_workdays:
                continue
            ci = _to_hours(row.get("time_1"))
            last_raw = None
            for i in range(10, 0, -1):
                v = row.get(f"time_{i}")
                if v is not None and _parse_time_str(v):
                    last_raw = v
                    break
            co = _to_hours(last_raw)
            if ci is None and co is None:
                continue
            data.append({"date": d, "clockIn": ci, "clockOut": co})

        return {"success": True, "name": name, "data": data}
    except Exception as e:
        logger.error(f"个人散点图数据查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
#  工作强度统计  A = 加班时长 / (应出勤时长 - 公出时长)
# ============================================================

def _get_overtime_by_person(year: int, month: Optional[int], lsys: Optional[str]) -> dict:
    """按人汇总加班小时 {name: hours}，仅已通过(jiabanzt=4)"""
    all_staff = not (lsys and lsys.strip())
    if all_staff:
        join_cond = ("INNER JOIN yggl ON jiaban.xm = yggl.name "
                     "AND RIGHT(TRIM(yggl.name),1)!='1' AND RIGHT(TRIM(yggl.lsys),1)!='1' "
                     f"AND TRIM(yggl.lsys)!=%s AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)")
        join_param = (LEADER_EXCLUDE_LSYS,)
    else:
        join_cond = ("INNER JOIN yggl ON jiaban.xm = yggl.name "
                     "AND yggl.lsys=%s AND RIGHT(TRIM(yggl.name),1)!='1' "
                     "AND RIGHT(TRIM(yggl.lsys),1)!='1' AND (COALESCE(yggl.zaizhi,0)=0)")
        join_param = (lsys,)

    if month:
        ms = f"{year}-{month:02d}"
        sql = f"""
            SELECT TRIM(jiaban.xm) AS name,
                   SUM(CAST(COALESCE(jiaban.tian1,0) AS DECIMAL(10,2))) AS hours
            FROM jiaban {join_cond}
            WHERE jiaban.jiabanzt=4
              AND (jiaban.timedate LIKE %s OR SUBSTRING(jiaban.timedate,1,7)=%s)
            GROUP BY TRIM(jiaban.xm)
        """
        rows = db.execute_query(sql, join_param + (f"{ms}%", ms))
    else:
        sql = f"""
            SELECT TRIM(jiaban.xm) AS name,
                   SUM(CAST(COALESCE(jiaban.tian1,0) AS DECIMAL(10,2))) AS hours
            FROM jiaban {join_cond}
            WHERE jiaban.jiabanzt=4
              AND (jiaban.timedate LIKE %s OR YEAR(jiaban.timedate)=%s)
            GROUP BY TRIM(jiaban.xm)
        """
        rows = db.execute_query(sql, join_param + (f"{year}%", year))

    result = {}
    for r in (rows or []):
        n = (r.get("name") or "").strip()
        if n:
            result[n] = float(r.get("hours") or 0)
    return result


def _get_trip_days_by_person(year: int, month: Optional[int], lsys: Optional[str]) -> dict:
    """按人汇总公出天数 {name: days}，区间并集去重，仅已批准"""
    import calendar as _cal
    all_staff = not (lsys and lsys.strip())
    if all_staff:
        jc = ("gcsqb INNER JOIN yggl ON gcsqb.gcr=yggl.name "
              "AND RIGHT(TRIM(yggl.name),1)!='1' AND RIGHT(TRIM(yggl.lsys),1)!='1' "
              "AND TRIM(yggl.lsys)!=%s AND TRIM(yggl.lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(yggl.zaizhi,0)=0)")
        jp = (LEADER_EXCLUDE_LSYS,)
    else:
        jc = ("gcsqb INNER JOIN yggl ON gcsqb.gcr=yggl.name "
              "AND yggl.lsys=%s AND RIGHT(TRIM(yggl.name),1)!='1' "
              "AND RIGHT(TRIM(yggl.lsys),1)!='1' AND (COALESCE(yggl.zaizhi,0)=0)")
        jp = (lsys,)

    if month:
        ms = date(year, month, 1)
        me = date(year, month, _cal.monthrange(year, month)[1])
        sql = f"""
            SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.yjcfsj
            FROM {jc}
            WHERE RIGHT(TRIM(gcsqb.gcr),1)!='1'
              AND gcsqb.bldzt=2 AND gcsqb.szrzt=2
              AND COALESCE(gcsqb.gcsj,gcsqb.yjcfsj)<=%s
              AND COALESCE(gcsqb.sjfhtime,gcsqb.yjfhsj)>=%s
        """
        rows = db.execute_query(sql, jp + (me.strftime("%Y-%m-%d"), ms.strftime("%Y-%m-%d")))
        clip_start, clip_end = ms, min(me, date.today())
    else:
        sql = f"""
            SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.yjcfsj
            FROM {jc}
            WHERE RIGHT(TRIM(gcsqb.gcr),1)!='1'
              AND gcsqb.bldzt=2 AND gcsqb.szrzt=2
              AND YEAR(COALESCE(gcsqb.gcsj,gcsqb.yjcfsj))=%s
        """
        rows = db.execute_query(sql, jp + (year,))
        clip_start = date(year, 1, 1)
        clip_end = min(date(year, 12, 31), date.today())

    by_person: dict = defaultdict(list)
    for row in (rows or []):
        gcr = (row.get("gcr") or "").strip()
        s = _parse_date(row.get("gcsj") or row.get("yjcfsj"))
        e = _parse_date(row.get("sjfhtime") or row.get("yjfhsj"))
        if s and e and e >= s:
            by_person[gcr].append((max(s, clip_start), min(e, clip_end)))

    result = {}
    for gcr, intervals in by_person.items():
        d = _merge_intervals_days(intervals)
        if d > 0:
            result[gcr] = round(d, 2)
    return result


def _get_staff_with_dept(lsys: Optional[str]) -> list:
    """返回 [{name, lsys}]，在职员工，排除 '部办' 及测试账号"""
    all_staff = not (lsys and lsys.strip())
    if all_staff:
        rows = db.execute_query(
            "SELECT name, lsys FROM yggl WHERE name IS NOT NULL AND name!='' "
            "AND RIGHT(TRIM(name),1)!='1' AND RIGHT(TRIM(lsys),1)!='1' "
            "AND TRIM(lsys)!=%s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(zaizhi,0)=0)",
            (LEADER_EXCLUDE_LSYS,),
        )
    else:
        rows = db.execute_query(
            "SELECT name, lsys FROM yggl WHERE lsys=%s AND name IS NOT NULL AND name!='' "
            "AND RIGHT(TRIM(name),1)!='1' AND RIGHT(TRIM(lsys),1)!='1' "
            "AND TRIM(lsys)!=%s AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') AND (COALESCE(zaizhi,0)=0)",
            (lsys, LEADER_EXCLUDE_LSYS),
        )
    return [{"name": (r["name"] or "").strip(), "lsys": (r.get("lsys") or "").strip()} for r in (rows or []) if (r.get("name") or "").strip()]


@router.get("/leader/work-intensity")
async def get_work_intensity(
    year: int = Query(..., description="年份"),
    month: Optional[int] = Query(None, description="月份，不传则全年"),
    lsys: Optional[str] = Query(None, description="科室，不传则全员"),
):
    """
    工作强度统计 A = 加班时长 / (应出勤时长 - 公出时长)
    时长单位统一为小时（应出勤天数×8，公出天数×8）。
    返回：全部门A、各科室A、每个人的A。
    """
    try:
        HOURS_PER_DAY = 8

        if month:
            workdays = _count_workdays_in_month(year, month)
        else:
            import calendar as _cal2
            workdays = sum(_count_workdays_in_month(year, m) for m in range(1, 13))

        expected_hours = workdays * HOURS_PER_DAY
        staff = _get_staff_with_dept(lsys)
        ot_map = _get_overtime_by_person(year, month, lsys)
        trip_map = _get_trip_days_by_person(year, month, lsys)

        person_list = []
        dept_agg = defaultdict(lambda: {"ot": 0.0, "trip_days": 0.0, "count": 0})

        for s in staff:
            name = s["name"]
            dept = s["lsys"]
            ot = ot_map.get(name, 0)
            trip_d = trip_map.get(name, 0)
            trip_h = trip_d * HOURS_PER_DAY
            actual_h = expected_hours - trip_h
            intensity = round(ot / actual_h, 4) if actual_h > 0 else 0

            person_list.append({
                "name": name,
                "lsys": dept,
                "overtimeHours": round(ot, 2),
                "tripDays": trip_d,
                "actualHours": round(actual_h, 2),
                "intensity": intensity,
            })

            da = dept_agg[dept]
            da["ot"] += ot
            da["trip_days"] += trip_d
            da["count"] += 1

        person_list.sort(key=lambda x: -x["intensity"])

        total_ot = sum(p["overtimeHours"] for p in person_list)
        total_trip_d = sum(p["tripDays"] for p in person_list)
        total_trip_h = total_trip_d * HOURS_PER_DAY
        total_actual = expected_hours * len(staff) - total_trip_h
        overall_intensity = round(total_ot / total_actual, 4) if total_actual > 0 else 0

        dept_list = []
        for dept_name, da in dept_agg.items():
            dept_actual = expected_hours * da["count"] - da["trip_days"] * HOURS_PER_DAY
            dept_i = round(da["ot"] / dept_actual, 4) if dept_actual > 0 else 0
            dept_list.append({
                "lsys": dept_name,
                "personCount": da["count"],
                "overtimeHours": round(da["ot"], 2),
                "tripDays": round(da["trip_days"], 2),
                "intensity": dept_i,
            })
        dept_list.sort(key=lambda x: -x["intensity"])

        return {
            "success": True,
            "workdays": workdays,
            "expectedHoursPerPerson": expected_hours,
            "totalPeople": len(staff),
            "overallIntensity": overall_intensity,
            "byDept": dept_list,
            "byPerson": person_list,
        }
    except Exception as e:
        logger.error(f"工作强度统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
