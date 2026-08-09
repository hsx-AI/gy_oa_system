# -*- coding: utf-8 -*-
"""
审批人规则 API - 基于 yggl 表的 jb(级别) 和 lsys(隶属于室)
审批规则:
  1. jb(员工) -> lsys(同隶属于室) jb(组长/主任)
  2. jb(组长) -> lsys(同隶属于室) jb(主任)
  3. jb(责任工艺师) -> lsys(同隶属于室) jb(主任)
  4. jb(主任/副主任) -> jb(部长/副部长) + 同室 jb(主任/副主任)，同室列表排除本人（支持同级审批）
  5. jb(部长/经理) -> jb(部长/副部长)（含副经理/经理助理），排除本人（支持交由副职审批）
  6. lsys(部办) 其他人员 -> jb(部长)
  7. 二级审批 -> jb(部长/副部长)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from database import db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvers", tags=["审批人"])


_ROLE_MAP = {
    "部长": {"部长", "经理"},
    "副部长": {"副部长", "副经理", "经理助理"},
    "主任": {"主任"},
    "副主任": {"副主任"},
    "组长": {"组长", "班组长"},
}


def _jb_match(jb_val: str, target: str) -> bool:
    """
    匹配级别，支持新旧职务名称映射。
    target 为权限级别关键字（部长/副部长/主任/副主任/组长/员工/责任工艺师）。
    jb_val 为数据库实际 jb 值，支持 "组长1" 等变体（startsWith）。
    """
    if not jb_val:
        return False
    j = (jb_val or "").strip()
    if target == "员工":
        return j == "员工" or j.startswith("员工")
    if target == "责任工艺师":
        return "责任工艺师" in j or j == "责任工艺师"
    titles = _ROLE_MAP.get(target)
    if titles:
        for t in titles:
            if j == t or j.startswith(t):
                return True
        if target == "副主任" and "副主任" in j:
            return True
        return False
    return j == target


def _jb_sql_conditions(target: str):
    """
    返回 SQL WHERE 片段和对应参数，用于按角色查询 yggl.jb。
    例如 _jb_sql_conditions("部长") 返回 ("(jb=%s OR jb LIKE %s OR jb=%s OR jb LIKE %s)", ("部长","部长%","经理","经理%"))
    """
    titles = _ROLE_MAP.get(target)
    if not titles:
        return "(jb = %s OR jb LIKE %s)", (target, f"{target}%")
    parts = []
    params = []
    for t in sorted(titles):
        parts.append("jb = %s OR jb LIKE %s")
        params.extend([t, f"{t}%"])
    return "(" + " OR ".join(parts) + ")", tuple(params)


def _get_user_info(name: str) -> Optional[dict]:
    """从 yggl 获取用户 jb 和 lsys"""
    rows = db.execute_query("SELECT jb, lsys FROM yggl WHERE name = %s LIMIT 1", (name,))
    if not rows:
        return None
    return rows[0]


def is_zonghe_tech_director(user: Optional[Dict[str, Any]]) -> bool:
    """
    综合技术室 且 主任/副主任：可查看全员请假、加班、公出记录（与部长同级数据范围，排除部办及离职等规则与统计一致）。
    """
    if not user:
        return False
    if (user.get("lsys") or "").strip() != "综合技术室":
        return False
    jb = (user.get("jb") or "").strip()
    return _jb_match(jb, "主任") or _jb_match(jb, "副主任")


def is_admin1_user(name: Optional[str]) -> bool:
    n = (name or "").strip()
    if not n:
        return False
    try:
        from routers.db_manager import _get_admin1
        a1 = (_get_admin1() or "").strip()
        return bool(a1 and n == a1)
    except Exception:
        return False


def is_admin2_user(name: Optional[str]) -> bool:
    """webconfig.admin2 人事管理员"""
    n = (name or "").strip()
    if not n:
        return False
    try:
        from routers.admin import _get_admin2
        a2 = (_get_admin2() or "").strip()
        return bool(a2 and n == a2)
    except Exception:
        return False


def has_leader_dashboard_all_dept_scope(name: Optional[str]) -> bool:
    """
    管理驾驶舱可选「全员」、任意科室的数据范围：
    部长/副部长、综合技术室主任/副主任、admin1、admin2。
    """
    n = (name or "").strip()
    if not n:
        return False
    if is_admin1_user(n) or is_admin2_user(n):
        return True
    user = _get_user_info(n)
    if not user:
        return False
    jb = (user.get("jb") or "").strip()
    if _jb_match(jb, "部长") or _jb_match(jb, "副部长"):
        return True
    return is_zonghe_tech_director(user)


def has_work_intensity_all_scope(name: Optional[str], user: Optional[Dict[str, Any]] = None) -> bool:
    """工作强度全员/任意科室：综合技术室主任/副主任、admin1、admin2。"""
    n = (name or "").strip()
    if not n:
        return False
    if is_admin1_user(n) or is_admin2_user(n):
        return True
    u = user if user is not None else _get_user_info(n)
    return is_zonghe_tech_director(u)


def can_access_leader_dashboard(name: Optional[str]) -> bool:
    """
    管理驾驶舱 / 考勤纪律审查：部长/副部长、综合技术室主任/副主任、
    系统管理员 admin1、人事管理员 admin2（与综合技术室主任同级数据范围）。
    """
    n = (name or "").strip()
    if not n:
        return False
    try:
        from routers.db_manager import _get_admin1
        from routers.admin import _get_admin2

        a1 = (_get_admin1() or "").strip()
        a2 = (_get_admin2() or "").strip()
        if a1 and n == a1:
            return True
        if a2 and n == a2:
            return True
    except Exception:
        pass
    user = _get_user_info(n)
    if not user:
        return False
    jb = (user.get("jb") or "").strip()
    if _jb_match(jb, "部长") or _jb_match(jb, "副部长"):
        return True
    return is_zonghe_tech_director(user)


def _get_approvers_first(name: str) -> List[dict]:
    """第一审批人：根据申请人 jb、lsys 按规则筛选"""
    user = _get_user_info(name)
    if not user:
        return []

    jb = (user.get("jb") or "").strip()
    lsys = (user.get("lsys") or "").strip()

    bz_cond, bz_p = _jb_sql_conditions("部长")
    fbz_cond, fbz_p = _jb_sql_conditions("副部长")
    bz_fbz_cond = f"({bz_cond[1:-1]} OR {fbz_cond[1:-1]})"
    bz_fbz_p = bz_p + fbz_p
    zr_cond, zr_p = _jb_sql_conditions("主任")
    fzr_cond, fzr_p = _jb_sql_conditions("副主任")
    zr_fzr_cond = f"({zr_cond[1:-1]} OR {fzr_cond[1:-1]})"
    zr_fzr_p = zr_p + fzr_p
    zz_cond, zz_p = _jb_sql_conditions("组长")
    zz_zr_fzr_cond = f"({zz_cond[1:-1]} OR {zr_cond[1:-1]} OR {fzr_cond[1:-1]})"
    zz_zr_fzr_p = zz_p + zr_p + fzr_p

    tail = " AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name"

    # 规则5: jb(部长/经理) -> 全部部领导（部长/副部长/经理/副经理/经理助理），排除本人
    # 注意：经理助理会误匹配 _jb_match(..., "部长")，需用副部长条件排除
    if _jb_match(jb, "部长") and not _jb_match(jb, "副部长"):
        rows = db.execute_query(
            f"SELECT name, jb, lsys FROM yggl WHERE {bz_fbz_cond} AND name != %s{tail}",
            bz_fbz_p + (name,),
        )
        return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]

    # 规则6: lsys(部办) 其他人员 -> jb(部长)
    if "部办" in lsys or lsys == "部办":
        rows = db.execute_query(f"SELECT name, jb, lsys FROM yggl WHERE {bz_cond}{tail}", bz_p)
        return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]

    # 规则4: jb(主任/副主任) -> jb(部长/副部长) + 同室主任/副主任（同级审批，排除本人）
    if _jb_match(jb, "主任") or _jb_match(jb, "副主任"):
        rows_bu = db.execute_query(f"SELECT name, jb, lsys FROM yggl WHERE {bz_fbz_cond}{tail}", bz_fbz_p)
        result = [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows_bu]
        if lsys:
            rows_room = db.execute_query(
                f"SELECT name, jb, lsys FROM yggl WHERE lsys = %s AND {zr_fzr_cond} AND name IS NOT NULL AND name != '' AND name != %s AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
                (lsys,) + zr_fzr_p + (name,)
            )
            for r in rows_room:
                result.append({"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")})
        return result

    # 规则2、3: jb(组长)、jb(责任工艺师) -> lsys(同词条) jb(主任/副主任)
    if _jb_match(jb, "组长") or _jb_match(jb, "责任工艺师"):
        if not lsys:
            return []
        rows = db.execute_query(
            f"SELECT name, jb, lsys FROM yggl WHERE lsys = %s AND {zr_fzr_cond}{tail}",
            (lsys,) + zr_fzr_p
        )
        return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]

    # 规则1: jb(员工) -> lsys(同词条) jb(组长/主任/副主任)
    if _jb_match(jb, "员工") or not jb:
        if not lsys:
            rows = db.execute_query(
                f"SELECT name, jb, lsys FROM yggl WHERE {zz_zr_fzr_cond} AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY lsys, jb, name",
                zz_zr_fzr_p
            )
        else:
            rows = db.execute_query(
                f"SELECT name, jb, lsys FROM yggl WHERE lsys = %s AND {zz_zr_fzr_cond}{tail}",
                (lsys,) + zz_zr_fzr_p
            )
        return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]

    # 其他级别默认：同室 组长/主任/副主任，若无则 部长/副部长
    if lsys:
        rows = db.execute_query(
            f"SELECT name, jb, lsys FROM yggl WHERE lsys = %s AND {zz_zr_fzr_cond}{tail}",
            (lsys,) + zz_zr_fzr_p
        )
        if rows:
            return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]

    rows = db.execute_query(f"SELECT name, jb, lsys FROM yggl WHERE {bz_fbz_cond}{tail}", bz_fbz_p)
    return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]


def _get_approvers_second(name: str) -> List[dict]:
    """第二审批人（二级审批）-> jb(部长/副部长)"""
    bz_cond, bz_p = _jb_sql_conditions("部长")
    fbz_cond, fbz_p = _jb_sql_conditions("副部长")
    cond = f"({bz_cond[1:-1]} OR {fbz_cond[1:-1]})"
    rows = db.execute_query(
        f"SELECT name, jb, lsys FROM yggl WHERE {cond} AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
        bz_p + fbz_p
    )
    return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]


def _get_dept_leaders() -> List[dict]:
    """部领导 -> jb(部长/副部长)"""
    bz_cond, bz_p = _jb_sql_conditions("部长")
    fbz_cond, fbz_p = _jb_sql_conditions("副部长")
    cond = f"({bz_cond[1:-1]} OR {fbz_cond[1:-1]})"
    rows = db.execute_query(
        f"SELECT name, jb, lsys FROM yggl WHERE {cond} AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
        bz_p + fbz_p
    )
    return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]


def _get_room_directors(name: str) -> List[dict]:
    """室主任 -> 同 lsys 的 jb(主任/副主任)"""
    user = _get_user_info(name)
    if not user:
        return []
    lsys = (user.get("lsys") or "").strip()
    if not lsys:
        return []
    zr_cond, zr_p = _jb_sql_conditions("主任")
    fzr_cond, fzr_p = _jb_sql_conditions("副主任")
    cond = f"({zr_cond[1:-1]} OR {fzr_cond[1:-1]})"
    rows = db.execute_query(
        f"SELECT name, jb, lsys FROM yggl WHERE lsys = %s AND {cond} AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
        (lsys,) + zr_p + fzr_p
    )
    return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]


@router.get("", response_model=dict)
def get_approvers(
    name: str = Query(..., description="申请人姓名"),
    level: str = Query("first", description="first=第一审批人, second=第二审批人, dept_leader=部领导, room_director=室主任")
):
    """
    根据审批规则返回可选审批人列表
    - level=first: 第一审批人（按申请人 jb、lsys 规则）
    - level=second: 第二审批人（部长/副部长）
    - level=dept_leader: 部领导（部长/副部长）
    - level=room_director: 室主任（同 lsys 的主任）
    """
    try:
        level = (level or "first").lower().strip()
        if level == "second":
            approvers = _get_approvers_second(name)
        elif level == "dept_leader":
            approvers = _get_dept_leaders()
        elif level == "room_director":
            approvers = _get_room_directors(name)
        else:
            approvers = _get_approvers_first(name)

        # 去重并按姓名排序
        seen = set()
        unique = []
        for a in approvers:
            n = (a.get("name") or "").strip()
            if n and n not in seen:
                seen.add(n)
                unique.append({"name": n, "jb": a.get("jb"), "lsys": a.get("lsys")})

        return {
            "success": True,
            "name": name,
            "level": level,
            "approvers": unique
        }
    except Exception as e:
        logger.error(f"获取审批人失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
