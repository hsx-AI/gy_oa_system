# -*- coding: utf-8 -*-
"""月度绩效录入、排名与统计。"""
from datetime import date
from typing import List, Optional
import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database import db, db_demo
from routers.approvers import _get_user_info, _jb_match, can_access_leader_dashboard, is_admin1_user, is_admin2_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/performance", tags=["月度绩效"])

MARKERS = {"", "总师", "新入职"}
GRADE_RATIOS = (("A", 0.2), ("B+", 0.3), ("B", 0.4), ("C", 0.1))


class PerformanceEntry(BaseModel):
    employee_name: str
    score: Optional[float] = Field(None, ge=0, le=10000)
    marker: Optional[str] = None
    job_level: Optional[str] = None


class PerformanceSaveRequest(BaseModel):
    current_user: str
    month: str
    department: Optional[str] = None
    entries: List[PerformanceEntry]


def _month(value: str) -> date:
    try:
        parts = (value or "").strip().split("-")
        return date(int(parts[0]), int(parts[1]), 1)
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail="月份格式应为 YYYY-MM")


def _editable_scope(name: str):
    """返回可录入科室；班组长、主任、副主任及系统管理员可录入。"""
    name = (name or "").strip()
    if is_admin1_user(name) or is_admin2_user(name):
        return "all", ""
    user = _get_user_info(name)
    if not user:
        return None, ""
    job = (user.get("jb") or "").strip()
    dept = (user.get("lsys") or "").strip()
    if any(_jb_match(job, role) for role in ("组长", "主任", "副主任")):
        return "department", dept
    return None, dept


def _view_scope(name: str):
    editable, dept = _editable_scope(name)
    if can_access_leader_dashboard(name):
        return "all", dept, bool(editable)
    if editable:
        return "department", dept, True
    return "self", dept, False


def _assert_department(name: str, requested: Optional[str], writing: bool = False) -> str:
    scope, user_dept = _editable_scope(name) if writing else _view_scope(name)[:2]
    if scope is None:
        raise HTTPException(status_code=403, detail="仅班组长、主任或副主任可录入绩效")
    department = (requested or user_dept or "").strip()
    if not department:
        raise HTTPException(status_code=422, detail="未找到所属科室")
    if scope != "all" and department != user_dept:
        raise HTTPException(status_code=403, detail="只能操作本人所属科室的绩效")
    return department


def _job_levels(names: List[str]) -> dict:
    if not names:
        return {}
    placeholders = ",".join(["%s"] * len(names))
    try:
        rows = db_demo.execute_query(
            f"SELECT name, job_level FROM employee_info WHERE name IN ({placeholders})",
            tuple(names),
        )
        return {str(r.get("name") or "").strip(): (r.get("job_level") or "") for r in rows}
    except Exception as exc:
        logger.warning("获取 employee_info.job_level 失败: %s", exc)
        return {}


def _recalculate_ranks(month: date, department: str) -> None:
    """按科室有效得分降序排名；标记人员、空分数均不参加排名。"""
    rows = db.execute_query(
        """
        SELECT id FROM performance_records
        WHERE performance_month=%s AND department=%s
          AND score IS NOT NULL AND COALESCE(marker, '') = ''
        ORDER BY score DESC, employee_name ASC
        """,
        (month, department),
    )
    db.execute_update(
        "UPDATE performance_records SET rank_no=NULL, rank_percent=NULL, performance_grade=NULL WHERE performance_month=%s AND department=%s",
        (month, department),
    )
    total = len(rows)
    if total:
        raw = [(grade, total * ratio) for grade, ratio in GRADE_RATIOS]
        counts = {grade: int(value) for grade, value in raw}
        order = {grade: index for index, (grade, _) in enumerate(GRADE_RATIOS)}
        # 最大余数法处理人数不能被比例整除的情况，确保参与排名人员都有等级。
        for grade, _ in sorted(raw, key=lambda item: (item[1] - int(item[1]), -order[item[0]]), reverse=True)[:total - sum(counts.values())]:
            counts[grade] += 1
        grades = [grade for grade, _ in GRADE_RATIOS for _ in range(counts[grade])]
        updates = [(idx, round(idx / total, 6), grades[idx - 1], row["id"]) for idx, row in enumerate(rows, start=1)]
        db.execute_many("UPDATE performance_records SET rank_no=%s, rank_percent=%s, performance_grade=%s WHERE id=%s", updates)


@router.get("/permission")
async def permission(current_user: str = Query(...)):
    scope, department, can_edit = _view_scope(current_user)
    return {"success": True, "scope": scope, "department": department, "can_edit": can_edit}


@router.get("/roster")
async def roster(
    current_user: str = Query(...), month: str = Query(...), department: Optional[str] = Query(None)
):
    perf_month = _month(month)
    dept = _assert_department(current_user, department, writing=True)
    people = db.execute_query(
        """
        SELECT TRIM(name) AS employee_name, TRIM(lsys) AS department
        FROM yggl
        WHERE TRIM(lsys)=%s AND name IS NOT NULL AND TRIM(name) != ''
          AND RIGHT(TRIM(name), 1) != '1' AND COALESCE(zaizhi, 0)=0
        ORDER BY name
        """,
        (dept,),
    )
    names = [p["employee_name"] for p in people]
    levels = _job_levels(names)
    existing = db.execute_query(
        """SELECT employee_name, score, marker, job_level, rank_no, rank_percent, performance_grade
           FROM performance_records WHERE performance_month=%s AND department=%s""",
        (perf_month, dept),
    )
    record_map = {r["employee_name"]: r for r in existing}
    return {
        "success": True,
        "department": dept,
        "list": [
            {
                "employee_name": n,
                "department": dept,
                "job_level": levels.get(n) or record_map.get(n, {}).get("job_level") or "",
                "score": record_map.get(n, {}).get("score"),
                "marker": record_map.get(n, {}).get("marker") or "",
                "rank_no": record_map.get(n, {}).get("rank_no"),
                "rank_percent": record_map.get(n, {}).get("rank_percent"),
                "performance_grade": record_map.get(n, {}).get("performance_grade"),
            }
            for n in names
        ],
    }


@router.post("/save")
async def save(request: PerformanceSaveRequest):
    perf_month = _month(request.month)
    dept = _assert_department(request.current_user, request.department, writing=True)
    allowed = db.execute_query(
        """SELECT TRIM(name) AS name FROM yggl WHERE TRIM(lsys)=%s AND name IS NOT NULL
           AND TRIM(name) != '' AND RIGHT(TRIM(name), 1) != '1' AND COALESCE(zaizhi, 0)=0""",
        (dept,),
    )
    allowed_names = {r["name"] for r in allowed}
    if not request.entries:
        raise HTTPException(status_code=422, detail="没有可保存的绩效数据")
    levels = _job_levels(list(allowed_names))
    values = []
    for entry in request.entries:
        employee_name = entry.employee_name.strip()
        if employee_name not in allowed_names:
            raise HTTPException(status_code=422, detail=f"{employee_name} 不属于 {dept}")
        marker = (entry.marker or "").strip()
        if marker not in MARKERS:
            raise HTTPException(status_code=422, detail="标记仅可为“总师”或“新入职”")
        values.append((
            perf_month, dept, employee_name, levels.get(employee_name) or entry.job_level or "",
            entry.score, marker or None, request.current_user.strip(),
        ))
    result = db.execute_many(
        """
        INSERT INTO performance_records
          (performance_month, department, employee_name, job_level, score, marker, created_by)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE department=VALUES(department), job_level=VALUES(job_level),
          score=VALUES(score), marker=VALUES(marker), created_by=VALUES(created_by)
        """,
        values,
    )
    if result < 0:
        raise HTTPException(status_code=500, detail="绩效保存失败")
    _recalculate_ranks(perf_month, dept)
    return {"success": True, "message": "绩效已保存并重新计算排名", "count": len(values)}


@router.get("/records")
async def records(
    current_user: str = Query(...), month: str = Query(...), department: Optional[str] = Query(None)
):
    perf_month = _month(month)
    dept = _assert_department(current_user, department, writing=False)
    rows = db.execute_query(
        """SELECT department, employee_name, job_level, score, marker, rank_no, rank_percent, performance_grade
           FROM performance_records WHERE performance_month=%s AND department=%s
           ORDER BY rank_no IS NULL, rank_no, employee_name""",
        (perf_month, dept),
    )
    return {"success": True, "department": dept, "list": rows}


@router.get("/history")
async def history(
    current_user: str = Query(...), year: Optional[int] = Query(None, ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12), department: Optional[str] = Query(None),
    employee_name: Optional[str] = Query(None),
):
    scope, user_dept, _ = _view_scope(current_user)
    if scope == "self":
        raise HTTPException(status_code=403, detail="暂无查看科室绩效统计的权限")
    dept = (department or user_dept or "").strip()
    if scope != "all":
        dept = user_dept
    clauses, params = ["1=1"], []
    if year:
        clauses.append("YEAR(performance_month)=%s"); params.append(year)
    if month:
        clauses.append("MONTH(performance_month)=%s"); params.append(month)
    if dept:
        clauses.append("department=%s"); params.append(dept)
    if employee_name and employee_name.strip():
        clauses.append("employee_name=%s"); params.append(employee_name.strip())
    rows = db.execute_query(
        """SELECT DATE_FORMAT(performance_month, '%%Y-%%m') AS month, department, employee_name,
                  job_level, score, marker, rank_no, rank_percent, performance_grade
           FROM performance_records WHERE """ + " AND ".join(clauses) +
        " ORDER BY performance_month DESC, department, rank_no IS NULL, rank_no, employee_name",
        tuple(params),
    )
    return {"success": True, "scope": scope, "department": dept, "list": rows}


@router.get("/departments")
async def departments(current_user: str = Query(...)):
    scope, user_dept, _ = _view_scope(current_user)
    if scope != "all":
        return {"success": True, "list": [user_dept] if user_dept else []}
    rows = db.execute_query(
        """SELECT name FROM (
             SELECT DISTINCT TRIM(lsys) AS name FROM yggl WHERE lsys IS NOT NULL AND TRIM(lsys) != ''
             UNION
             SELECT DISTINCT department AS name FROM performance_records WHERE department IS NOT NULL AND TRIM(department) != ''
           ) departments ORDER BY name"""
    )
    return {"success": True, "list": [r["name"] for r in rows]}
