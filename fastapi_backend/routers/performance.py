# -*- coding: utf-8 -*-
"""月度、季度绩效录入、排名与统计。"""
from datetime import date
from typing import List, Optional
import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database import db, db_demo
from routers.approvers import _get_user_info, _jb_match, can_access_leader_dashboard, is_admin1_user, is_admin2_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/performance", tags=["绩效统计"])

MARKERS = {"", "总师", "新入职"}
GRADE_RATIOS = (("A", 0.2), ("B+", 0.3), ("B", 0.4), ("C", 0.1))


class PerformanceEntry(BaseModel):
    employee_name: str
    score: Optional[float] = Field(None, ge=0, le=10000)
    marker: Optional[str] = None
    job_level: Optional[str] = None
    performance_grade: Optional[str] = None
    grade_manual: bool = False


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
    db.execute_update("UPDATE performance_records SET rank_no=NULL, rank_percent=NULL WHERE performance_month=%s AND department=%s", (month, department))
    db.execute_update("UPDATE performance_records SET performance_grade=NULL WHERE performance_month=%s AND department=%s AND COALESCE(grade_manual, 0)=0", (month, department))
    total = len(rows)
    if total:
        raw = [(grade, total * ratio) for grade, ratio in GRADE_RATIOS]
        counts = {grade: int(value) for grade, value in raw}
        order = {grade: index for index, (grade, _) in enumerate(GRADE_RATIOS)}
        # 最大余数法处理人数不能被比例整除的情况，确保参与排名人员都有等级。
        for grade, _ in sorted(raw, key=lambda item: (item[1] - int(item[1]), -order[item[0]]), reverse=True)[:total - sum(counts.values())]:
            counts[grade] += 1
        grades = [grade for grade, _ in GRADE_RATIOS for _ in range(counts[grade])]
        rank_updates = [(idx, round(idx / total, 6), row["id"]) for idx, row in enumerate(rows, start=1)]
        grade_updates = [(grades[idx - 1], row["id"]) for idx, row in enumerate(rows, start=1)]
        db.execute_many("UPDATE performance_records SET rank_no=%s, rank_percent=%s WHERE id=%s", rank_updates)
        db.execute_many("UPDATE performance_records SET performance_grade=%s WHERE id=%s AND COALESCE(grade_manual, 0)=0", grade_updates)


@router.get("/permission")
def permission(current_user: str = Query(...)):
    scope, department, can_edit = _view_scope(current_user)
    user = _get_user_info((current_user or "").strip()) or {}
    job = (user.get("jb") or "").strip()
    can_quarterly = _jb_match(job, "主任") or _jb_match(job, "副主任")
    return {"success": True, "scope": scope, "department": department, "can_edit": can_edit, "can_quarterly": can_quarterly}


@router.get("/roster")
def roster(
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
        """SELECT employee_name, score, marker, job_level, rank_no, rank_percent, performance_grade, grade_manual
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
                "grade_manual": bool(record_map.get(n, {}).get("grade_manual")),
            }
            for n in names
        ],
    }


@router.post("/save")
def save(request: PerformanceSaveRequest):
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
        grade = (entry.performance_grade or "").strip()
        if grade not in {"", "A", "B+", "B", "C"}:
            raise HTTPException(status_code=422, detail="绩效等级仅可为 A、B+、B、C")
        values.append((
            perf_month, dept, employee_name, levels.get(employee_name) or entry.job_level or "",
            entry.score, marker or None, grade or None, 1 if entry.grade_manual and grade else 0, request.current_user.strip(),
        ))
    result = db.execute_many(
        """
        INSERT INTO performance_records
          (performance_month, department, employee_name, job_level, score, marker, performance_grade, grade_manual, created_by)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE department=VALUES(department), job_level=VALUES(job_level),
          score=VALUES(score), marker=VALUES(marker), performance_grade=VALUES(performance_grade),
          grade_manual=VALUES(grade_manual), created_by=VALUES(created_by)
        """,
        values,
    )
    if result < 0:
        raise HTTPException(status_code=500, detail="绩效保存失败")
    _recalculate_ranks(perf_month, dept)
    return {"success": True, "message": "绩效已保存并重新计算排名", "count": len(values)}


@router.get("/records")
def records(
    current_user: str = Query(...), month: str = Query(...), department: Optional[str] = Query(None)
):
    perf_month = _month(month)
    dept = _assert_department(current_user, department, writing=False)
    rows = db.execute_query(
        """SELECT department, employee_name, job_level, score, marker, rank_no, rank_percent, performance_grade, grade_manual
           FROM performance_records WHERE performance_month=%s AND department=%s
           ORDER BY rank_no IS NULL, rank_no, employee_name""",
        (perf_month, dept),
    )
    return {"success": True, "department": dept, "list": rows}


@router.get("/history")
def history(
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
                  job_level, score, marker, rank_no, rank_percent, performance_grade, grade_manual
           FROM performance_records WHERE """ + " AND ".join(clauses) +
        " ORDER BY performance_month DESC, department, rank_no IS NULL, rank_no, employee_name",
        tuple(params),
    )
    return {"success": True, "scope": scope, "department": dept, "list": rows}


@router.get("/departments")
def departments(current_user: str = Query(...)):
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


# ==================== 季度绩效 ====================
class QuarterlyPerformanceEntry(BaseModel):
    employee_name: str
    work_performance_score: Optional[float] = Field(None, ge=0, le=70)
    ability_score: Optional[float] = Field(None, ge=0, le=20)
    behavior_score: Optional[float] = Field(None, ge=0, le=10)
    adjustment_score: Optional[float] = Field(0, ge=-10000, le=10000)
    assessment_grade: Optional[str] = None
    grade_manual: bool = False
    remark: Optional[str] = None


class QuarterlyPerformanceSaveRequest(BaseModel):
    current_user: str
    quarter: str
    department: Optional[str] = None
    entries: List[QuarterlyPerformanceEntry]


def _quarter_start(value: str) -> date:
    try:
        year_text, quarter_text = (value or "").strip().upper().split("-Q")
        year, quarter = int(year_text), int(quarter_text)
        if quarter not in (1, 2, 3, 4):
            raise ValueError
        return date(year, (quarter - 1) * 3 + 1, 1)
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail="季度格式应为 YYYY-Q1 至 YYYY-Q4")


def _quarterly_department(name: str) -> str:
    user = _get_user_info((name or "").strip())
    if not user:
        raise HTTPException(status_code=403, detail="仅主任、副主任可录入季度绩效")
    job, department = (user.get("jb") or "").strip(), (user.get("lsys") or "").strip()
    if not (_jb_match(job, "主任") or _jb_match(job, "副主任")):
        raise HTTPException(status_code=403, detail="仅主任、副主任可录入季度绩效")
    if not department:
        raise HTTPException(status_code=422, detail="未找到所属科室")
    return department


def _quarter_monthly_totals(start: date, department: str) -> dict:
    end_month = start.month + 2
    rows = db.execute_query(
        """SELECT employee_name, COALESCE(SUM(score), 0) AS monthly_total
           FROM performance_records WHERE department=%s AND performance_month >= %s
             AND performance_month < DATE_ADD(%s, INTERVAL 3 MONTH) AND score IS NOT NULL
           GROUP BY employee_name""",
        (department, start, start),
    )
    return {r["employee_name"]: float(r.get("monthly_total") or 0) for r in rows}


def _recalculate_quarterly(start: date, department: str) -> None:
    """季度排序以月绩效总计为准，考核等级以季度总分为准。"""
    rows = db.execute_query(
        """SELECT id, total_score FROM quarterly_performance_records
           WHERE quarter_start=%s AND department=%s ORDER BY monthly_total DESC, employee_name""",
        (start, department),
    )
    db.execute_update("UPDATE quarterly_performance_records SET rank_no=NULL, rank_percent=NULL WHERE quarter_start=%s AND department=%s", (start, department))
    db.execute_update("UPDATE quarterly_performance_records SET assessment_grade=NULL WHERE quarter_start=%s AND department=%s AND COALESCE(grade_manual,0)=0", (start, department))
    total = len(rows)
    if not total:
        return
    db.execute_many(
        "UPDATE quarterly_performance_records SET rank_no=%s, rank_percent=%s WHERE id=%s",
        [(index, round(index / total, 6), row["id"]) for index, row in enumerate(rows, start=1)],
    )
    grade_rows = sorted([row for row in rows if row.get("total_score") is not None], key=lambda row: (float(row["total_score"]), row["id"]), reverse=True)
    grade_total = len(grade_rows)
    if not grade_total:
        return
    raw = [(grade, grade_total * ratio) for grade, ratio in GRADE_RATIOS]
    counts = {grade: int(value) for grade, value in raw}
    order = {grade: index for index, (grade, _) in enumerate(GRADE_RATIOS)}
    for grade, _ in sorted(raw, key=lambda item: (item[1] - int(item[1]), -order[item[0]]), reverse=True)[:grade_total - sum(counts.values())]:
        counts[grade] += 1
    grades = [grade for grade, _ in GRADE_RATIOS for _ in range(counts[grade])]
    db.execute_many(
        "UPDATE quarterly_performance_records SET assessment_grade=%s WHERE id=%s AND COALESCE(grade_manual,0)=0",
        [(grades[index], row["id"]) for index, row in enumerate(grade_rows)],
    )


@router.get("/quarterly/roster")
def quarterly_roster(current_user: str = Query(...), quarter: str = Query(...)):
    start, department = _quarter_start(quarter), _quarterly_department(current_user)
    people = db.execute_query(
        """SELECT TRIM(name) AS employee_name FROM yggl WHERE TRIM(lsys)=%s
           AND name IS NOT NULL AND TRIM(name) != '' AND RIGHT(TRIM(name),1) != '1' AND COALESCE(zaizhi,0)=0""",
        (department,),
    )
    names = [row["employee_name"] for row in people]
    totals, levels = _quarter_monthly_totals(start, department), _job_levels(names)
    existing = db.execute_query("SELECT * FROM quarterly_performance_records WHERE quarter_start=%s AND department=%s", (start, department))
    record_map = {row["employee_name"]: row for row in existing}
    result = []
    for name in names:
        old, monthly_total = record_map.get(name, {}), totals.get(name, 0)
        result.append({
            "employee_name": name, "department": department, "job_level": levels.get(name) or old.get("job_level") or "",
            "monthly_total": monthly_total, "work_performance_score": old.get("work_performance_score"),
            "ability_score": old.get("ability_score"), "behavior_score": old.get("behavior_score"),
            "adjustment_score": old.get("adjustment_score", 0), "total_score": old.get("total_score"),
            "rank_no": old.get("rank_no"), "rank_percent": old.get("rank_percent"),
            "assessment_grade": old.get("assessment_grade"), "grade_manual": bool(old.get("grade_manual")), "remark": old.get("remark") or "",
        })
    result.sort(key=lambda row: (-float(row["monthly_total"] or 0), row["employee_name"]))
    return {"success": True, "quarter_start": start, "department": department, "list": result}


@router.post("/quarterly/save")
def save_quarterly(request: QuarterlyPerformanceSaveRequest):
    start, department = _quarter_start(request.quarter), _quarterly_department(request.current_user)
    allowed_rows = db.execute_query("SELECT TRIM(name) AS name FROM yggl WHERE TRIM(lsys)=%s AND name IS NOT NULL AND TRIM(name) != '' AND RIGHT(TRIM(name),1) != '1' AND COALESCE(zaizhi,0)=0", (department,))
    allowed = {row["name"] for row in allowed_rows}
    if not request.entries:
        raise HTTPException(status_code=422, detail="没有可保存的季度绩效数据")
    totals, levels, values = _quarter_monthly_totals(start, department), _job_levels(list(allowed)), []
    for entry in request.entries:
        name = entry.employee_name.strip()
        if name not in allowed:
            raise HTTPException(status_code=422, detail=f"{name} 不属于 {department}")
        grade = (entry.assessment_grade or "").strip()
        if grade not in {"", "A", "B+", "B", "C"}:
            raise HTTPException(status_code=422, detail="考核等级仅可为 A、B+、B、C")
        monthly_total = totals.get(name, 0)
        work, ability, behavior = entry.work_performance_score, entry.ability_score, entry.behavior_score
        adjustment = float(entry.adjustment_score or 0)
        has_score = any(value is not None for value in (work, ability, behavior)) or adjustment != 0
        total_score = (float(work or 0) + float(ability or 0) + float(behavior or 0) + adjustment) if has_score else None
        if total_score is not None and not 0 <= total_score <= 100:
            raise HTTPException(status_code=422, detail=f"{name} 的总分必须在 0 至 100 分之间")
        values.append((start, department, name, levels.get(name) or "", monthly_total, work, ability, behavior, adjustment, total_score, grade or None, 1 if entry.grade_manual and grade else 0, (entry.remark or "").strip() or None, request.current_user.strip()))
    sql = """
      INSERT INTO quarterly_performance_records
       (quarter_start,department,employee_name,job_level,monthly_total,work_performance_score,ability_score,behavior_score,adjustment_score,total_score,assessment_grade,grade_manual,remark,created_by)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
      ON DUPLICATE KEY UPDATE job_level=VALUES(job_level), monthly_total=VALUES(monthly_total), work_performance_score=VALUES(work_performance_score), ability_score=VALUES(ability_score), behavior_score=VALUES(behavior_score), adjustment_score=VALUES(adjustment_score), total_score=VALUES(total_score), assessment_grade=VALUES(assessment_grade), grade_manual=VALUES(grade_manual), remark=VALUES(remark), created_by=VALUES(created_by)
    """
    if db.execute_many(sql, values) < 0:
        raise HTTPException(status_code=500, detail="季度绩效保存失败")
    _recalculate_quarterly(start, department)
    return {"success": True, "message": "季度绩效已保存并重新计算排序及考核等级", "count": len(values)}
