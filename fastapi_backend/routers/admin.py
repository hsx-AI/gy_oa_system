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
from io import BytesIO
from datetime import datetime
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


def _get_admin_scope(name: str) -> Optional[Dict[str, Any]]:
    """
    获取当前用户的管理权限范围。
    返回: None=无权限; {"role": "full", "lsys": None}=部长/副部长/人事管理员(admin2)可管全部;
          {"role": "dept", "lsys": "科室名"}=主任仅可管本室。
    """
    if not (name or "").strip():
        return None
    name_stripped = name.strip()
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
    if jb == "部长" or jb.startswith("部长") or jb == "副部长" or jb.startswith("副部长"):
        return {"role": "full", "lsys": None}
    # 主任与副主任权限一致：仅可管本室
    if jb == "主任" or (jb and jb.startswith("主任")):
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
            "AND RIGHT(TRIM(lsys), 1) != '1' ORDER BY lsys"
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
