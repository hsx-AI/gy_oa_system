# -*- coding: utf-8 -*-
"""
部门通讯录 API
"""
import logging
from typing import Optional
from fastapi import APIRouter, Query
from database import db, db_demo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contacts", tags=["通讯录"])

JB_RANK = [
    ("副经理", 2), ("经理", 1),
    ("副主任", 4), ("主任", 3),
    ("副组长", 6), ("组长", 5),
]


def _jb_sort_key(jb: str) -> int:
    jb = (jb or "").strip()
    for keyword, rank in JB_RANK:
        if keyword in jb:
            return rank
    return 99


@router.get("/list")
async def get_contacts(
    department: Optional[str] = Query(None, description="筛选科室"),
    keyword: Optional[str] = Query(None, description="搜索关键字（姓名/工号/手机/座机）"),
):
    """按科室分组返回通讯录，领导优先排序"""
    try:
        sql = (
            "SELECT name, gh, lsys, jb, rcnf, sfzh, enterprise_email "
            "FROM yggl WHERE COALESCE(zaizhi, 0) = 0 "
            "AND TRIM(lsys) NOT IN ('其他部门员工', '其他部门成员', '') "
            "AND lsys IS NOT NULL "
            "AND RIGHT(TRIM(name), 1) != '1' "
        )
        params = []
        if department:
            sql += " AND lsys = %s"
            params.append(department.strip())
        sql += " ORDER BY lsys, gh"
        rows = db.execute_query(sql, tuple(params) if params else None)
        if not rows:
            return {"success": True, "departments": [], "total": 0}

        sfzh_map = {}
        for r in rows:
            sfzh = (r.get("sfzh") or "").strip().replace(" ", "")
            if sfzh:
                sfzh_map[sfzh] = (r.get("name") or "").strip()

        phone_map = {}
        if sfzh_map:
            id_cards = list(sfzh_map.keys())
            batch_size = 100
            for i in range(0, len(id_cards), batch_size):
                batch = id_cards[i:i + batch_size]
                ph = ",".join(["%s"] * len(batch))
                try:
                    demo_rows = db_demo.execute_query(
                        f"SELECT id_card, mobile, telephone FROM employee_info WHERE id_card IN ({ph})",
                        tuple(batch),
                    )
                    for dr in demo_rows or []:
                        idc = (dr.get("id_card") or "").strip()
                        name = sfzh_map.get(idc, "")
                        if name:
                            phone_map[name] = {
                                "mobile": (dr.get("mobile") or "").strip(),
                                "telephone": (dr.get("telephone") or "").strip(),
                            }
                except Exception as e:
                    logger.warning("查询 demo 库 employee_info 失败: %s", e)

        dept_groups = {}
        for r in rows:
            name = (r.get("name") or "").strip()
            dept = (r.get("lsys") or "").strip()
            jb = (r.get("jb") or "").strip()
            gh = (r.get("gh") or "").strip()
            rcnf = r.get("rcnf")
            if hasattr(rcnf, "strftime"):
                rcnf_str = rcnf.strftime("%Y-%m-%d")
            else:
                rcnf_str = str(rcnf)[:10] if rcnf else ""
            phones = phone_map.get(name, {})
            mobile = phones.get("mobile", "")
            telephone = phones.get("telephone", "")
            email = (r.get("enterprise_email") or "").strip()

            if keyword:
                kw = keyword.strip().lower()
                searchable = f"{name}{gh}{mobile}{telephone}{email}{dept}{jb}".lower()
                if kw not in searchable:
                    continue

            person = {
                "name": name,
                "gh": gh,
                "jb": jb,
                "department": dept,
                "mobile": mobile,
                "telephone": telephone,
                "email": email,
                "rcnf": rcnf_str,
            }
            dept_groups.setdefault(dept, []).append(person)

        DEPT_ORDER = [
            "部办",
            "综合技术室", "工具技术室", "数控编程室", "智能制造技术室",
            "水发工艺室", "水轮机工艺室", "汽发工艺室", "焊接工艺室", "非标技术室",
        ]

        def dept_sort_key(dept_name):
            try:
                return DEPT_ORDER.index(dept_name)
            except ValueError:
                return len(DEPT_ORDER)

        for members in dept_groups.values():
            members.sort(key=lambda p: (_jb_sort_key(p["jb"]), p["gh"]))

        sorted_depts = sorted(dept_groups.keys(), key=dept_sort_key)
        departments = []
        total = 0
        for dept_name in sorted_depts:
            members = dept_groups[dept_name]
            total += len(members)
            departments.append({
                "name": dept_name,
                "count": len(members),
                "members": members,
            })

        return {"success": True, "departments": departments, "total": total}
    except Exception as e:
        logger.error("获取通讯录失败: %s", e)
        return {"success": False, "departments": [], "total": 0, "error": str(e)}
