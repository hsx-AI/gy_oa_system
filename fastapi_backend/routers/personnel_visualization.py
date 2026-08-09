# -*- coding: utf-8 -*-
"""
人员出勤可视化聚合接口
"""
import logging
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from attendance_db import attendance_db
from database import db
from routers.approvers import _get_user_info, _jb_match, is_zonghe_tech_director
from routers.db_manager import _get_admin1

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/personnel-visualization", tags=["人员出勤可视化"])


DEPT_ORDER = [
    "部办",
    "综合技术室",
    "工具技术室",
    "数控编程室",
    "智能制造技术室",
    "水发工艺室",
    "水轮机工艺室",
    "汽发工艺室",
    "焊接工艺室",
    "非标技术室",
]

JB_RANK = [
    ("副经理", 2),
    ("经理", 1),
    ("副主任", 4),
    ("主任", 3),
    ("副组长", 6),
    ("组长", 5),
]


def _jb_sort_key(jb: str) -> int:
    jb = (jb or "").strip()
    for keyword, rank in JB_RANK:
        if keyword in jb:
            return rank
    return 99


def _fmt_dt(v) -> str:
    if v is None:
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d %H:%M")
    return str(v).replace("T", " ")[:16]


def _fmt_date(v) -> str:
    if v is None:
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    return str(v)[:10]


def _safe_int(v, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _has_attendance_time(row: dict) -> bool:
    for i in range(1, 11):
        if (row.get(f"time_{i}") or "").strip():
            return True
    return False


def _attendance_times(row: dict) -> list[str]:
    times = []
    for i in range(1, 11):
        val = row.get(f"time_{i}")
        if val:
            times.append(str(val).strip())
    return times


def _dept_sort_key(dept_name: str) -> int:
    try:
        return DEPT_ORDER.index(dept_name)
    except ValueError:
        return len(DEPT_ORDER)


def _get_dakaman() -> str:
    try:
        rows = db.execute_query("SELECT dakaman FROM webconfig WHERE id = %s LIMIT 1", ("1",))
        return (rows[0].get("dakaman") or "").strip() if rows else ""
    except Exception:
        return ""


def _can_view_all_departments(viewer: str, user: Optional[dict]) -> bool:
    if not viewer:
        return False
    try:
        from routers.approvers import is_admin2_user
        if is_admin2_user(viewer):
            return True
    except Exception:
        pass
    admin1 = (_get_admin1() or "").strip()
    dakaman = _get_dakaman()
    if (admin1 and viewer == admin1) or (dakaman and viewer == dakaman):
        return True
    if not user:
        return False
    jb = (user.get("jb") or "").strip()
    return (
        _jb_match(jb, "经理")
        or _jb_match(jb, "部长")
        or _jb_match(jb, "副部长")
        or is_zonghe_tech_director(user)
    )


def _load_departments(can_view_all: bool, own_dept: str) -> list[str]:
    if not can_view_all:
        return [own_dept] if own_dept else []
    rows = db.execute_query(
        """
        SELECT DISTINCT TRIM(lsys) AS dept
        FROM yggl
        WHERE COALESCE(zaizhi, 0) = 0
          AND lsys IS NOT NULL
          AND TRIM(lsys) NOT IN ('', '其他部门员工', '其他部门成员')
          AND RIGHT(TRIM(name), 1) != '1'
          AND RIGHT(TRIM(lsys), 1) != '1'
        """,
        (),
    ) or []
    depts = [(r.get("dept") or "").strip() for r in rows if (r.get("dept") or "").strip()]
    return ["全员"] + sorted(set(depts), key=_dept_sort_key)


@router.get("/scene")
def get_personnel_scene(
    current_user: str = Query(..., description="当前登录用户姓名"),
    department: Optional[str] = Query(None, description="要查看的科室；无全员权限时只能查看本科室"),
    target_date: Optional[str] = Query(None, description="日期 YYYY-MM-DD，默认今天"),
):
    """返回指定科室在某一天的人员出勤/公出状态，用于前端办公室可视化。"""
    viewer = (current_user or "").strip()
    if not viewer:
        raise HTTPException(status_code=400, detail="当前用户不能为空")

    try:
        user = _get_user_info(viewer)
        if not user:
            raise HTTPException(status_code=403, detail="用户信息不存在")

        own_dept = (user.get("lsys") or "").strip()
        can_view_all = _can_view_all_departments(viewer, user)
        available_departments = _load_departments(can_view_all, own_dept)

        requested_dept = (department or "").strip()
        selected_all = requested_dept in ("全员", "__all__", "all")
        selected_dept = "全员" if selected_all else (requested_dept or own_dept)
        if not selected_dept:
            return {
                "success": True,
                "department": "",
                "date": target_date or date.today().strftime("%Y-%m-%d"),
                "canViewAll": can_view_all,
                "availableDepartments": available_departments,
                "people": [],
                "summary": {"total": 0, "present": 0, "businessTrip": 0, "leave": 0, "leavePending": 0, "noRecord": 0},
                "generatedAt": attendance_db.get_latest_successful_upload_time() or "",
            }
        if selected_all and not can_view_all:
            raise HTTPException(status_code=403, detail="无权限查看全员")
        if selected_dept != own_dept and not selected_all and not can_view_all:
            raise HTTPException(status_code=403, detail="无权限查看其他科室")

        day = (target_date or date.today().strftime("%Y-%m-%d")).strip()
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")

        if selected_all:
            people_rows = db.execute_query(
                """
                SELECT name, gh, lsys, jb, xbie, enterprise_email
                FROM yggl
                WHERE COALESCE(zaizhi, 0) = 0
                  AND lsys IS NOT NULL
                  AND TRIM(lsys) NOT IN ('', '其他部门员工', '其他部门成员')
                  AND name IS NOT NULL
                  AND TRIM(name) <> ''
                  AND RIGHT(TRIM(name), 1) != '1'
                  AND RIGHT(TRIM(lsys), 1) != '1'
                ORDER BY lsys, gh
                """,
                (),
            ) or []
        else:
            people_rows = db.execute_query(
                """
                SELECT name, gh, lsys, jb, xbie, enterprise_email
                FROM yggl
                WHERE COALESCE(zaizhi, 0) = 0
                  AND lsys = %s
                  AND name IS NOT NULL
                  AND TRIM(name) <> ''
                  AND RIGHT(TRIM(name), 1) != '1'
                ORDER BY gh
                """,
                (selected_dept,),
            ) or []

        people = []
        names = []
        for row in people_rows:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            names.append(name)
            people.append(
                {
                    "name": name,
                    "gh": (row.get("gh") or "").strip(),
                    "department": (row.get("lsys") or "").strip(),
                    "jb": (row.get("jb") or "").strip(),
                    "xbie": (row.get("xbie") or "").strip(),
                    "gender": "female" if "女" in ((row.get("xbie") or "").strip()) else "male",
                    "email": (row.get("enterprise_email") or "").strip(),
                }
            )

        people.sort(key=lambda p: (_dept_sort_key(p.get("department") or ""), _jb_sort_key(p.get("jb") or ""), p.get("gh") or "", p.get("name") or ""))

        attendance_by_name = {}
        trips_by_name = {}
        leaves_by_name = {}
        if names:
            placeholders = ",".join(["%s"] * len(names))
            att_rows = db.execute_query(
                f"""
                SELECT *
                FROM attendance_records
                WHERE attendance_date = %s
                  AND employee_name IN ({placeholders})
                """,
                tuple([day] + names),
            ) or []
            for row in att_rows:
                nm = (row.get("employee_name") or "").strip()
                if nm and _has_attendance_time(row):
                    times = _attendance_times(row)
                    attendance_by_name[nm] = {
                        "date": _fmt_date(row.get("attendance_date")),
                        "firstTime": times[0] if times else "",
                        "lastTime": times[-1] if times else "",
                        "times": times,
                    }

            trip_rows = db.execute_query(
                f"""
                SELECT id, gcr, gclx, gcdd, yjcfsj, yjfhsj, gcsj, sjfhtime, xmmc, gcrw
                FROM gcsqb
                WHERE gcr IN ({placeholders})
                  AND COALESCE(bldzt, 0) = 2
                  AND COALESCE(szrzt, 0) = 2
                  AND DATE(COALESCE(gcsj, yjcfsj, wpsj, yjfhsj)) <= %s
                  AND DATE(COALESCE(sjfhtime, yjfhsj, gcsj, yjcfsj, wpsj)) >= %s
                ORDER BY COALESCE(gcsj, yjcfsj, wpsj, yjfhsj) DESC
                """,
                tuple(names + [day, day]),
            ) or []
            for row in trip_rows:
                nm = (row.get("gcr") or "").strip()
                if nm and nm not in trips_by_name:
                    trips_by_name[nm] = {
                        "id": row.get("id"),
                        "type": (row.get("gclx") or "").strip() or "公出",
                        "location": (row.get("gcdd") or "").strip(),
                        "project": (row.get("xmmc") or "").strip(),
                        "task": (row.get("gcrw") or "").strip(),
                        "startTime": _fmt_dt(row.get("gcsj") or row.get("yjcfsj")),
                        "endTime": _fmt_dt(row.get("sjfhtime") or row.get("yjfhsj")),
                    }

            day_start = f"{day} 00:00:00"
            day_end = f"{day} 23:59:59"
            leave_rows = db.execute_query(
                f"""
                SELECT id, xm, qjfs, timefrom, timeto, qjzt, tian, xiaoshi
                FROM qj
                WHERE xm IN ({placeholders})
                  AND qjzt IN (0, 1, 3, 4)
                  AND timefrom <= %s
                  AND timeto >= %s
                ORDER BY
                  CASE WHEN qjzt = 4 THEN 0 ELSE 1 END,
                  timefrom DESC
                """,
                tuple(names + [day_end, day_start]),
            ) or []
            for row in leave_rows:
                nm = (row.get("xm") or "").strip()
                if not nm or nm in leaves_by_name:
                    continue
                qjzt = _safe_int(row.get("qjzt"))
                approved = qjzt == 4
                leaves_by_name[nm] = {
                    "id": row.get("id"),
                    "type": (row.get("qjfs") or "").strip() or "请假",
                    "status": qjzt,
                    "statusLabel": "请假" if approved else "请假审核中",
                    "approved": approved,
                    "startTime": _fmt_dt(row.get("timefrom")),
                    "endTime": _fmt_dt(row.get("timeto")),
                    "days": str(row.get("tian") or "").strip(),
                    "hours": str(row.get("xiaoshi") or "").strip(),
                }

        result_people = []
        summary = {"total": len(people), "present": 0, "businessTrip": 0, "leave": 0, "leavePending": 0, "noRecord": 0}
        for person in people:
            name = person["name"]
            trip = trips_by_name.get(name)
            attendance = attendance_by_name.get(name)
            leave = leaves_by_name.get(name)
            if trip:
                status = "business_trip"
                status_label = "公出中"
                summary["businessTrip"] += 1
            elif leave and leave.get("approved") and not attendance:
                status = "leave"
                status_label = "请假"
                summary["leave"] += 1
            elif attendance:
                status = "present"
                status_label = "在岗"
                summary["present"] += 1
            else:
                status = "no_record"
                status_label = "请假审核中" if leave else "暂无打卡"
                if leave:
                    summary["leavePending"] += 1
                summary["noRecord"] += 1
            result_people.append(
                {
                    **person,
                    "status": status,
                    "statusLabel": status_label,
                    "attendance": attendance,
                    "businessTrip": trip,
                    "leave": leave,
                }
            )

        return {
            "success": True,
            "department": selected_dept,
            "date": day,
            "canViewAll": can_view_all,
            "availableDepartments": available_departments,
            "people": result_people,
            "summary": summary,
            "generatedAt": attendance_db.get_latest_successful_upload_time() or "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("人员出勤可视化加载失败: %s", e)
        raise HTTPException(status_code=500, detail=f"加载失败: {str(e)}")
