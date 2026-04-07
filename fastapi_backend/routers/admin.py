# -*- coding: utf-8 -*-
"""
管理员 API - 员工在职/离职管理
- 部长/副部长：可管理全部科室
- 各科室主任：仅可管理本室（lsys）员工
利用 yggl.zaizhi：0=在职，1=离职；离职人员不参与统计与显示，且不可登录。
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from database import db
from routers.db_manager import _get_admin1
from utils.hxp_helper import compute_expire_date, parse_expire_for_sort
from io import BytesIO
from datetime import datetime, date
import uuid
import json
import logging

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["管理员"])


def _get_admin2() -> Optional[str]:
    """从 webconfig 表读取 admin2（人事管理员用户名，与 yggl.name 对应）。"""
    try:
        rows = db.execute_query(
            "SELECT admin2 FROM webconfig WHERE id = %s LIMIT 1",
            ("1",),
        )
        if rows and rows[0].get("admin2") is not None:
            return (rows[0]["admin2"] or "").strip() or None
    except Exception as e:
        logger.debug(f"读取 webconfig.admin2 失败: {e}")
    return None


def _jb_is_minister_or_deputy(jb: str) -> bool:
    """yggl.jb 是否为部长/副部长权限（含新职务名称映射）。"""
    from routers.approvers import _jb_match
    return _jb_match(jb, "部长") or _jb_match(jb, "副部长")


def _can_manage_hxp_batch(name: str) -> bool:
    """换休票批量管理页：系统管理员 admin1、人事管理员 admin2、或 yggl 部长/副部长。"""
    ns = (name or "").strip()
    if not ns:
        return False
    a1 = _get_admin1()
    if a1 and ns == a1:
        return True
    a2 = _get_admin2()
    if a2 and ns == a2:
        return True
    rows = db.execute_query("SELECT jb FROM yggl WHERE name = %s LIMIT 1", (ns,))
    if not rows:
        return False
    return _jb_is_minister_or_deputy(rows[0].get("jb") or "")


def _get_admin_scope(name: str) -> Optional[Dict[str, Any]]:
    """
    获取当前用户的管理权限范围。
    返回: None=无权限; {"role": "full", "lsys": None}=部长/副部长/人事管理员(admin2)可管全部;
          {"role": "dept", "lsys": "科室名"}=主任仅可管本室。
    """
    if not (name or "").strip():
        return None
    name_stripped = name.strip()
    # 系统管理员（webconfig.admin1）最高权限，等同部长+人事管理员（不含打卡管理员最终审批加班）
    admin1 = _get_admin1()
    if admin1 and name_stripped == admin1:
        return {"role": "full", "lsys": None}
    # 人事管理员（webconfig.admin2）权限等同于部长/副部长
    admin2 = _get_admin2()
    if admin2 and name_stripped == admin2:
        return {"role": "full", "lsys": None}
    rows = db.execute_query(
        "SELECT jb, lsys FROM yggl WHERE name = %s LIMIT 1",
        (name_stripped,)
    )
    if not rows:
        return None
    jb = (rows[0].get("jb") or "").strip()
    lsys = (rows[0].get("lsys") or "").strip()
    if _jb_is_minister_or_deputy(jb):
        return {"role": "full", "lsys": None}
    from routers.approvers import _jb_match
    if _jb_match(jb, "主任") or _jb_match(jb, "副主任"):
        return {"role": "dept", "lsys": lsys}
    if jb == "副主任" or (jb and ("副主任" in jb or jb.startswith("副主任"))):
        return {"role": "dept", "lsys": lsys}
    return None


@router.get("/employees")
async def list_employees(
    current_user: str = Query(..., description="当前登录用户姓名，用于权限校验"),
    zaizhi: Optional[str] = Query("0", description="在职状态：0=在职 1=离职 all=全部"),
    lsys: Optional[str] = Query(None, description="按科室筛选"),
    q: Optional[str] = Query(None, description="按姓名模糊搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """
    员工列表（含在职状态）。部长/副部长可查全部；主任仅可查本室。
    返回: { success, list, total, scope?: { role, lsys } }
    """
    scope = _get_admin_scope(current_user)
    if not scope:
        raise HTTPException(status_code=403, detail="仅部长/副部长/科室主任可查看员工在职管理")
    try:
        conditions = ["name IS NOT NULL", "name != ''"]
        params: list = []
        if scope["role"] == "dept":
            # 主任只能看本室
            if not scope.get("lsys"):
                return {"success": True, "list": [], "total": 0, "scope": {"role": "dept", "lsys": ""}}
            conditions.append("lsys = %s")
            params.append(scope["lsys"])
        elif lsys and lsys.strip():
            conditions.append("lsys = %s")
            params.append(lsys.strip())
        if zaizhi and zaizhi.lower() != "all":
            if zaizhi == "0":
                conditions.append("(COALESCE(zaizhi,0)=0)")
            elif zaizhi == "1":
                conditions.append("(COALESCE(zaizhi,0)=1)")
        if q and q.strip():
            conditions.append("name LIKE %s")
            params.append(f"%{q.strip()}%")
        where = " AND ".join(conditions)
        count_sql = f"SELECT COUNT(*) AS cnt FROM yggl WHERE {where}"
        total = db.execute_scalar(count_sql, tuple(params) if params else None) or 0
        select_sql = (
            f"SELECT name, gh, lsys, jb, COALESCE(zaizhi,0) AS zaizhi FROM yggl WHERE {where} "
            "ORDER BY lsys, name LIMIT %s OFFSET %s"
        )
        params.extend([page_size, (page - 1) * page_size])
        rows = db.execute_query(select_sql, tuple(params))
        list_data = []
        for r in rows:
            z = int(r.get("zaizhi") or 0)
            list_data.append({
                "name": (r.get("name") or "").strip(),
                "gh": (r.get("gh") or "").strip(),
                "lsys": (r.get("lsys") or "").strip(),
                "jb": (r.get("jb") or "").strip(),
                "zaizhi": z,
                "zaizhiText": "离职" if z == 1 else "在职"
            })
        result = {"success": True, "list": list_data, "total": total}
        if scope["role"] == "dept":
            result["scope"] = {"role": "dept", "lsys": scope.get("lsys") or ""}
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"员工列表查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class AddEmployeeRequest(BaseModel):
    """添丁：向 yggl 主表新增一条员工记录"""
    current_user: str  # 当前操作人，用于权限校验
    name: str          # 姓名（必填，登录用）
    gh: str = ""       # 工号
    lsys: str = ""     # 隶属科室
    jb: str = ""       # 级别（如 员工、组长、主任 等）
    xbie: str = ""     # 性别
    password: str = "" # 初始登录密码（必填，至少4位）


@router.post("/employee")
async def add_employee(req: AddEmployeeRequest):
    """
    添丁：在 yggl 主表新增员工。部长/副部长可添加任意科室；主任仅可添加本室。
    必填：姓名、初始密码（至少4位）。
    """
    scope = _get_admin_scope(req.current_user)
    if not scope:
        raise HTTPException(status_code=403, detail="仅部长/副部长/科室主任可添加员工")
    name = (req.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="请填写姓名")
    pwd = (req.password or "").strip()
    if len(pwd) < 4:
        raise HTTPException(status_code=400, detail="初始密码至少4位")
    # 主任只能添加本室
    if scope["role"] == "dept":
        allowed_lsys = (scope.get("lsys") or "").strip()
        if (req.lsys or "").strip() != allowed_lsys:
            raise HTTPException(status_code=403, detail="仅可添加本室员工，请选择本室")
        lsys_val = allowed_lsys
    else:
        lsys_val = (req.lsys or "").strip()
    # 姓名不可重复
    exist = db.execute_query("SELECT 1 FROM yggl WHERE name = %s LIMIT 1", (name,))
    if exist:
        raise HTTPException(status_code=400, detail="该姓名已存在，请勿重复添加")
    try:
        gh_val = (req.gh or "").strip()
        jb_val = (req.jb or "").strip()
        xbie_val = (req.xbie or "").strip()
        # yggl 常用字段：name, pass, gh, lsys, jb, xbie, zaizhi；若有 lsysjm 可同 lsys 或空
        sql = (
            "INSERT INTO yggl (name, `pass`, gh, lsys, jb, xbie, zaizhi) "
            "VALUES (%s, %s, %s, %s, %s, %s, 0)"
        )
        db.execute_update(sql, (name, pwd, gh_val, lsys_val, jb_val, xbie_val))
        return {
            "success": True,
            "message": "添加成功，新员工可凭姓名与初始密码登录",
            "name": name,
            "lsys": lsys_val,
        }
    except Exception as e:
        logger.error(f"添加员工失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class SetEmployeeStatusRequest(BaseModel):
    current_user: str  # 当前操作人，用于权限校验
    name: str          # 被操作员工姓名
    zaizhi: int        # 0=设为在职 1=设为离职


class UpdateEmployeeDeptLevelRequest(BaseModel):
    """更新员工科室/级别（升职降级、部门调动）"""
    current_user: str
    name: str
    lsys: Optional[str] = None   # 新科室，仅部长/副部长可改
    jb: Optional[str] = None     # 新级别


@router.post("/employee-update-dept-level")
async def update_employee_dept_level(req: UpdateEmployeeDeptLevelRequest):
    """
    更新员工科室、级别。仅部长/副部长可操作；主任不可改科室与级别。
    """
    scope = _get_admin_scope(req.current_user)
    if not scope:
        raise HTTPException(status_code=403, detail="仅部长/副部长/科室主任可访问")
    if scope["role"] == "dept":
        raise HTTPException(status_code=403, detail="仅部长/副部长可修改员工科室与级别")
    name = (req.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="请指定员工姓名")
    try:
        emp_rows = db.execute_query("SELECT lsys, jb FROM yggl WHERE name = %s LIMIT 1", (name,))
        if not emp_rows:
            raise HTTPException(status_code=404, detail="未找到该员工")
        emp_lsys = (emp_rows[0].get("lsys") or "").strip()
        emp_jb = (emp_rows[0].get("jb") or "").strip()
        new_lsys = (req.lsys if req.lsys is not None else emp_lsys).strip()
        new_jb = (req.jb if req.jb is not None else emp_jb).strip()

        db.execute_update(
            "UPDATE yggl SET lsys = %s, jb = %s WHERE name = %s",
            (new_lsys, new_jb, name)
        )
        return {
            "success": True,
            "message": "已更新",
            "name": name,
            "lsys": new_lsys,
            "jb": new_jb
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新员工科室/级别失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/employee-status")
async def set_employee_status(req: SetEmployeeStatusRequest):
    """设置员工在职状态（0=在职 1=离职）。部长/副部长可操作全部；主任仅可操作本室员工。"""
    scope = _get_admin_scope(req.current_user)
    if not scope:
        raise HTTPException(status_code=403, detail="仅部长/副部长/科室主任可操作员工在职状态")
    if req.zaizhi not in (0, 1):
        raise HTTPException(status_code=400, detail="zaizhi 只能为 0（在职）或 1（离职）")
    if not (req.name or "").strip():
        raise HTTPException(status_code=400, detail="请指定员工姓名")
    try:
        if scope["role"] == "dept":
            # 主任只能改本室员工：先查该员工是否属于本室
            emp_rows = db.execute_query(
                "SELECT lsys FROM yggl WHERE name = %s LIMIT 1",
                (req.name.strip(),)
            )
            if not emp_rows:
                return {"success": False, "message": "未找到该员工"}
            emp_lsys = (emp_rows[0].get("lsys") or "").strip()
            if emp_lsys != (scope.get("lsys") or ""):
                raise HTTPException(status_code=403, detail="仅可设置本室员工的在职状态")
        n = db.execute_update(
            "UPDATE yggl SET zaizhi = %s WHERE name = %s",
            (req.zaizhi, req.name.strip())
        )
        if n <= 0:
            return {"success": False, "message": "未找到该员工或未变更"}
        return {
            "success": True,
            "message": "已设为在职" if req.zaizhi == 0 else "已设为离职",
            "name": req.name.strip(),
            "zaizhi": req.zaizhi
        }
    except Exception as e:
        logger.error(f"设置在职状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dept-list")
async def admin_dept_list(
    current_user: str = Query(..., description="当前登录用户，用于权限校验")
):
    """管理员页获取科室列表。部长/副部长获全部；主任仅获本室。"""
    scope = _get_admin_scope(current_user)
    if not scope:
        raise HTTPException(status_code=403, detail="仅部长/副部长/科室主任可访问")
    try:
        if scope["role"] == "dept" and scope.get("lsys"):
            return {"success": True, "list": [scope["lsys"]], "scope": {"role": "dept", "lsys": scope["lsys"]}}
        # 排除末尾为「1」的科室（视为已撤销/历史），与统计等逻辑一致
        rows = db.execute_query(
            "SELECT DISTINCT lsys FROM yggl WHERE lsys IS NOT NULL AND lsys != '' "
            "AND RIGHT(TRIM(lsys), 1) != '1' "
            "AND TRIM(lsys) != '其他部门员工' "
            "ORDER BY lsys"
        )
        list_data = [r["lsys"].strip() for r in rows if r.get("lsys")]
        return {"success": True, "list": list_data}
    except Exception as e:
        logger.error(f"科室列表查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-employees")
async def export_employees_excel(
    current_user: str = Query(..., description="当前登录用户，用于权限校验")
):
    """
    导出在职员工表格（按科室排序）。部长/副部长导出全部；主任仅导出本室。
    返回 Excel 文件：科室、姓名、工号、级别、性别。
    """
    scope = _get_admin_scope(current_user)
    if not scope:
        raise HTTPException(status_code=403, detail="仅部长/副部长/科室主任可导出")
    if not HAS_OPENPYXL:
        raise HTTPException(status_code=500, detail="服务端未安装 openpyxl，无法生成 Excel")
    try:
        base_sql = (
            "SELECT lsys, name, gh, jb, xbie FROM yggl "
            "WHERE (COALESCE(zaizhi,0)=0) AND name IS NOT NULL AND name != '' "
        )
        if scope["role"] == "dept" and scope.get("lsys"):
            rows = db.execute_query(base_sql + " AND lsys = %s ORDER BY name", (scope["lsys"],))
        else:
            rows = db.execute_query(base_sql + " ORDER BY lsys, name")
        wb = Workbook()
        ws = wb.active
        ws.title = "在职员工按科室"
        headers = ["科室", "姓名", "工号", "级别", "性别"]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")
        for r in rows:
            ws.append([
                (r.get("lsys") or "").strip(),
                (r.get("name") or "").strip(),
                (r.get("gh") or "").strip(),
                (r.get("jb") or "").strip(),
                (r.get("xbie") or "").strip(),
            ])
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        # 使用纯 ASCII 文件名，避免 HTTP 头编码报错 ordinal not in range(256)
        filename_ascii = f"employees_by_dept_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename_ascii}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出在职员工表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 换休票批量增减 ====================

class HxpBatchRequest(BaseModel):
    current_user: str
    names: List[str]
    amount: float
    action: str  # "add" | "subtract"
    ly: str = ""


@router.post("/hxp/batch")
async def hxp_batch(req: HxpBatchRequest):
    """
    批量增减换休票。系统管理员、人事管理员或 yggl 部长/副部长可操作。
    add：为每人新增一条 hxp 记录，sj=当前时间。
    subtract：按过期日期从早到晚扣减，不足则跳过。
    """
    name = (req.current_user or "").strip()
    if not name:
        raise HTTPException(status_code=403, detail="未登录")
    if not _can_manage_hxp_batch(name):
        raise HTTPException(status_code=403, detail="仅系统管理员、人事管理员或部长/副部长可执行此操作")

    names = [n.strip() for n in req.names if n.strip()]
    if not names:
        raise HTTPException(status_code=400, detail="姓名列表不能为空")
    amount = round(req.amount, 3)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="数量必须大于 0")

    from utils.hxp_helper import compute_expire_date, parse_expire_for_sort
    from datetime import date

    results = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = date.today().strftime("%Y-%m-%d")

    for emp_name in names:
        emp_rows = db.execute_query(
            "SELECT name FROM yggl WHERE name = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
            (emp_name,),
        )
        if not emp_rows:
            results.append({"name": emp_name, "ok": False, "msg": "未找到在职员工"})
            continue

        if req.action == "add":
            hxp_id = uuid.uuid4().hex
            ly = (req.ly or "").strip() or "管理员手动增加"
            try:
                db.execute_update(
                    "INSERT INTO hxp (id, name, sl, sj, ly) VALUES (%s, %s, %s, %s, %s)",
                    (hxp_id, emp_name, amount, now_str, ly),
                )
                results.append({"name": emp_name, "ok": True, "msg": f"+{amount}"})
            except Exception as e:
                results.append({"name": emp_name, "ok": False, "msg": str(e)})

        elif req.action == "subtract":
            try:
                rows = db.execute_query(
                    "SELECT id, sl, sj FROM hxp WHERE name = %s AND sl > 0 ORDER BY id",
                    (emp_name,),
                )
                rows_with_exp = []
                for r in rows:
                    exp = compute_expire_date(r.get("sj"))
                    if exp and exp < today:
                        continue
                    rows_with_exp.append((r, parse_expire_for_sort(exp) if exp else (9999, 12)))
                rows_with_exp.sort(key=lambda x: x[1])

                avail = sum(float(r.get("sl") or 0) for r, _ in rows_with_exp)
                if avail < amount:
                    results.append({"name": emp_name, "ok": False, "msg": f"余额不足（可用 {avail}）"})
                    continue

                remain = amount
                for row, _ in rows_with_exp:
                    if remain <= 0:
                        break
                    rid = row["id"]
                    sl = float(row.get("sl") or 0)
                    if sl <= 0:
                        continue
                    if remain >= sl:
                        db.execute_update("DELETE FROM hxp WHERE id = %s", (rid,))
                        remain = round(remain - sl, 3)
                    else:
                        db.execute_update(
                            "UPDATE hxp SET sl = ROUND(sl - %s, 3) WHERE id = %s",
                            (round(remain, 3), rid),
                        )
                        remain = 0
                results.append({"name": emp_name, "ok": True, "msg": f"-{amount}"})
            except Exception as e:
                results.append({"name": emp_name, "ok": False, "msg": str(e)})
        else:
            raise HTTPException(status_code=400, detail="action 必须为 add 或 subtract")

    ok_count = sum(1 for r in results if r["ok"])
    fail_count = len(results) - ok_count
    return {
        "success": True,
        "message": f"处理完成：成功 {ok_count}，失败 {fail_count}",
        "results": results,
    }


# ==================== 换休票统计 ====================


@router.get("/hxp/summary")
async def hxp_summary(
    current_user: str = Query(..., description="当前用户姓名，用于权限校验"),
    keyword: Optional[str] = Query(None, description="姓名关键字"),
    lsys: Optional[str] = Query(None, description="隶属室筛选"),
):
    """全员换休票余额汇总（系统管理员、人事管理员或部长/副部长）"""
    cu = (current_user or "").strip()
    if not cu or not _can_manage_hxp_batch(cu):
        raise HTTPException(status_code=403, detail="无权查看换休票统计")
    today_str = date.today().strftime("%Y-%m-%d")

    emp_rows = db.execute_query(
        "SELECT name, lsys FROM yggl WHERE COALESCE(zaizhi,0) = 0 ORDER BY lsys, name"
    )
    if not emp_rows:
        return {"success": True, "data": [], "lsys_list": []}

    hxp_rows = db.execute_query("SELECT name, sl, sj FROM hxp WHERE sl > 0") or []

    hxp_by_name: Dict[str, float] = {}
    for r in hxp_rows:
        n = (r.get("name") or "").strip()
        try:
            sl = float(r.get("sl") or 0)
        except (TypeError, ValueError):
            sl = 0.0
        if sl <= 0:
            continue
        exp = compute_expire_date(r.get("sj"))
        if exp and exp < today_str:
            continue
        hxp_by_name[n] = hxp_by_name.get(n, 0.0) + sl

    lsys_set = set()
    data = []
    for emp in emp_rows:
        name = (emp.get("name") or "").strip()
        emp_lsys = (emp.get("lsys") or "").strip()
        if not name:
            continue
        if emp_lsys:
            lsys_set.add(emp_lsys)
        if keyword and keyword.strip() not in name:
            continue
        if lsys and lsys.strip() and emp_lsys != lsys.strip():
            continue
        total = round(hxp_by_name.get(name, 0.0), 2)
        data.append({"name": name, "lsys": emp_lsys, "total": total})

    data.sort(key=lambda x: (-x["total"], x["name"]))
    return {"success": True, "data": data, "lsys_list": sorted(lsys_set)}


@router.get("/hxp/detail")
async def hxp_detail(
    current_user: str = Query(..., description="当前用户姓名，用于权限校验"),
    name: str = Query(..., description="员工姓名"),
):
    """查询指定员工的全部换休票获取记录（系统管理员、人事管理员或部长/副部长）"""
    cu = (current_user or "").strip()
    if not cu or not _can_manage_hxp_batch(cu):
        raise HTTPException(status_code=403, detail="无权查看换休票明细")
    rows = db.execute_query(
        "SELECT id, name, sl, sj, ly FROM hxp WHERE name = %s ORDER BY sj DESC",
        (name.strip(),),
    )
    today_str = date.today().strftime("%Y-%m-%d")
    items = []
    for r in (rows or []):
        try:
            sl = float(r.get("sl") or 0)
        except (TypeError, ValueError):
            sl = 0.0
        sj_raw = r.get("sj")
        if hasattr(sj_raw, "strftime"):
            sj_str = sj_raw.strftime("%Y-%m-%d %H:%M:%S")
        else:
            sj_str = str(sj_raw or "")
        exp = compute_expire_date(r.get("sj"))
        expired = bool(exp and exp < today_str)
        items.append({
            "id": r.get("id") or "",
            "sl": round(sl, 2),
            "sj": sj_str,
            "ly": (r.get("ly") or "").strip() or "-",
            "expire": exp,
            "expired": expired,
        })
    return {"success": True, "name": name.strip(), "data": items}


# ==================== 换休票审批流程 ====================


def _ensure_hxp_approval_table():
    """启动时确保 hxp_approval 表存在。"""
    try:
        db.execute_update("""
            CREATE TABLE IF NOT EXISTS hxp_approval (
                id VARCHAR(36) PRIMARY KEY,
                applicant VARCHAR(50) NOT NULL,
                action VARCHAR(10) NOT NULL,
                amount DECIMAL(10,3) NOT NULL,
                ly VARCHAR(500) NOT NULL DEFAULT '',
                names_json TEXT NOT NULL,
                approver VARCHAR(50) NOT NULL,
                status TINYINT NOT NULL DEFAULT 0,
                reject_reason VARCHAR(500) DEFAULT '',
                apply_time DATETIME,
                approve_time DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """, ())
        logger.info("hxp_approval 表已就绪")
    except Exception as e:
        logger.warning(f"hxp_approval 表创建/检查失败（可能已存在）: {e}")


_ensure_hxp_approval_table()


class HxpApplyRequest(BaseModel):
    current_user: str
    names: List[str]
    amount: float
    action: str       # "add" | "subtract"
    ly: str           # 原因（必填）
    approver: str     # 审批人姓名


@router.post("/hxp/apply")
async def hxp_apply(req: HxpApplyRequest):
    """提交换休票增减审批申请。系统管理员、人事管理员或 yggl 部长/副部长可操作。"""
    name = (req.current_user or "").strip()
    if not name:
        raise HTTPException(status_code=403, detail="未登录")
    if not _can_manage_hxp_batch(name):
        raise HTTPException(status_code=403, detail="仅系统管理员、人事管理员或部长/副部长可提交")

    names = [n.strip() for n in req.names if n.strip()]
    if not names:
        raise HTTPException(status_code=400, detail="姓名列表不能为空")
    amount = round(req.amount, 3)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="数量必须大于 0")
    if req.action not in ("add", "subtract"):
        raise HTTPException(status_code=400, detail="action 必须为 add 或 subtract")
    ly = (req.ly or "").strip()
    if not ly:
        raise HTTPException(status_code=400, detail="原因不能为空")
    approver = (req.approver or "").strip()
    if not approver:
        raise HTTPException(status_code=400, detail="审批人不能为空")

    urows = db.execute_query("SELECT jb FROM yggl WHERE name = %s LIMIT 1", (name,))
    if urows and _jb_is_minister_or_deputy(urows[0].get("jb") or ""):
        if approver == name:
            raise HTTPException(status_code=400, detail="部长/副部长不能选择自己作为审批人")

    rid = uuid.uuid4().hex
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute_update(
        "INSERT INTO hxp_approval (id, applicant, action, amount, ly, names_json, approver, status, apply_time) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s)",
        (rid, name, req.action, amount, ly, json.dumps(names, ensure_ascii=False), approver, now_str),
    )
    return {
        "success": True,
        "message": f"已提交审批，等待 {approver} 审批",
        "id": rid,
    }


@router.get("/hxp/pending-approvals")
async def hxp_pending_approvals(approver: str = Query(..., description="审批人姓名")):
    """查询待审批的换休票申请（status=0 且 approver 匹配）。"""
    rows = db.execute_query(
        "SELECT id, applicant, action, amount, ly, names_json, approver, status, apply_time "
        "FROM hxp_approval WHERE approver = %s AND status = 0 ORDER BY apply_time DESC",
        (approver.strip(),),
    )
    data = []
    for r in (rows or []):
        try:
            names_list = json.loads(r.get("names_json") or "[]")
        except (json.JSONDecodeError, TypeError):
            names_list = []
        at = r.get("apply_time")
        if hasattr(at, "strftime"):
            at = at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            at = str(at or "")
        data.append({
            "id": r["id"],
            "applicant": r.get("applicant") or "",
            "action": r.get("action") or "",
            "amount": float(r.get("amount") or 0),
            "ly": r.get("ly") or "",
            "names": names_list,
            "namesCount": len(names_list),
            "approver": r.get("approver") or "",
            "applyTime": at,
        })
    return {"success": True, "data": data}


class HxpApprovalActionRequest(BaseModel):
    action: str       # "approve" | "reject"
    approver: str
    reason: str = ""


@router.post("/hxp/approval/{approval_id}/action")
async def hxp_approval_action(approval_id: str, req: HxpApprovalActionRequest):
    """审批换休票申请：通过 / 驳回。"""
    approver = (req.approver or "").strip()
    if not approver:
        raise HTTPException(status_code=400, detail="审批人不能为空")

    rows = db.execute_query(
        "SELECT id, applicant, action, amount, ly, names_json, approver, status "
        "FROM hxp_approval WHERE id = %s LIMIT 1",
        (approval_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="审批单不存在")
    record = rows[0]
    if record.get("status") != 0:
        raise HTTPException(status_code=400, detail="该审批单已处理")
    if (record.get("approver") or "").strip() != approver:
        raise HTTPException(status_code=403, detail="您不是该申请的审批人")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if req.action == "reject":
        db.execute_update(
            "UPDATE hxp_approval SET status = 22, reject_reason = %s, approve_time = %s WHERE id = %s",
            ((req.reason or "").strip(), now_str, approval_id),
        )
        return {"success": True, "message": "已驳回"}

    if req.action != "approve":
        raise HTTPException(status_code=400, detail="action 必须为 approve 或 reject")

    # 执行实际换休票增减
    try:
        names_list = json.loads(record.get("names_json") or "[]")
    except (json.JSONDecodeError, TypeError):
        names_list = []
    amount = float(record.get("amount") or 0)
    act = (record.get("action") or "").strip()
    ly = (record.get("ly") or "").strip() or "管理员操作"
    applicant = (record.get("applicant") or "").strip()
    today = date.today().strftime("%Y-%m-%d")

    results = []
    for emp_name in names_list:
        emp_rows = db.execute_query(
            "SELECT name FROM yggl WHERE name = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
            (emp_name,),
        )
        if not emp_rows:
            results.append({"name": emp_name, "ok": False, "msg": "未找到在职员工"})
            continue

        if act == "add":
            hxp_id = uuid.uuid4().hex
            try:
                db.execute_update(
                    "INSERT INTO hxp (id, name, sl, sj, ly) VALUES (%s, %s, %s, %s, %s)",
                    (hxp_id, emp_name, amount, now_str, ly),
                )
                results.append({"name": emp_name, "ok": True, "msg": f"+{amount}"})
            except Exception as e:
                results.append({"name": emp_name, "ok": False, "msg": str(e)})

        elif act == "subtract":
            try:
                hxp_rows = db.execute_query(
                    "SELECT id, sl, sj FROM hxp WHERE name = %s AND sl > 0 ORDER BY id",
                    (emp_name,),
                )
                rows_with_exp = []
                for r in hxp_rows:
                    exp = compute_expire_date(r.get("sj"))
                    if exp and exp < today:
                        continue
                    rows_with_exp.append((r, parse_expire_for_sort(exp) if exp else (9999, 12)))
                rows_with_exp.sort(key=lambda x: x[1])

                avail = sum(float(r.get("sl") or 0) for r, _ in rows_with_exp)
                if avail < amount:
                    results.append({"name": emp_name, "ok": False, "msg": f"余额不足（可用 {avail}）"})
                    continue

                remain = amount
                for row, _ in rows_with_exp:
                    if remain <= 0:
                        break
                    rid = row["id"]
                    sl = float(row.get("sl") or 0)
                    if sl <= 0:
                        continue
                    if remain >= sl:
                        db.execute_update("DELETE FROM hxp WHERE id = %s", (rid,))
                        remain = round(remain - sl, 3)
                    else:
                        db.execute_update(
                            "UPDATE hxp SET sl = ROUND(sl - %s, 3) WHERE id = %s",
                            (round(remain, 3), rid),
                        )
                        remain = 0
                results.append({"name": emp_name, "ok": True, "msg": f"-{amount}"})
            except Exception as e:
                results.append({"name": emp_name, "ok": False, "msg": str(e)})

    db.execute_update(
        "UPDATE hxp_approval SET status = 2, approve_time = %s WHERE id = %s",
        (now_str, approval_id),
    )

    ok_count = sum(1 for r in results if r["ok"])
    fail_count = len(results) - ok_count
    return {
        "success": True,
        "message": f"已通过并执行：成功 {ok_count}，失败 {fail_count}",
        "results": results,
    }


@router.post("/hxp/approval/{approval_id}/resubmit")
async def resubmit_hxp_approval(approval_id: str, req: HxpApplyRequest):
    """修改并重新提交已驳回的换休票管理申请（status 22→0，更新字段）"""
    rows = db.execute_query(
        "SELECT id, applicant, status FROM hxp_approval WHERE id = %s LIMIT 1",
        (approval_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    r = rows[0]
    if r.get("status") != 22:
        raise HTTPException(status_code=400, detail="仅可重新提交已驳回的申请")
    applicant = (req.current_user or "").strip()
    if (r.get("applicant") or "").strip() != applicant:
        raise HTTPException(status_code=403, detail="只能重新提交本人的申请")

    names = [n.strip() for n in req.names if n.strip()]
    if not names:
        raise HTTPException(status_code=400, detail="姓名列表不能为空")
    amount = round(req.amount, 3)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="数量必须大于 0")
    if req.action not in ("add", "subtract"):
        raise HTTPException(status_code=400, detail="action 必须为 add 或 subtract")
    ly = (req.ly or "").strip()
    if not ly:
        raise HTTPException(status_code=400, detail="原因不能为空")
    approver = (req.approver or "").strip()
    if not approver:
        raise HTTPException(status_code=400, detail="审批人不能为空")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute_update(
        """UPDATE hxp_approval SET action=%s, amount=%s, ly=%s, names_json=%s,
           approver=%s, status=0, reject_reason=NULL, approve_time=NULL, apply_time=%s
           WHERE id=%s AND status=22 AND applicant=%s""",
        (req.action, amount, ly, json.dumps(names, ensure_ascii=False),
         approver, now_str, approval_id, applicant),
    )
    return {"success": True, "message": "已重新提交"}


@router.get("/hxp/my-requests")
async def hxp_my_requests(applicant: str = Query(..., description="申请人姓名")):
    """查询自己提交的换休票审批申请。"""
    rows = db.execute_query(
        "SELECT id, applicant, action, amount, ly, names_json, approver, status, reject_reason, apply_time, approve_time "
        "FROM hxp_approval WHERE applicant = %s ORDER BY apply_time DESC LIMIT 50",
        (applicant.strip(),),
    )
    data = []
    for r in (rows or []):
        try:
            names_list = json.loads(r.get("names_json") or "[]")
        except (json.JSONDecodeError, TypeError):
            names_list = []
        at = r.get("apply_time")
        if hasattr(at, "strftime"):
            at = at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            at = str(at or "")
        apt = r.get("approve_time")
        if hasattr(apt, "strftime"):
            apt = apt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            apt = str(apt or "")
        status_val = int(r.get("status") or 0)
        status_text = "待审批" if status_val == 0 else ("已通过" if status_val == 2 else "已驳回")
        data.append({
            "id": r["id"],
            "action": r.get("action") or "",
            "amount": float(r.get("amount") or 0),
            "ly": r.get("ly") or "",
            "names": names_list,
            "namesCount": len(names_list),
            "approver": r.get("approver") or "",
            "status": status_val,
            "statusText": status_text,
            "rejectReason": (r.get("reject_reason") or "").strip(),
            "applyTime": at,
            "approveTime": apt,
        })
    return {"success": True, "data": data}


# ==================== 部长信息简报（首页滚动信息） ====================


@router.get("/leader-briefing")
async def get_leader_briefing(
    name: str = Query(..., description="当前用户姓名"),
    days: int = Query(7, ge=1, le=30, description="最近 N 天"),
):
    """
    部长首页「重要信息审阅」：最近 N 天内审批通过的换休票获取 + 公出记录。
    仅部长可调用。
    """
    from routers.approvers import _get_user_info, _jb_match

    user = _get_user_info(name)
    if not user:
        raise HTTPException(status_code=403, detail="用户不存在")
    jb = (user.get("jb") or "").strip()
    admin1 = (_get_admin1() or "").strip()
    is_admin = bool(admin1 and (name or "").strip() == admin1)
    if not (is_admin or _jb_match(jb, "部长")):
        raise HTTPException(status_code=403, detail="仅部长可查看")

    items = []

    try:
        hxp_rows = db.execute_query(
            """SELECT h.xm, h.days, h.hxp_count, h.date_from, h.date_to,
                      h.spr, h.spr2, h.apply_time
               FROM holiday_exchange h
               WHERE h.status = 4
                 AND h.apply_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
               ORDER BY h.apply_time DESC""",
            (days,),
        )
        for r in hxp_rows:
            xm = (r.get("xm") or "").strip()
            cnt = r.get("hxp_count") or r.get("days") or 0
            cnt_f = float(cnt)
            cnt_display = int(cnt_f) if cnt_f == int(cnt_f) else f"{cnt_f:g}"
            spr = (r.get("spr") or "").strip()
            spr2 = (r.get("spr2") or "").strip()
            approvers = "、".join(filter(None, [spr, spr2]))
            d_from = str(r.get("date_from") or "")[:10]
            d_to = str(r.get("date_to") or "")[:10]
            date_range = d_from if d_from == d_to else f"{d_from}~{d_to}"
            at = str(r.get("apply_time") or "")[:10]
            at_year = at[:4] if len(at) >= 4 else ""
            items.append({
                "type": "hxp",
                "time": at,
                "name": xm,
                "year": at_year,
                "text": f"{at}，{xm}，值班获得换休票{cnt_display}张（{date_range}，{approvers}审批）",
            })
    except Exception as e:
        logger.warning(f"leader-briefing 查换休票失败: {e}")

    try:
        batch_rows = db.execute_query(
            """SELECT a.applicant, a.action, a.amount, a.ly, a.names_json,
                      a.approver, a.approve_time
               FROM hxp_approval a
               WHERE a.status = 2
                 AND a.approve_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
               ORDER BY a.approve_time DESC""",
            (days,),
        )
        for r in batch_rows:
            applicant = (r.get("applicant") or "").strip()
            action = r.get("action") or "add"
            amount = r.get("amount") or 0
            amt_f = float(amount)
            amt_display = int(amt_f) if amt_f == int(amt_f) else f"{amt_f:g}"
            ly = (r.get("ly") or "").strip()
            approver = (r.get("approver") or "").strip()
            names_list = []
            try:
                names_list = json.loads(r.get("names_json") or "[]")
            except Exception:
                pass
            names_str = "、".join(names_list[:5])
            if len(names_list) > 5:
                names_str += f"等{len(names_list)}人"
            at = r.get("approve_time")
            if hasattr(at, "strftime"):
                at = at.strftime("%Y-%m-%d")
            else:
                at = str(at or "")[:10]
            at_year = at[:4] if len(at) >= 4 else ""
            action_text = "增加" if action == "add" else "减少"
            items.append({
                "type": "hxp_batch",
                "time": at,
                "name": applicant,
                "year": at_year,
                "text": f"{at}，{applicant}为{names_str}{action_text}换休票{amt_display}张，原因：{ly}（{approver}审批）",
            })
    except Exception as e:
        logger.warning(f"leader-briefing 查换休票批量审批失败: {e}")

    try:
        trip_rows = db.execute_query(
            """SELECT g.gcr, g.gcdd, g.gcrw, g.bld, g.szr,
                      g.bldpztime, g.wpsj, g.yjcfsj
               FROM gcsqb g
               WHERE g.bldzt = 2 AND g.szrzt = 2
                 AND g.bldpztime >= DATE_SUB(NOW(), INTERVAL %s DAY)
               ORDER BY g.bldpztime DESC""",
            (days,),
        )
        for r in trip_rows:
            gcr = (r.get("gcr") or "").strip()
            gcdd = (r.get("gcdd") or "").strip()
            gcrw = (r.get("gcrw") or "").strip()
            bld = (r.get("bld") or "").strip()
            szr = (r.get("szr") or "").strip()
            approvers = "、".join(filter(None, [szr, bld]))
            reason = gcrw if gcrw else "公出"
            at = str(r.get("bldpztime") or r.get("wpsj") or "")[:10]
            at_year = at[:4] if len(at) >= 4 else ""
            items.append({
                "type": "trip",
                "time": at,
                "name": gcr,
                "year": at_year,
                "text": f"{at}，{gcr}，因{reason}去{gcdd}公出（{approvers}审批）",
            })
    except Exception as e:
        logger.warning(f"leader-briefing 查公出失败: {e}")

    items.sort(key=lambda x: x.get("time", ""), reverse=True)
    return {"success": True, "items": items}
