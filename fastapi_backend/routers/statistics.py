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
    - 春节/国庆节/高温防暑休假 这三类节日当天：若当日加班时长(已扣午休) >= 8 小时，则这天加班费固定 200 元；
      超过 8 小时不再额外计算；这些小时不再计入普通 15 元/小时部分。
    - 其他日期或不足 8 小时的节日，加班费按 15 元/小时计算。
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
            # 激励日且当日加班满 8 小时：固定 200 元，不再按小时计费
            incentive_pay = 200.0
            normal_hours = 0.0
        else:
            # 非激励日或不足 8 小时：全部按普通时薪计算
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
            "SELECT DISTINCT lsys FROM yggl WHERE lsys IS NOT NULL AND lsys != '' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND (COALESCE(zaizhi,0)=0) ORDER BY lsys",
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
    quarter: Optional[str] = None
):
    """
    科室请假统计（按人汇总天数）。不传 lsys 时为全员（排除部办）。
    返回: { totalDays, personCount, list: [{ name, days }] }
    仅统计 qjzt=4 已通过
    """
    try:
        if year is None:
            year = __import__("datetime").datetime.now().year
        all_staff = not (lsys and lsys.strip())

        # 月度
        if month:
            month_str = f"{year}-{month:02d}"
            if all_staff:
                query = """
                    SELECT xm AS name, SUM(CAST(tian AS DECIMAL(10,2))) AS days
                    FROM qj
                    WHERE qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s
                    AND (timefrom LIKE %s OR timefromdate LIKE %s OR SUBSTRING(timefrom, 1, 7) = %s)
                    GROUP BY xm
                    ORDER BY days DESC
                """
                rows = db.execute_query(query, (LEADER_EXCLUDE_LSYS, f"{month_str}%", f"{month_str}%", month_str))
            else:
                query = """
                    SELECT xm AS name, SUM(CAST(tian AS DECIMAL(10,2))) AS days
                    FROM qj
                    WHERE lsys = %s AND qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1'
                    AND (timefrom LIKE %s OR timefromdate LIKE %s OR SUBSTRING(timefrom, 1, 7) = %s)
                    GROUP BY xm
                    ORDER BY days DESC
                """
                rows = db.execute_query(query, (lsys, f"{month_str}%", f"{month_str}%", month_str))
        # 年度或季度
        else:
            if quarter:
                if quarter == "1":
                    mon_cond = "MONTH(timefrom) BETWEEN 1 AND 3"
                elif quarter == "2":
                    mon_cond = "MONTH(timefrom) BETWEEN 4 AND 6"
                elif quarter == "3":
                    mon_cond = "MONTH(timefrom) BETWEEN 7 AND 9"
                else:
                    mon_cond = "MONTH(timefrom) BETWEEN 10 AND 12"
                if all_staff:
                    query = f"""
                        SELECT xm AS name, SUM(CAST(tian AS DECIMAL(10,2))) AS days
                        FROM qj
                        WHERE qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s
                        AND YEAR(timefrom) = %s AND {mon_cond}
                        GROUP BY xm
                        ORDER BY days DESC
                    """
                    rows = db.execute_query(query, (LEADER_EXCLUDE_LSYS, year))
                else:
                    query = f"""
                        SELECT xm AS name, SUM(CAST(tian AS DECIMAL(10,2))) AS days
                        FROM qj
                        WHERE lsys = %s AND qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1'
                        AND YEAR(timefrom) = %s AND {mon_cond}
                        GROUP BY xm
                        ORDER BY days DESC
                    """
                    rows = db.execute_query(query, (lsys, year))
            else:
                if all_staff:
                    query = """
                        SELECT xm AS name, SUM(CAST(tian AS DECIMAL(10,2))) AS days
                        FROM qj
                        WHERE qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s
                        AND (timefrom LIKE %s OR timefromdate LIKE %s OR YEAR(timefrom) = %s)
                        GROUP BY xm
                        ORDER BY days DESC
                    """
                    rows = db.execute_query(query, (LEADER_EXCLUDE_LSYS, f"{year}%", f"{year}%", year))
                else:
                    query = """
                        SELECT xm AS name, SUM(CAST(tian AS DECIMAL(10,2))) AS days
                        FROM qj
                        WHERE lsys = %s AND qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1'
                        AND (timefrom LIKE %s OR timefromdate LIKE %s OR YEAR(timefrom) = %s)
                        GROUP BY xm
                        ORDER BY days DESC
                    """
                    rows = db.execute_query(query, (lsys, f"{year}%", f"{year}%", year))

        list_data = []
        total_days = 0
        for r in rows:
            d = float(r.get("days") or 0)
            list_data.append({"name": r.get("name") or "", "days": round(d, 2)})
            total_days += d

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

@router.get("/dept/overtime")
async def get_dept_overtime_stats(
    lsys: Optional[str] = Query(None, description="隶属于室，不传或空为全员"),
    year: Optional[int] = None,
    month: Optional[int] = None,
    quarter: Optional[str] = None
):
    """
    科室加班统计（按人汇总小时）。不传 lsys 时为全员（排除部办）。
    返回: { totalHours, personCount, list: [{ name, hours }] }
    仅统计 jiabanzt=4 已通过
    """
    try:
        if year is None:
            year = __import__("datetime").datetime.now().year
        all_staff = not (lsys and lsys.strip())

        # 通过 yggl 关联；全员时仅排除部办
        if all_staff:
            join_cond = "INNER JOIN yggl ON jiaban.xm = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) != %s AND (COALESCE(yggl.zaizhi,0)=0)"
            join_param = (LEADER_EXCLUDE_LSYS,)
        else:
            join_cond = "INNER JOIN yggl ON jiaban.xm = yggl.name AND yggl.lsys = %s AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND (COALESCE(yggl.zaizhi,0)=0)"
            join_param = (lsys,)
        if month:
            month_str = f"{year}-{month:02d}"
            query = f"""
                SELECT jiaban.xm AS name, SUM(CAST(COALESCE(jiaban.jbf, jiaban.tian1, 0) AS DECIMAL(10,2))) AS hours
                FROM jiaban {join_cond}
                WHERE jiaban.jiabanzt = 4
                AND (jiaban.timedate LIKE %s OR SUBSTRING(jiaban.timedate, 1, 7) = %s)
                GROUP BY jiaban.xm
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
                    SELECT jiaban.xm AS name, SUM(CAST(COALESCE(jiaban.jbf, jiaban.tian1, 0) AS DECIMAL(10,2))) AS hours
                    FROM jiaban {join_cond}
                    WHERE jiaban.jiabanzt = 4
                    AND YEAR(jiaban.timedate) = %s AND {mon_cond}
                    GROUP BY jiaban.xm
                    ORDER BY hours DESC
                """
                rows = db.execute_query(query, join_param + (year,))
            else:
                query = f"""
                    SELECT jiaban.xm AS name, SUM(CAST(COALESCE(jiaban.jbf, jiaban.tian1, 0) AS DECIMAL(10,2))) AS hours
                    FROM jiaban {join_cond}
                    WHERE jiaban.jiabanzt = 4
                    AND (jiaban.timedate LIKE %s OR YEAR(jiaban.timedate) = %s)
                    GROUP BY jiaban.xm
                    ORDER BY hours DESC
                """
                rows = db.execute_query(query, join_param + (f"{year}%", year))

        list_data = []
        total_hours = 0
        for r in rows:
            h = float(r.get("hours") or 0)
            list_data.append({"name": r.get("name") or "", "hours": round(h, 2)})
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


@router.get("/dept/overtime-pay-by-month")
async def get_dept_overtime_pay_by_month(
    lsys: Optional[str] = Query(None, description="隶属于室，不传或空为全员"),
    year: Optional[int] = None,
    month: Optional[int] = Query(None, ge=1, le=12, description="筛选月份，不传为全年"),
    name: Optional[str] = Query(None, description="仅查某人（如普通员工查本人）"),
):
    """
    加班费按月份统计。仅统计 jiaban 审核完成(jiabanzt=4)、换休票为否(hx 非「是」)，
    激励规则：
    - 若某天是假期表中节日为 春节/国庆节/高温防暑休假，且当天加班时长(已扣午休) >= 8 小时，则该天加班费固定 200 元；
      超出 8 小时部分不再额外计算；
    - 其他日期或不足 8 小时部分，按 webconfig.zhibanfei（默认 15 元/小时）计算；
    支持 name=某人 仅查本人；month=1~12 仅查该月。
    返回: { success, zhibanfei, list: [{ month, monthLabel, hours, pay }] }
    """
    try:
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
                join_cond = "INNER JOIN yggl ON jiaban.xm = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) != %s AND (COALESCE(yggl.zaizhi,0)=0)"
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
        logger.error(f"加班费按月考勤失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dept/overtime-pay-by-employee")
async def get_dept_overtime_pay_by_employee(
    lsys: Optional[str] = Query(None, description="隶属于室，不传或空返回空列表（传 name 时可为空）"),
    year: Optional[int] = None,
    month: Optional[int] = Query(None, ge=1, le=12, description="筛选月份，不传为全年"),
    name: Optional[str] = Query(None, description="仅查某人（如普通员工查本人）"),
):
    """
    科室员工加班费明细：指定科室、年份，按人汇总（审核通过且换休票为否）。
    激励规则与 /dept/overtime-pay-by-month 相同。
    支持 name=某人 仅查本人；month=1~12 仅查该月。
    返回: { success, zhibanfei, list: [{ name, hours, pay }] }
    """
    try:
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
        logger.error(f"加班费按员工统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dept/overtime-pay-export")
async def get_overtime_pay_export(
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份（必选，用于按月工资报表）"),
):
    """
    按月导出加班费工资报表数据：全员 + 各科室。
    以 yggl 名单为准，当月无加班记录者本月加班费为 0，保证科室人全。
    加班费计算采用与统计页面相同的节日激励规则。
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

        # 本月所有加班记录（不区分科室），用于计算激励与普通加班费
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
              AND (COALESCE(yggl.zaizhi,0)=0)
        """
        month_key = f"{year}-{month:02d}"
        rows = db.execute_query(q_rows, (year, month, month_key))

        holiday_map = _load_holiday_festival_map(year)
        _, per_employee = _aggregate_overtime_with_incentive(rows, holiday_map, zhibanfei)

        # 先准备全员名单（排除部办），再按 per_employee 中的 pay 填值，保证人全
        yggl_rows = db.execute_query(
            "SELECT name, lsys FROM yggl WHERE lsys IS NOT NULL AND lsys != '' AND RIGHT(TRIM(lsys), 1) != '1' "
            "AND TRIM(lsys) != %s AND RIGHT(TRIM(name), 1) != '1' AND (COALESCE(zaizhi,0)=0)",
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

        return {"success": True, "zhibanfei": zhibanfei, "all": list_all, "byDept": by_dept}
    except Exception as e:
        logger.error(f"加班费按月导出失败: {str(e)}")
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
                AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) != %s AND (COALESCE(yggl.zaizhi,0)=0)
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
                SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.wpsj
                FROM {join_cond}
                WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                  AND COALESCE(gcsqb.gcsj, gcsqb.wpsj) <= %s AND COALESCE(gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.gcsj, gcsqb.wpsj) >= %s
            """
            trip_rows = db.execute_query(trip_raw_query, join_param + (month_end.strftime("%Y-%m-%d"), month_start.strftime("%Y-%m-%d")))
        elif quarter and q_start and q_end:
            month_str_s = q_start.strftime("%Y-%m-%d")
            month_str_e = q_end.strftime("%Y-%m-%d")
            trip_raw_query = f"""
                SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.wpsj
                FROM {join_cond}
                WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                  AND COALESCE(gcsqb.gcsj, gcsqb.wpsj) <= %s AND COALESCE(gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.gcsj, gcsqb.wpsj) >= %s
            """
            trip_rows = db.execute_query(trip_raw_query, join_param + (month_str_e, month_str_s))
        else:
            month_str = f"{year}%"
            trip_raw_query = f"""
                SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.wpsj
                FROM {join_cond}
                WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                  AND (gcsqb.wpsj LIKE %s OR gcsqb.gcsj LIKE %s OR YEAR(COALESCE(gcsqb.gcsj, gcsqb.wpsj)) = %s)
            """
            trip_rows = db.execute_query(trip_raw_query, join_param + (month_str, month_str, year))

        by_person: dict = defaultdict(list)
        for row in trip_rows:
            gcr = (row.get("gcr") or "").strip()
            start_d = _parse_date(row.get("gcsj") or row.get("wpsj"))
            end_d = _parse_date(row.get("sjfhtime") or row.get("yjfhsj") or row.get("gcsj") or row.get("wpsj"))
            if start_d and end_d and end_d >= start_d:
                by_person[gcr].append((start_d, end_d))

        list_data = []
        for gcr, intervals in by_person.items():
            if not intervals:
                continue
            if month and month_start and month_end:
                clipped = [(max(s, month_start), min(e, month_end)) for s, e in intervals if s <= month_end and e >= month_start]
            elif quarter and q_start and q_end:
                clipped = [(max(s, q_start), min(e, q_end)) for s, e in intervals if s <= q_end and e >= q_start]
            else:
                clipped = [(max(s, year_start), min(e, year_end)) for s, e in intervals if s <= year_end and e >= year_start]
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


# ==================== 领导人看板扩展 API ====================

@router.get("/leader/full-attendance")
async def get_leader_full_attendance(
    year: int = Query(..., description="年份"),
    month: int = Query(..., description="月份"),
    lsys: Optional[str] = Query(None, description="隶属科室，不传则全员")
):
    """
    满勤率：指定月份全员或指定科室的满勤率。
    满勤 = 当月没有请假（即无请假记录或请假天数为 0）。
    返回: workdays(当月应出勤工作日，仅作参考), totalPeople, fullCount, rate, byDept(仅当未传lsys时)
    """
    try:
        workdays = _count_workdays_in_month(year, month)
        month_str = f"{year}-{month:02d}"

        if lsys:
            rows = db.execute_query(
                "SELECT name FROM yggl WHERE lsys = %s AND name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND (COALESCE(zaizhi,0)=0)",
                (lsys, LEADER_EXCLUDE_LSYS)
            )
            names = [r["name"].strip() for r in rows if r.get("name")]
        else:
            rows = db.execute_query(
                "SELECT name, lsys FROM yggl WHERE name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND (COALESCE(zaizhi,0)=0)",
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
                "byDept": []
            }

        # 当月有请假的人员及其请假天数（仅已通过 qjzt=4）；排除名字末尾为1
        leave_rows = db.execute_query(
            """SELECT xm AS name, SUM(CAST(tian AS DECIMAL(10,2))) AS days
               FROM qj
               WHERE qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1' AND (timefrom LIKE %s OR timefromdate LIKE %s OR SUBSTRING(timefrom, 1, 7) = %s)
               GROUP BY xm""",
            (f"{month_str}%", f"{month_str}%", month_str)
        )
        # 满勤 = 当月没有请假 或 请假天数为 0
        leave_days_map = {}
        for r in leave_rows:
            n = (r.get("name") or "").strip()
            d = float(r.get("days") or 0)
            if n:
                leave_days_map[n] = d
        full_count = sum(1 for n in names if leave_days_map.get(n, 0) <= 0)
        total = len(names)
        rate = round(full_count / total, 4) if total else 0

        result = {
            "success": True,
            "workdays": workdays,
            "totalPeople": total,
            "fullCount": full_count,
            "rate": rate,
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
                fc = sum(1 for n in nlist if leave_days_map.get(n, 0) <= 0)
                tot = len(nlist)
                by_dept.append({
                    "lsys": d,
                    "totalPeople": tot,
                    "fullCount": fc,
                    "rate": round(fc / tot, 4) if tot else 0
                })
            result["byDept"] = by_dept

        return result
    except Exception as e:
        logger.error(f"满勤率查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leader/full-attendance-year")
async def get_leader_full_attendance_year(
    year: int = Query(..., description="年份"),
    lsys: Optional[str] = Query(None, description="隶属科室，不传则全员")
):
    """
    满勤率（全年）：指定年份全员或指定科室的全年满勤率。
    全年满勤 = 该年度内无请假（即该年请假总天数<=0，仅统计已通过请假记录）。
    返回: totalPeople, fullCount, rate, byDept(仅当未传lsys时)，无 workdays。
    """
    try:
        year_prefix = f"{year}-"
        if lsys:
            rows = db.execute_query(
                "SELECT name FROM yggl WHERE lsys = %s AND name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND (COALESCE(zaizhi,0)=0)",
                (lsys, LEADER_EXCLUDE_LSYS)
            )
            names = [r["name"].strip() for r in rows if r.get("name")]
        else:
            rows = db.execute_query(
                "SELECT name, lsys FROM yggl WHERE name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND (COALESCE(zaizhi,0)=0)",
                (LEADER_EXCLUDE_LSYS,)
            )
            names = [r["name"].strip() for r in rows if r.get("name")]

        if not names:
            return {
                "success": True,
                "totalPeople": 0,
                "fullCount": 0,
                "rate": 0,
                "byDept": []
            }

        # 该年度内每人请假总天数（仅已通过 qjzt=4）
        leave_rows = db.execute_query(
            """SELECT xm AS name, SUM(CAST(tian AS DECIMAL(10,2))) AS days
               FROM qj
               WHERE qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1'
                 AND (timefrom LIKE %s OR timefromdate LIKE %s OR SUBSTRING(timefrom, 1, 4) = %s)
               GROUP BY xm""",
            (f"{year_prefix}%", f"{year_prefix}%", str(year))
        )
        leave_days_map = {}
        for r in leave_rows:
            n = (r.get("name") or "").strip()
            d = float(r.get("days") or 0)
            if n:
                leave_days_map[n] = d
        full_count = sum(1 for n in names if leave_days_map.get(n, 0) <= 0)
        total = len(names)
        rate = round(full_count / total, 4) if total else 0

        result = {
            "success": True,
            "totalPeople": total,
            "fullCount": full_count,
            "rate": rate,
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
                fc = sum(1 for n in nlist if leave_days_map.get(n, 0) <= 0)
                tot = len(nlist)
                by_dept.append({
                    "lsys": d,
                    "totalPeople": tot,
                    "fullCount": fc,
                    "rate": round(fc / tot, 4) if tot else 0
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
    满勤 = 当月没有请假。返回 12 个月每月的 fullCount、totalPeople。
    返回: list[{ month, monthLabel, fullCount, totalPeople }]
    """
    try:
        list_data = []
        for month in range(1, 13):
            month_str = f"{year}-{month:02d}"
            if lsys:
                rows = db.execute_query(
                    "SELECT name FROM yggl WHERE lsys = %s AND name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND (COALESCE(zaizhi,0)=0)",
                    (lsys, LEADER_EXCLUDE_LSYS)
                )
                names = [r["name"].strip() for r in rows if r.get("name")]
            else:
                rows = db.execute_query(
                    "SELECT name FROM yggl WHERE name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s AND (COALESCE(zaizhi,0)=0)",
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

            leave_rows = db.execute_query(
                """SELECT xm AS name, SUM(CAST(tian AS DECIMAL(10,2))) AS days
                   FROM qj
                   WHERE qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1' AND (timefrom LIKE %s OR timefromdate LIKE %s OR SUBSTRING(timefrom, 1, 7) = %s)
                   GROUP BY xm""",
                (f"{month_str}%", f"{month_str}%", month_str)
            )
            leave_days_map = {}
            for r in leave_rows:
                n = (r.get("name") or "").strip()
                d = float(r.get("days") or 0)
                if n:
                    leave_days_map[n] = d
            full_count = sum(1 for n in names if leave_days_map.get(n, 0) <= 0)
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
        month_str = f"{year}-{month:02d}%" if month else f"{year}%"
        month_cond_leave = "AND (timefrom LIKE %s OR SUBSTRING(timefrom, 1, 7) = %s)" if month else "AND (timefrom LIKE %s OR YEAR(timefrom) = %s)"
        month_cond_overtime = "AND (timedate LIKE %s OR SUBSTRING(timedate, 1, 7) = %s)" if month else "AND (timedate LIKE %s OR YEAR(timedate) = %s)"
        params_leave = (month_str, month_str) if month else (month_str, year)
        params_overtime = (month_str, month_str) if month else (month_str, year)

        person_rows = db.execute_query(
            "SELECT lsys, COUNT(*) AS cnt FROM yggl WHERE lsys IS NOT NULL AND lsys != '' AND RIGHT(TRIM(lsys), 1) != '1' AND RIGHT(TRIM(name), 1) != '1' AND TRIM(lsys) != %s AND (COALESCE(zaizhi,0)=0) GROUP BY lsys ORDER BY lsys",
            (LEADER_EXCLUDE_LSYS,)
        )
        person_by_lsys = {r["lsys"].strip(): int(r.get("cnt") or 0) for r in person_rows if r.get("lsys")}

        leave_query = f"""
            SELECT lsys, SUM(CAST(tian AS DECIMAL(10,2))) AS total
            FROM qj WHERE qjzt = 4 AND RIGHT(TRIM(xm), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND TRIM(lsys) != %s {month_cond_leave}
            GROUP BY lsys
        """
        leave_rows = db.execute_query(leave_query, (LEADER_EXCLUDE_LSYS,) + tuple(params_leave))
        leave_by_lsys = {r["lsys"].strip(): round(float(r.get("total") or 0), 2) for r in leave_rows if r.get("lsys")}

        overtime_query = f"""
            SELECT yggl.lsys, SUM(CAST(COALESCE(jiaban.jbf, jiaban.tian1, 0) AS DECIMAL(10,2))) AS total
            FROM jiaban INNER JOIN yggl ON jiaban.xm = yggl.name AND yggl.lsys IS NOT NULL AND yggl.lsys != '' AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND (COALESCE(yggl.zaizhi,0)=0)
            WHERE jiaban.jiabanzt = 4 {month_cond_overtime}
            GROUP BY yggl.lsys
        """
        ot_rows = db.execute_query(overtime_query, params_overtime)
        overtime_by_lsys = {r["lsys"].strip(): round(float(r.get("total") or 0), 2) for r in ot_rows if r.get("lsys")}

        # 公出与「全体员工排序」一致：仅已批准(bldzt=2, szrzt=2)，按区间并集计天数后按科室汇总
        import calendar
        month_start = date(year, month, 1) if month else None
        month_end = date(year, month, calendar.monthrange(year, month)[1]) if month else None
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        if month:
            trip_raw_query = """
                SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.wpsj, yggl.lsys
                FROM gcsqb INNER JOIN yggl ON gcsqb.gcr = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) != %s AND (COALESCE(yggl.zaizhi,0)=0)
                WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                  AND COALESCE(gcsqb.gcsj, gcsqb.wpsj) <= %s AND COALESCE(gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.gcsj, gcsqb.wpsj) >= %s
            """
            trip_rows = db.execute_query(trip_raw_query, (LEADER_EXCLUDE_LSYS, month_end.strftime("%Y-%m-%d"), month_start.strftime("%Y-%m-%d")))
        else:
            trip_raw_query = """
                SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.wpsj, yggl.lsys
                FROM gcsqb INNER JOIN yggl ON gcsqb.gcr = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND TRIM(yggl.lsys) != %s AND (COALESCE(yggl.zaizhi,0)=0)
                WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                  AND (gcsqb.wpsj LIKE %s OR gcsqb.gcsj LIKE %s OR YEAR(COALESCE(gcsqb.gcsj, gcsqb.wpsj)) = %s)
            """
            trip_rows = db.execute_query(trip_raw_query, (LEADER_EXCLUDE_LSYS, month_str, month_str, year))
        by_person_trip: dict = defaultdict(list)
        for row in trip_rows:
            gcr = (row.get("gcr") or "").strip()
            lsys = (row.get("lsys") or "").strip()
            if not lsys:
                continue
            start_d = _parse_date(row.get("gcsj") or row.get("wpsj"))
            end_d = _parse_date(row.get("sjfhtime") or row.get("yjfhsj") or row.get("gcsj") or row.get("wpsj"))
            if start_d and end_d and end_d >= start_d:
                by_person_trip[(gcr, lsys)].append((start_d, end_d))
        trip_by_lsys = defaultdict(float)
        for (gcr, lsys), intervals in by_person_trip.items():
            if not intervals:
                continue
            if month and month_start and month_end:
                clipped = [(max(s, month_start), min(e, month_end)) for s, e in intervals if s <= month_end and e >= month_start]
            else:
                clipped = [(max(s, year_start), min(e, year_end)) for s, e in intervals if s <= year_end and e >= year_start]
            days = _merge_intervals_days(clipped)
            if days > 0:
                trip_by_lsys[lsys] += round(days, 2)
        trip_by_lsys = dict(trip_by_lsys)

        all_lsys = sorted(person_by_lsys.keys())
        list_data = []
        for l in all_lsys:
            pc = person_by_lsys.get(l, 0)
            ot = overtime_by_lsys.get(l, 0)
            lv = leave_by_lsys.get(l, 0)
            tr = trip_by_lsys.get(l, 0)
            list_data.append({
                "lsys": l,
                "personCount": pc,
                "overtimeTotal": ot,
                "leaveTotal": lv,
                "tripTotal": tr,
                "overtimePerCapita": round(ot / pc, 2) if pc else 0,
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
        month_str = f"{year}-{month:02d}%" if month else f"{year}%"
        month_param = (month_str, month_str) if month else (month_str, year)

        if type_ == "overtime":
            query = """
                SELECT jiaban.xm AS name, yggl.lsys,
                    SUM(CAST(COALESCE(jiaban.jbf, jiaban.tian1, 0) AS DECIMAL(10,2))) AS value
                FROM jiaban INNER JOIN yggl ON jiaban.xm = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND (COALESCE(yggl.zaizhi,0)=0)
                WHERE jiaban.jiabanzt = 4 AND RIGHT(TRIM(jiaban.xm), 1) != '1' AND (jiaban.timedate LIKE %s OR YEAR(jiaban.timedate) = %s)
                GROUP BY jiaban.xm, yggl.lsys ORDER BY value DESC
            """
            unit = "小时"
        elif type_ == "leave":
            query = """
                SELECT qj.xm AS name, qj.lsys,
                    SUM(CAST(qj.tian AS DECIMAL(10,2))) AS value
                FROM qj WHERE qj.qjzt = 4 AND RIGHT(TRIM(qj.xm), 1) != '1' AND RIGHT(TRIM(qj.lsys), 1) != '1' AND (qj.timefrom LIKE %s OR YEAR(qj.timefrom) = %s)
                GROUP BY qj.xm, qj.lsys ORDER BY value DESC
            """
            unit = "天"
        elif type_ == "trip":
            # 公出天数按区间并集计算，避免重复申报导致超过 365 天
            import calendar
            month_start = date(year, month, 1) if month else None
            month_end = date(year, month, calendar.monthrange(year, month)[1]) if month else None
            if month:
                trip_raw_query = """
                    SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.wpsj, yggl.lsys
                    FROM gcsqb INNER JOIN yggl ON gcsqb.gcr = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND (COALESCE(yggl.zaizhi,0)=0)
                    WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                      AND COALESCE(gcsqb.gcsj, gcsqb.wpsj) <= %s AND COALESCE(gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.gcsj, gcsqb.wpsj) >= %s
                """
                trip_rows = db.execute_query(trip_raw_query, (month_end.strftime("%Y-%m-%d"), month_start.strftime("%Y-%m-%d")))
            else:
                trip_raw_query = """
                    SELECT gcsqb.gcr, gcsqb.gcsj, gcsqb.sjfhtime, gcsqb.yjfhsj, gcsqb.wpsj, yggl.lsys
                    FROM gcsqb INNER JOIN yggl ON gcsqb.gcr = yggl.name AND RIGHT(TRIM(yggl.name), 1) != '1' AND RIGHT(TRIM(yggl.lsys), 1) != '1' AND (COALESCE(yggl.zaizhi,0)=0)
                    WHERE RIGHT(TRIM(gcsqb.gcr), 1) != '1' AND (gcsqb.bldzt = 2 AND gcsqb.szrzt = 2)
                      AND (gcsqb.wpsj LIKE %s OR gcsqb.gcsj LIKE %s OR YEAR(COALESCE(gcsqb.gcsj, gcsqb.wpsj)) = %s)
                """
                trip_param = (month_str, month_str, year)
                trip_rows = db.execute_query(trip_raw_query, trip_param)
            # 按 (gcr, lsys) 分组，每人收集 [start, end] 区间后做并集再算天数
            by_person: dict = defaultdict(list)
            for row in trip_rows:
                gcr = (row.get("gcr") or "").strip()
                lsys = (row.get("lsys") or "").strip()
                start_d = _parse_date(row.get("gcsj") or row.get("wpsj"))
                end_d = _parse_date(row.get("sjfhtime") or row.get("yjfhsj") or row.get("gcsj") or row.get("wpsj"))
                if start_d and end_d and end_d >= start_d:
                    by_person[(gcr, lsys)].append((start_d, end_d))
            list_trip = []
            year_start = date(year, 1, 1)
            year_end = date(year, 12, 31)
            for (gcr, lsys), intervals in by_person.items():
                if not intervals:
                    continue
                if month and month_start and month_end:
                    # 指定月份时：只保留区间与当月交集的并集天数
                    clipped = [(max(s, month_start), min(e, month_end)) for s, e in intervals if s <= month_end and e >= month_start]
                    days = _merge_intervals_days(clipped)
                else:
                    # 全年时：只统计该年内的天数，区间裁剪到 [year-01-01, year-12-31]
                    clipped = [(max(s, year_start), min(e, year_end)) for s, e in intervals if s <= year_end and e >= year_start]
                    days = _merge_intervals_days(clipped)
                if days > 0:
                    list_trip.append({"name": gcr, "lsys": lsys, "value": round(days, 2)})
            list_trip.sort(key=lambda x: -x["value"])
            rows = list_trip
            unit = "天"
        else:
            raise HTTPException(status_code=400, detail="type 须为 overtime|leave|trip")

        if type_ != "trip":
            rows = db.execute_query(query, month_param)
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
