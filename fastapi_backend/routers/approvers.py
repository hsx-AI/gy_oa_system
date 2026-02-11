# -*- coding: utf-8 -*-
"""
审批人规则 API - 基于 yggl 表的 jb(级别) 和 lsys(隶属于室)
审批规则:
  1. jb(员工) -> lsys(同隶属于室) jb(组长/主任)
  2. jb(组长) -> lsys(同隶属于室) jb(主任)
  3. jb(责任工艺师) -> lsys(同隶属于室) jb(主任)
  4. jb(主任/副主任) -> jb(部长/副部长) + 同室 jb(主任/副主任)，同室列表排除本人（支持同级审批）
  5. lsys(隶属于室) 所有人员 -> jb(部长)
  6. 二级审批 -> jb(部长/副部长)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from database import db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvers", tags=["审批人"])


def _jb_match(jb_val: str, target: str) -> bool:
    """匹配级别，支持 组长/组长1 等变体"""
    if not jb_val:
        return False
    j = (jb_val or "").strip()
    if target == "组长":
        return j == "组长" or j.startswith("组长")
    if target == "副主任":
        return j == "副主任" or j.startswith("副主任") or "副主任" in j
    if target == "主任":
        return j == "主任" or j.startswith("主任")
    if target == "部长":
        return j == "部长" or j.startswith("部长")
    if target == "副部长":
        return j == "副部长" or j.startswith("副部长")
    if target == "员工":
        return j == "员工" or j.startswith("员工")
    if target == "责任工艺师":
        return "责任工艺师" in j or j == "责任工艺师"
    return j == target


def _get_user_info(name: str) -> Optional[dict]:
    """从 yggl 获取用户 jb 和 lsys"""
    rows = db.execute_query("SELECT jb, lsys FROM yggl WHERE name = %s LIMIT 1", (name,))
    if not rows:
        return None
    return rows[0]


def _get_approvers_first(name: str) -> List[dict]:
    """第一审批人：根据申请人 jb、lsys 按规则筛选"""
    user = _get_user_info(name)
    if not user:
        return []

    jb = (user.get("jb") or "").strip()
    lsys = (user.get("lsys") or "").strip()

    # 规则5: lsys(部办) 所有人员 -> jb(部长)
    if "部办" in lsys or lsys == "部办":
        rows = db.execute_query(
            "SELECT name, jb, lsys FROM yggl WHERE (jb = %s OR jb LIKE %s) AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
            ("部长", "部长%")
        )
        return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]

    # 规则4: jb(主任/副主任) -> jb(部长/副部长) + 同室主任/副主任（同级审批，排除本人）
    if _jb_match(jb, "主任") or _jb_match(jb, "副主任"):
        rows_bu = db.execute_query(
            "SELECT name, jb, lsys FROM yggl WHERE (jb = %s OR jb LIKE %s OR jb = %s OR jb LIKE %s) AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
            ("部长", "部长%", "副部长", "副部长%")
        )
        result = [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows_bu]
        if lsys:
            rows_room = db.execute_query(
                "SELECT name, jb, lsys FROM yggl WHERE lsys = %s AND ((jb = %s OR jb LIKE %s) OR (jb = %s OR jb LIKE %s)) AND name IS NOT NULL AND name != '' AND name != %s AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
                (lsys, "主任", "主任%", "副主任", "副主任%", name)
            )
            for r in rows_room:
                result.append({"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")})
        return result

    # 规则2、3: jb(组长)、jb(责任工艺师) -> lsys(同词条) jb(主任/副主任)
    if _jb_match(jb, "组长") or _jb_match(jb, "责任工艺师"):
        if not lsys:
            return []
        rows = db.execute_query(
            "SELECT name, jb, lsys FROM yggl WHERE lsys = %s AND ((jb = %s OR jb LIKE %s) OR (jb = %s OR jb LIKE %s)) AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
            (lsys, "主任", "主任%", "副主任", "副主任%")
        )
        return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]

    # 规则1: jb(员工) -> lsys(同词条) jb(组长/主任/副主任)
    if _jb_match(jb, "员工") or not jb:
        if not lsys:
            # 无 lsys 时降级：查所有 组长/主任/副主任
            rows = db.execute_query(
                "SELECT name, jb, lsys FROM yggl WHERE (jb = %s OR jb LIKE %s OR jb = %s OR jb LIKE %s OR jb = %s OR jb LIKE %s) AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY lsys, jb, name",
                ("组长", "组长%", "主任", "主任%", "副主任", "副主任%")
            )
        else:
            rows = db.execute_query(
                "SELECT name, jb, lsys FROM yggl WHERE lsys = %s AND ((jb = %s OR jb LIKE %s) OR (jb = %s OR jb LIKE %s) OR (jb = %s OR jb LIKE %s)) AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
                (lsys, "组长", "组长%", "主任", "主任%", "副主任", "副主任%")
            )
        return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]

    # 其他级别默认：同室 组长/主任/副主任，若无则 部长/副部长
    if lsys:
        rows = db.execute_query(
            "SELECT name, jb, lsys FROM yggl WHERE lsys = %s AND ((jb = %s OR jb LIKE %s) OR (jb = %s OR jb LIKE %s) OR (jb = %s OR jb LIKE %s)) AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
            (lsys, "组长", "组长%", "主任", "主任%", "副主任", "副主任%")
        )
        if rows:
            return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]

    rows = db.execute_query(
        "SELECT name, jb, lsys FROM yggl WHERE (jb = %s OR jb LIKE %s OR jb = %s OR jb LIKE %s) AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
        ("部长", "部长%", "副部长", "副部长%")
    )
    return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]


def _get_approvers_second(name: str) -> List[dict]:
    """第二审批人（二级审批）-> jb(部长/副部长)"""
    rows = db.execute_query(
        "SELECT name, jb, lsys FROM yggl WHERE (jb = %s OR jb LIKE %s OR jb = %s OR jb LIKE %s) AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
        ("部长", "部长%", "副部长", "副部长%")
    )
    return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]


def _get_dept_leaders() -> List[dict]:
    """部领导 -> jb(部长/副部长)"""
    rows = db.execute_query(
        "SELECT name, jb, lsys FROM yggl WHERE (jb = %s OR jb LIKE %s OR jb = %s OR jb LIKE %s) AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
        ("部长", "部长%", "副部长", "副部长%")
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
    rows = db.execute_query(
        "SELECT name, jb, lsys FROM yggl WHERE lsys = %s AND ((jb = %s OR jb LIKE %s) OR (jb = %s OR jb LIKE %s)) AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
        (lsys, "主任", "主任%", "副主任", "副主任%")
    )
    return [{"name": r["name"], "jb": r.get("jb"), "lsys": r.get("lsys")} for r in rows]


@router.get("", response_model=dict)
async def get_approvers(
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
