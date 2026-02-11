# -*- coding: utf-8 -*-
"""
加班与请假统计API路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Tuple
from pydantic import BaseModel
from datetime import datetime, date
import calendar
from database import db
from collections import defaultdict
from routers.approvers import _get_user_info, _jb_match
from utils.helpers import format_datetime_plain
import logging

logger = logging.getLogger(__name__)


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
    """将多个 [start, end] 区间做并集后计算总天数（去重）。与领导人看板一致。"""
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


router = APIRouter(prefix="/report", tags=["报表统计"])


# ==================== 统计汇总权限 ====================
# 1级：仅自己；2级：组长/主任/副主任 可查看隶属科室，下拉选择；3级：部长/副部长 可查看所有人，输入查询


@router.get("/statistics-permission")
async def get_statistics_permission(name: str = Query(..., description="当前用户姓名")):
    """
    统计汇总页权限：1=仅自己 2=科室下拉 3=全部输入查询
    总监、责任工艺师、副总专业师等按1级；按 yggl.jb 职级判定，不做 admin2 特开。
    """
    user = _get_user_info(name)
    if not user:
        return {"success": True, "level": 1, "lsys": "", "name": name}
    jb = (user.get("jb") or "").strip()
    lsys = (user.get("lsys") or "").strip()
    if _jb_match(jb, "部长") or _jb_match(jb, "副部长"):
        return {"success": True, "level": 3, "lsys": lsys, "name": name}
    if _jb_match(jb, "组长") or _jb_match(jb, "主任") or (jb == "副主任" or (jb and "副主任" in jb)):
        return {"success": True, "level": 2, "lsys": lsys, "name": name}
    return {"success": True, "level": 1, "lsys": lsys, "name": name}


@router.get("/overtime-pay-permission")
async def get_overtime_pay_permission(name: str = Query(..., description="当前用户姓名")):
    """
    加班费统计页权限：仅部长/副部长 或 人事管理员（webconfig.admin2）可访问该页面。
    返回 { success, canView: true/false }
    """
    can_view = False
    user = _get_user_info(name)
    if user:
        jb = (user.get("jb") or "").strip()
        if _jb_match(jb, "部长") or _jb_match(jb, "副部长"):
            can_view = True
    if not can_view:
        try:
            wc = db.execute_query("SELECT admin2 FROM webconfig WHERE id = 1 LIMIT 1")
            if wc and wc[0].get("admin2") and (name or "").strip() == (wc[0]["admin2"] or "").strip():
                can_view = True
        except Exception:
            pass
    return {"success": True, "canView": can_view}


@router.get("/statistics-employees")
async def get_statistics_employees(
    current_user: str = Query(..., description="当前登录用户姓名"),
    lsys: Optional[str] = Query(None, description="隶属科室，2级下拉用"),
    q: Optional[str] = Query(None, description="搜索关键词，3级输入查询用"),
    limit: int = Query(50, description="3级搜索返回条数上限")
):
    """
    统计汇总可选员工列表
    - 2级：传 lsys 返回该科室所有员工
    - 3级：传 q 按姓名模糊搜索
    """
    try:
        if lsys:
            rows = db.execute_query(
                "SELECT name FROM yggl WHERE lsys = %s AND name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND (COALESCE(zaizhi,0)=0) ORDER BY name",
                (lsys,)
            )
            names = [r["name"].strip() for r in rows if r.get("name")]
            return {"success": True, "list": names}
        if q and q.strip():
            kw = f"%{q.strip()}%"
            rows = db.execute_query(
                "SELECT name FROM yggl WHERE name LIKE %s AND name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND (COALESCE(zaizhi,0)=0) ORDER BY name LIMIT %s",
                (kw, limit)
            )
            names = [r["name"].strip() for r in rows if r.get("name")]
            return {"success": True, "list": names}
        return {"success": True, "list": []}
    except Exception as e:
        logger.error(f"获取员工列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 数据模型 ====================

class OvertimeRecord(BaseModel):
    """加班记录模型"""
    id: int
    bz: Optional[str] = None  # 部门
    xm: Optional[str] = None  # 姓名
    jiabanfs: Optional[str] = None  # 加班方式
    timedate: Optional[str] = None  # 加班日期
    timefrom: Optional[str] = None  # 开始时间
    timeto: Optional[str] = None  # 结束时间
    jiabantime: Optional[str] = None  # 申请时间
    tian1: Optional[str] = None  # 加班时长（小时）
    jbf: Optional[float] = None  # 加班费小时数
    jiabanzt: Optional[int] = None  # 状态 (4=已通过)
    content: Optional[str] = None  # 内容描述


class LeaveRecord(BaseModel):
    """请假记录模型"""
    id: int
    bz: Optional[str] = None  # 部门
    xm: Optional[str] = None  # 姓名
    qjfs: Optional[str] = None  # 请假方式/类型
    timefrom: Optional[str] = None  # 开始时间
    timeto: Optional[str] = None  # 结束时间
    qjtime: Optional[str] = None  # 申请时间
    tian: Optional[str] = None  # 天数
    xiaoshi: Optional[str] = None  # 小时数
    qjzt: Optional[int] = None  # 状态 (4=已通过)
    content: Optional[str] = None  # 内容描述


class MonthlyOvertimeSummary(BaseModel):
    """月度加班汇总"""
    month: str  # 月份 YYYY-MM
    total_count: int  # 加班次数
    total_hours: float  # 加班总小时数
    overtime_types: dict  # 各类型加班统计


class MonthlyLeaveSummary(BaseModel):
    """月度请假汇总"""
    month: str  # 月份 YYYY-MM
    total_count: int  # 请假次数
    total_days: float  # 请假总天数
    total_hours: float  # 请假总小时数
    leave_types: dict  # 各类型请假统计


class UserStatisticsResponse(BaseModel):
    """用户统计响应"""
    success: bool
    message: Optional[str] = None
    user_name: str
    department: str
    overtime_summary: List[MonthlyOvertimeSummary] = []
    leave_summary: List[MonthlyLeaveSummary] = []
    overtime_records: List[OvertimeRecord] = []
    leave_records: List[LeaveRecord] = []


# ==================== API 路由 ====================

@router.get("/overtime", response_model=dict)
async def get_overtime_records(
    name: str = Query(..., description="员工姓名"),
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份 (1-12)")
):
    """
    获取员工加班记录
    """
    try:
        # 构建查询条件
        if year is None:
            year = datetime.now().year
        
        # 查询加班记录（只查已通过的，jiabanzt=4）
        if month:
            # 查询指定月份
            month_str = f"{year}-{month:02d}"
            query = """
                SELECT id, bz, xm, jiabanfs, timedate, timefrom, timeto, 
                       jiabantime, tian1, jbf, jiabanzt, content
                FROM jiaban 
                WHERE xm = %s AND jiabanzt = 4
                AND (
                    timedate LIKE %s OR
                    substr(timedate, 1, 7) = %s
                )
                ORDER BY timedate DESC
            """
            rows = db.execute_query(query, (name, f"{year}-{month:02d}%", month_str))
        else:
            # 查询全年
            query = """
                SELECT id, bz, xm, jiabanfs, timedate, timefrom, timeto, 
                       jiabantime, tian1, jbf, jiabanzt, content
                FROM jiaban 
                WHERE xm = %s AND jiabanzt = 4
                AND (
                    timedate LIKE %s OR
                    substr(timedate, 1, 4) = %s
                )
                ORDER BY timedate DESC
            """
            rows = db.execute_query(query, (name, f"{year}%", str(year)))
        
        records = []
        total_hours = 0.0
        
        for row in rows:
            record = {
                "id": row["id"],
                "bz": row["bz"],
                "xm": row["xm"],
                "jiabanfs": row["jiabanfs"],
                "timedate": row["timedate"],
                "timefrom": format_datetime_plain(row["timefrom"]),
                "timeto": format_datetime_plain(row["timeto"]),
                "jiabantime": format_datetime_plain(row["jiabantime"]),
                "tian1": row["tian1"],
                "jbf": row["jbf"],
                "jiabanzt": row["jiabanzt"],
                "content": row["content"]
            }
            records.append(record)
            
            # 计算总小时数
            if row["jbf"]:
                total_hours += float(row["jbf"])
            elif row["tian1"]:
                try:
                    total_hours += float(row["tian1"])
                except:
                    pass
        
        return {
            "success": True,
            "name": name,
            "year": year,
            "month": month,
            "total_count": len(records),
            "total_hours": round(total_hours, 2),
            "records": records
        }
    
    except Exception as e:
        logger.error(f"查询加班记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/leave", response_model=dict)
async def get_leave_records(
    name: str = Query(..., description="员工姓名"),
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份 (1-12)")
):
    """
    获取员工请假记录
    """
    try:
        if year is None:
            year = datetime.now().year
        
        # 查询请假记录（只查已通过的，qjzt=4）
        if month:
            month_str = f"{year}-{month:02d}"
            query = """
                SELECT id, bz, xm, qjfs, timefrom, timeto, 
                       qjtime, tian, xiaoshi, qjzt, content
                FROM qj 
                WHERE xm = %s AND qjzt = 4
                AND (
                    timefrom LIKE %s OR
                    substr(timefrom, 1, 7) = %s OR
                    timefromdate LIKE %s OR
                    substr(timefromdate, 1, 7) = %s
                )
                ORDER BY timefrom DESC
            """
            rows = db.execute_query(query, (name, f"{year}-{month:02d}%", month_str, f"{year}-{month:02d}%", month_str))
        else:
            query = """
                SELECT id, bz, xm, qjfs, timefrom, timeto, 
                       qjtime, tian, xiaoshi, qjzt, content
                FROM qj 
                WHERE xm = %s AND qjzt = 4
                AND (
                    timefrom LIKE %s OR
                    substr(timefrom, 1, 4) = %s OR
                    timefromdate LIKE %s OR
                    substr(timefromdate, 1, 4) = %s
                )
                ORDER BY timefrom DESC
            """
            rows = db.execute_query(query, (name, f"{year}%", str(year), f"{year}%", str(year)))
        
        records = []
        total_days = 0.0
        total_hours = 0.0
        
        for row in rows:
            record = {
                "id": row["id"],
                "bz": row["bz"],
                "xm": row["xm"],
                "qjfs": row["qjfs"],
                "timefrom": format_datetime_plain(row["timefrom"]),
                "timeto": format_datetime_plain(row["timeto"]),
                "qjtime": format_datetime_plain(row["qjtime"]),
                "tian": row["tian"],
                "xiaoshi": row["xiaoshi"],
                "qjzt": row["qjzt"],
                "content": row["content"]
            }
            records.append(record)
            
            # 计算总天数和小时数
            if row["tian"]:
                try:
                    total_days += float(row["tian"])
                except:
                    pass
            if row["xiaoshi"]:
                try:
                    total_hours += float(row["xiaoshi"])
                except:
                    pass
        
        return {
            "success": True,
            "name": name,
            "year": year,
            "month": month,
            "total_count": len(records),
            "total_days": round(total_days, 2),
            "total_hours": round(total_hours, 2),
            "records": records
        }
    
    except Exception as e:
        logger.error(f"查询请假记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/business-trip", response_model=dict)
async def get_business_trip_records(
    name: str = Query(..., description="员工姓名"),
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份 (1-12)")
):
    """
    获取员工公出记录。公出天数按实际公出时间计算：有 sjfhtime 用 gcsj～sjfhtime，否则用 gcsj～yjfhsj。
    """
    try:
        if year is None:
            year = datetime.now().year

        if month:
            month_str = f"{year}-{month:02d}"
            query = """
                SELECT id, wpdw, gcdd, gcsj, yjfhsj, sjfhtime, gcrw, gcr
                FROM gcsqb
                WHERE gcr = %s AND (gcsj LIKE %s OR DATE_FORMAT(gcsj, '%%Y-%%m') = %s)
                ORDER BY gcsj DESC
            """
            rows = db.execute_query(query, (name, f"{month_str}%", month_str))
        else:
            query = """
                SELECT id, wpdw, gcdd, gcsj, yjfhsj, sjfhtime, gcrw, gcr
                FROM gcsqb
                WHERE gcr = %s AND (gcsj LIKE %s OR YEAR(gcsj) = %s)
                ORDER BY gcsj DESC
            """
            rows = db.execute_query(query, (name, f"{year}%", year))

        records = []
        total_days = 0.0

        def _fmt(d):
            if d is None:
                return ""
            if hasattr(d, "strftime"):
                return d.strftime("%Y-%m-%d %H:%M")
            return str(d)[:16]

        for row in rows:
            gcsj = row.get("gcsj")
            # 实际公出天数：有实际返回时间用 sjfhtime，否则用预计返回时间 yjfhsj
            end_dt = row.get("sjfhtime") or row.get("yjfhsj") or gcsj
            days = 1.0
            if gcsj and end_dt:
                try:
                    from datetime import datetime as dt
                    d1 = gcsj if hasattr(gcsj, "day") else dt.strptime(str(gcsj)[:10], "%Y-%m-%d")
                    d2 = end_dt if hasattr(end_dt, "day") else dt.strptime(str(end_dt)[:10], "%Y-%m-%d")
                    days = max(1, (d2 - d1).days + 1)
                except Exception:
                    pass
            total_days += days
            records.append({
                "id": row["id"],
                "wpdw": row.get("wpdw"),
                "gcdd": row.get("gcdd"),
                "gcsj": _fmt(gcsj),
                "yjfhsj": _fmt(row.get("yjfhsj")),
                "sjfhtime": _fmt(row.get("sjfhtime")),
                "gcrw": row.get("gcrw"),
                "gcryxm": row.get("gcr"),
                "days": round(days, 2)
            })
        
        return {
            "success": True,
            "name": name,
            "year": year,
            "month": month,
            "total_count": len(records),
            "total_days": round(total_days, 2),
            "records": records
        }
    except Exception as e:
        logger.error(f"查询公出记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/monthly-summary", response_model=dict)
async def get_monthly_summary(
    name: Optional[str] = Query(None, description="员工姓名，不传或空且传 lsys 时为科室全员汇总"),
    lsys: Optional[str] = Query(None, description="隶属科室，全员汇总时必传"),
    year: Optional[int] = Query(None, description="年份")
):
    """
    获取员工月度汇总统计。传 name 为单人；不传 name 且传 lsys 时为该科室全员加和汇总。
    公出计算与领导人看板一致：仅已批准(bldzt=2, szrzt=2)，按区间并集计天数。
    """
    try:
        if year is None:
            year = datetime.now().year
        if not (name or (name is not None and name.strip())):
            name = None
        if name and lsys:
            lsys = None  # 单人查询时忽略 lsys
        if name is None and not lsys:
            raise HTTPException(status_code=400, detail="请指定员工姓名或科室(全员)")

        # 确定要统计的人员列表
        if name:
            names = [name.strip()]
        else:
            rows = db.execute_query(
                "SELECT name FROM yggl WHERE lsys = %s AND name IS NOT NULL AND name != '' AND RIGHT(TRIM(name), 1) != '1' AND RIGHT(TRIM(lsys), 1) != '1' AND (COALESCE(zaizhi,0)=0) ORDER BY name",
                (lsys.strip(),)
            )
            names = [r["name"].strip() for r in rows if r.get("name")]
            if not names:
                return {"success": True, "name": "" if not name else name, "year": year, "monthly": [], "year_total": None}

        monthly_data = {}
        for m in range(1, 13):
            month_key = f"{year}-{m:02d}"
            monthly_data[month_key] = {
                "month": month_key,
                "overtime": {"count": 0, "hours": 0.0, "by_type": {}},
                "leave": {"count": 0, "days": 0.0, "hours": 0.0, "by_type": {}},
                "business_trip": {"count": 0, "days": 0.0}
            }

        for _name in names:
            # 查询加班记录统计
            overtime_query = """
                SELECT id, timedate, jiabanfs, tian1, jbf
                FROM jiaban 
                WHERE xm = %s AND jiabanzt = 4
                AND (
                    timedate LIKE %s OR
                    substr(timedate, 1, 4) = %s
                )
            """
            overtime_rows = db.execute_query(overtime_query, (_name, f"{year}%", str(year)))
        
            for row in overtime_rows:
                timedate = row["timedate"]
                if timedate:
                    try:
                        if "-" in str(timedate):
                            parts = str(timedate).split("-")
                            if len(parts) >= 2:
                                m = int(parts[1])
                                month_key = f"{year}-{m:02d}"
                                if month_key in monthly_data:
                                    monthly_data[month_key]["overtime"]["count"] += 1
                                    hours = 0.0
                                    if row["jbf"]:
                                        hours = float(row["jbf"])
                                    elif row["tian1"]:
                                        try:
                                            hours = float(row["tian1"])
                                        except Exception:
                                            pass
                                    monthly_data[month_key]["overtime"]["hours"] += hours
                                    jb_type = row["jiabanfs"] or "其他"
                                    if jb_type not in monthly_data[month_key]["overtime"]["by_type"]:
                                        monthly_data[month_key]["overtime"]["by_type"][jb_type] = {"count": 0, "hours": 0}
                                    monthly_data[month_key]["overtime"]["by_type"][jb_type]["count"] += 1
                                    monthly_data[month_key]["overtime"]["by_type"][jb_type]["hours"] += hours
                    except Exception:
                        pass

            leave_query = """
                SELECT id, timefrom, timefromdate, qjfs, tian, xiaoshi
                FROM qj 
                WHERE xm = %s AND qjzt = 4
                AND (
                    timefrom LIKE %s OR
                    substr(timefrom, 1, 4) = %s OR
                    timefromdate LIKE %s OR
                    substr(timefromdate, 1, 4) = %s
                )
            """
            leave_rows = db.execute_query(leave_query, (_name, f"{year}%", str(year), f"{year}%", str(year)))

            for row in leave_rows:
                timefrom = row["timefrom"] or row["timefromdate"]
                if timefrom:
                    try:
                        if "-" in str(timefrom):
                            parts = str(timefrom).split("-")
                            if len(parts) >= 2:
                                m = int(parts[1])
                                month_key = f"{year}-{m:02d}"
                                if month_key in monthly_data:
                                    monthly_data[month_key]["leave"]["count"] += 1
                                    days = 0.0
                                    hours = 0.0
                                    if row["tian"]:
                                        try:
                                            days = float(row["tian"])
                                        except Exception:
                                            pass
                                    if row["xiaoshi"]:
                                        try:
                                            hours = float(row["xiaoshi"])
                                        except Exception:
                                            pass
                                    monthly_data[month_key]["leave"]["days"] += days
                                    monthly_data[month_key]["leave"]["hours"] += hours
                                    qj_type = row["qjfs"] or "其他"
                                    if qj_type not in monthly_data[month_key]["leave"]["by_type"]:
                                        monthly_data[month_key]["leave"]["by_type"][qj_type] = {"count": 0, "days": 0, "hours": 0}
                                    monthly_data[month_key]["leave"]["by_type"][qj_type]["count"] += 1
                                    monthly_data[month_key]["leave"]["by_type"][qj_type]["days"] += days
                                    monthly_data[month_key]["leave"]["by_type"][qj_type]["hours"] += hours
                    except Exception:
                        pass

            # 公出：与领导人看板一致，仅已批准(bldzt=2, szrzt=2)，按区间并集计天数
            bt_raw_query = """
                SELECT gcsj, yjfhsj, sjfhtime, wpsj
                FROM gcsqb
                WHERE gcr = %s AND (bldzt = 2 AND szrzt = 2)
                  AND (wpsj LIKE %s OR gcsj LIKE %s OR YEAR(COALESCE(gcsj, wpsj)) = %s)
            """
            bt_rows = db.execute_query(bt_raw_query, (_name, f"{year}%", f"{year}%", year))
            by_month_intervals = defaultdict(list)
            for row in bt_rows:
                start_d = _parse_date(row.get("gcsj") or row.get("wpsj"))
                end_d = _parse_date(row.get("sjfhtime") or row.get("yjfhsj") or row.get("gcsj") or row.get("wpsj"))
                if not start_d or not end_d or end_d < start_d:
                    continue
                for m in range(1, 13):
                    month_start = date(year, m, 1)
                    _, last_d = calendar.monthrange(year, m)
                    month_end = date(year, m, last_d)
                    if start_d <= month_end and end_d >= month_start:
                        by_month_intervals[m].append((max(start_d, month_start), min(end_d, month_end)))
            for m in range(1, 13):
                month_key = f"{year}-{m:02d}"
                intervals = by_month_intervals.get(m, [])
                days = _merge_intervals_days(intervals)
                if days > 0:
                    monthly_data[month_key]["business_trip"]["count"] += 1
                    monthly_data[month_key]["business_trip"]["days"] += days
        
        # 转换为列表并四舍五入
        monthly_list = []
        for month_key in sorted(monthly_data.keys()):
            data = monthly_data[month_key]
            data["overtime"]["hours"] = round(data["overtime"]["hours"], 2)
            data["leave"]["days"] = round(data["leave"]["days"], 2)
            data["leave"]["hours"] = round(data["leave"]["hours"], 2)
            data["business_trip"]["days"] = round(data["business_trip"]["days"], 2)
            
            # 四舍五入类型统计
            for t in data["overtime"]["by_type"]:
                data["overtime"]["by_type"][t]["hours"] = round(data["overtime"]["by_type"][t]["hours"], 2)
            for t in data["leave"]["by_type"]:
                data["leave"]["by_type"][t]["days"] = round(data["leave"]["by_type"][t]["days"], 2)
                data["leave"]["by_type"][t]["hours"] = round(data["leave"]["by_type"][t]["hours"], 2)
            
            monthly_list.append(data)
        
        # 计算年度总计
        year_total = {
            "overtime": {
                "count": sum(m["overtime"]["count"] for m in monthly_list),
                "hours": round(sum(m["overtime"]["hours"] for m in monthly_list), 2)
            },
            "leave": {
                "count": sum(m["leave"]["count"] for m in monthly_list),
                "days": round(sum(m["leave"]["days"] for m in monthly_list), 2),
                "hours": round(sum(m["leave"]["hours"] for m in monthly_list), 2)
            },
            "business_trip": {
                "count": sum(m["business_trip"]["count"] for m in monthly_list),
                "days": round(sum(m["business_trip"]["days"] for m in monthly_list), 2)
            }
        }
        
        return {
            "success": True,
            "name": (name if name else ""),
            "lsys": (lsys if not name and lsys else None),
            "year": year,
            "monthly": monthly_list,
            "year_total": year_total
        }
    
    except Exception as e:
        logger.error(f"查询月度汇总失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/leave-types", response_model=dict)
async def get_leave_types():
    """
    获取所有请假类型
    """
    try:
        rows = db.execute_query("SELECT DISTINCT qjfs FROM qj WHERE qjfs IS NOT NULL AND qjfs != ''")
        types = [row["qjfs"] for row in rows]
        
        return {
            "success": True,
            "types": types
        }
    
    except Exception as e:
        logger.error(f"获取请假类型失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/overtime-types", response_model=dict)
async def get_overtime_types():
    """
    获取所有加班类型
    """
    try:
        rows = db.execute_query("SELECT DISTINCT jiabanfs FROM jiaban WHERE jiabanfs IS NOT NULL AND jiabanfs != ''")
        types = [row["jiabanfs"] for row in rows]
        
        return {
            "success": True,
            "types": types
        }
    
    except Exception as e:
        logger.error(f"获取加班类型失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
