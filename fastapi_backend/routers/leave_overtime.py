# -*- coding: utf-8 -*-
"""
请假申请与加班登记 API 路由
- 申请请假: 插入 qj 表 (字段映射: bz=班组,xm=姓名,qjfs=类别,bc=班次,gx=告别方式,
  timefrom/timeto=开始/结束时间,tian=天数,xiaoshi=小时,jy=事由,smcl=书面材料,smclwj=说明材料文件,
  spr=第一审批人,2j=二级审批,spr2=第二审批人,qjzt=状态)
- 加班登记: 插入 jiaban 表
"""
from fastapi import APIRouter, HTTPException, Query, Form, File, UploadFile
from fastapi.responses import FileResponse
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
from database import db
from config import settings
from utils.helpers import format_datetime_plain, normalize_datetime_for_db, normalize_qj_tian_days
import logging
import math
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(tags=["请假与加班"])


def _safe_float(val, default: float = 0.0) -> float:
    """避免历史脏数据导致 float() 抛错进而 500"""
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

# 说明材料文件存储目录（相对于 fastapi_backend 根目录）
_BASE = Path(__file__).resolve().parent.parent
UPLOAD_LEAVE_MATERIALS = _BASE / settings.UPLOAD_DIR / "leave_materials"


def _ensure_upload_dir():
    UPLOAD_LEAVE_MATERIALS.mkdir(parents=True, exist_ok=True)


# ==================== 请假申请 ====================

class LeaveApplyRequest(BaseModel):
    """请假申请请求（JSON 方式，兼容旧客户端）"""
    department: str  # 班组 bz
    name: str  # 姓名 xm
    type: str  # 类别/请假类型 qjfs: 事假/病假/年休假等
    shift: str = "白班"  # 班次 bc
    contactMethod: str = ""  # 告别方式
    startTime: str  # 开始时间
    endTime: str  # 结束时间
    duration: float  # 时长(天) tian
    exchangeTicketNo: Optional[str] = ""  # 换休票序号
    reason: str  # 事由 jy
    material: str = ""  # 书面材料说明 smcl，选填
    approver1: str  # 第一审批人 spr
    needSecondApproval: bool = False
    approver2: Optional[str] = ""


@router.post("/leave/apply")
async def apply_leave(
    department: str = Form(...),
    name: str = Form(...),
    type: str = Form("事假"),
    shift: str = Form("白班"),
    contactMethod: str = Form(""),
    startTime: str = Form(...),
    endTime: str = Form(...),
    duration: str = Form(...),
    exchangeTicketNo: str = Form(""),
    reason: str = Form(...),
    material: str = Form(""),
    approver1: str = Form(...),
    needSecondApproval: str = Form("false"),
    approver2: str = Form(""),
    materialFile: Optional[UploadFile] = File(None),
):
    """
    申请请假 - 插入 qj 表（支持 Form + 可选文件上传）
    前端需使用 FormData 提交，Content-Type: multipart/form-data
    qjzt: 0=待审批, 1=室主任审批中, 4=已通过
    """
    try:
        need_2j_val = str(needSecondApproval).lower() in ("true", "1", "yes")
        if need_2j_val and not (approver2 or "").strip():
            raise HTTPException(status_code=400, detail="需要二级审批时请选择第二审批人")

        raw_dur = float(duration) if duration else 0
        dur = normalize_qj_tian_days(raw_dur)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        xiaoshi = str(round(dur * 8, 2))
        # 1天=2张，最小0.5张(0.25天)，四舍五入到0.5（基于已规范化的 dur）
        hxpxh = round(round(dur * 4) / 2, 2) if type in ("员工换休票", "换休") and dur > 0 else 0
        need_2j = 1 if need_2j_val and approver2 else 0

        rows = db.execute_query("SELECT lsys FROM yggl WHERE name = %s AND (COALESCE(zaizhi,0)=0) LIMIT 1", (name,))
        lsys = (rows[0]["lsys"] or "").strip() if rows else ""
        spr2_val = (approver2 or "") if need_2j else ""
        hxps_val = 0

        smcl_text = (material or "").strip() or "无"
        smclwj = ""
        # qj.timefrom/timeto 为 DATETIME(0)，写入须为 YYYY-MM-DD HH:MM:SS
        start_time_norm = normalize_datetime_for_db(startTime)
        end_time_norm = normalize_datetime_for_db(endTime)

        if materialFile and materialFile.filename:
            _ensure_upload_dir()
            ext = Path(materialFile.filename).suffix or ""
            safe_name = f"leave_{uuid.uuid4().hex[:12]}{ext}"
            save_path = UPLOAD_LEAVE_MATERIALS / safe_name
            content = await materialFile.read()
            with open(save_path, "wb") as f:
                f.write(content)
            smclwj = safe_name

        # qj.id 若为 VARCHAR(36) 主键无默认值，必须显式传入
        new_id = uuid.uuid4().hex
        sql = """
            INSERT INTO qj (id, bz, xm, qjfs, bc, gx, jy, smcl, smclwj, timefrom, timeto, timefromdate,
                tian, xiaoshi, qjtime, qjzt, spr, `2j`, spr2, content, lsys, hxpxh, hxwc, hxps)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, 0, %s)
        """
        params = (
            new_id,
            department or "",
            name or "",
            type or "事假",
            shift or "白班",
            contactMethod or "电话",
            reason or "",
            smcl_text,
            smclwj,
            start_time_norm,
            end_time_norm,
            start_time_norm[:10] if start_time_norm else "",
            str(dur),
            xiaoshi,
            now,
            approver1 or "",
            need_2j,
            spr2_val,
            reason or "",
            lsys,
            hxpxh,
            hxps_val,
        )
        last_id = db.execute_insert(sql, params)
        if last_id is None:
            raise HTTPException(status_code=500, detail="插入请假记录失败")

        return {
            "success": True,
            "message": "请假申请已提交",
            "id": new_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"申请请假失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"申请失败: {str(e)}")


@router.get("/leave/download-material/{filename}")
async def download_leave_material(filename: str):
    """下载请假说明材料文件"""
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效文件名")
    path = UPLOAD_LEAVE_MATERIALS / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, filename=filename)


@router.post("/leave/apply-json")
async def apply_leave_json(req: LeaveApplyRequest):
    """
    申请请假（JSON 方式，兼容无文件上传的客户端）
    """
    try:
        if req.needSecondApproval and not (req.approver2 or "").strip():
            raise HTTPException(status_code=400, detail="需要二级审批时请选择第二审批人")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dur = normalize_qj_tian_days(req.duration)
        xiaoshi = str(round(dur * 8, 2))
        # 1天=2张，最小0.5张(0.25天)，四舍五入到0.5（基于已规范化的 dur）
        hxpxh = round(round(dur * 4) / 2, 2) if req.type in ("员工换休票", "换休") and dur > 0 else 0
        need_2j = 1 if req.needSecondApproval and req.approver2 else 0
        rows = db.execute_query("SELECT lsys FROM yggl WHERE name = %s AND (COALESCE(zaizhi,0)=0) LIMIT 1", (req.name,))
        lsys = (rows[0]["lsys"] or "").strip() if rows else ""
        spr2_val = (req.approver2 or "") if need_2j else ""
        smcl_text = (req.material or "").strip() or "无"
        # qj.timefrom/timeto 为 DATETIME(0)，写入须为 YYYY-MM-DD HH:MM:SS
        start_time_norm = normalize_datetime_for_db(req.startTime)
        end_time_norm = normalize_datetime_for_db(req.endTime)
        new_id = uuid.uuid4().hex
        sql = """
            INSERT INTO qj (id, bz, xm, qjfs, bc, gx, jy, smcl, smclwj, timefrom, timeto, timefromdate,
                tian, xiaoshi, qjtime, qjzt, spr, `2j`, spr2, content, lsys, hxpxh, hxwc, hxps)
            VALUES (%s, %s, %s, %s, %s, %s, %s, '', %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, 0, %s)
        """
        params = (
            new_id,
            req.department or "", req.name or "", req.type or "事假", req.shift or "白班",
            req.contactMethod or "电话", req.reason or "", smcl_text,
            start_time_norm, end_time_norm, start_time_norm[:10] if start_time_norm else "",
            str(dur), xiaoshi, now, req.approver1 or "", need_2j, spr2_val,
            req.reason or "", lsys, hxpxh, 0
        )
        last_id = db.execute_insert(sql, params)
        if last_id is None:
            raise HTTPException(status_code=500, detail="插入请假记录失败")
        return {"success": True, "message": "请假申请已提交", "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"申请请假失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"申请失败: {str(e)}")


def _record_scope_xm_clause(viewer_name: str, scope: str, resource: str):
    """
    请假/加班列表：scope=self 仅本人；scope=lsys 同 lsys 全员（主任/副主任）；
    scope=all：部长/副部长/打卡管理员/系统管理员为不限制 xm（与原「全部请假记录」一致）；
    综合技术室主任/副主任为 yggl 子查询（排除部办等，与统计规则一致）。
    返回 (xm_where_sql, xm_params, meta dict)。
    """
    from routers.approvers import _get_user_info, _jb_match, is_zonghe_tech_director
    from routers.db_manager import _get_admin1

    scope = (scope or "self").strip().lower()
    if scope not in ("self", "lsys", "all"):
        raise HTTPException(status_code=400, detail="无效的 scope")
    viewer = (viewer_name or "").strip()
    if not viewer:
        raise HTTPException(status_code=400, detail="姓名不能为空")
    meta = {"canViewLsys": False, "canViewAll": False, "lsysLabel": ""}
    user = _get_user_info(viewer)
    admin1 = (_get_admin1() or "").strip()
    is_admin_user = bool(admin1 and viewer == admin1)
    # 打卡管理员 dakaman 与系统管理员同等权限查看全员
    try:
        _dk_rows = db.execute_query("SELECT dakaman FROM webconfig WHERE id = %s LIMIT 1", ("1",))
        _dakaman = (_dk_rows[0].get("dakaman") or "").strip() if _dk_rows else ""
    except Exception:
        _dakaman = ""
    is_dakaman = bool(_dakaman and viewer == _dakaman)
    jb = ""
    if user:
        jb = (user.get("jb") or "").strip()
        lsys = (user.get("lsys") or "").strip()
        meta["lsysLabel"] = lsys
        meta["canViewLsys"] = (_jb_match(jb, "主任") or _jb_match(jb, "副主任")) and bool(lsys)
    is_minister = _jb_match(jb, "部长") or _jb_match(jb, "副部长")
    zonghe_dir = bool(user and is_zonghe_tech_director(user))
    meta["canViewAll"] = is_admin_user or is_minister or zonghe_dir or is_dakaman
    if scope == "self":
        return "xm = %s", [viewer], meta
    if scope == "all":
        if not meta["canViewAll"]:
            raise HTTPException(
                status_code=403,
                detail="仅部长、副部长、综合技术室主任/副主任或系统管理员可查看全员请假记录"
                if resource == "leave"
                else "仅部长、副部长、综合技术室主任/副主任或系统管理员可查看全员加班记录",
            )
        if is_admin_user or is_minister or is_dakaman:
            return "1=1", [], meta
        clause = (
            "xm IN (SELECT y.name FROM yggl AS y WHERE COALESCE(y.zaizhi,0)=0 "
            "AND y.name IS NOT NULL AND TRIM(y.name) <> '' "
            "AND TRIM(y.lsys) <> '部办' "
            "AND RIGHT(TRIM(y.name), 1) <> '1' "
            "AND RIGHT(TRIM(y.lsys), 1) <> '1')"
        )
        return clause, [], meta
    if not meta["canViewLsys"]:
        raise HTTPException(
            status_code=403,
            detail="仅主任、副主任可查看本专业全员请假记录" if resource == "leave" else "仅主任、副主任可查看本专业全员加班记录",
        )
    lsys = (user.get("lsys") or "").strip()
    clause = (
        "xm IN (SELECT y.name FROM yggl AS y WHERE y.lsys = %s AND COALESCE(y.zaizhi,0)=0 "
        "AND y.name IS NOT NULL AND TRIM(y.name) <> '')"
    )
    return clause, [lsys], meta


@router.get("/leave/list")
async def get_leave_list(
    name: str,
    year: Optional[int] = None,
    month: Optional[int] = Query(None, ge=1, le=12, description="与 year 同时使用时按请假开始时间所在年月筛选"),
    status: Optional[str] = Query("processing", description="processing=审核中, approved=已通过, all=全部"),
    all_years: Optional[bool] = Query(False, description="为 true 时不过滤年份，返回全部"),
    scope: str = Query("self", description="self=仅本人，lsys=同属室全员，all=全员（仅综合技术室主任/副主任）"),
):
    """
    获取请假记录列表。默认仅本人；主任/副主任可选 lsys；综合技术室主任/副主任可选 all 查看全员。
    """
    try:
        if year is None and not all_years:
            year = datetime.now().year

        xm_where, xm_params, meta = _record_scope_xm_clause(name, scope, "leave")

        if all_years:
            query = f"""
                SELECT id, bz, xm, qjfs, timefrom, timeto, qjtime, tian, xiaoshi, qjzt, content, spr, spr2, `2j`, bhyy
                FROM qj WHERE {xm_where}
            """
            params = list(xm_params)
        elif month is not None:
            month_str = f"{year}-{month:02d}"
            query = f"""
                SELECT id, bz, xm, qjfs, timefrom, timeto, qjtime, tian, xiaoshi, qjzt, content, spr, spr2, `2j`, bhyy
                FROM qj WHERE {xm_where}
                AND (
                    timefrom LIKE %s OR timefromdate LIKE %s OR SUBSTR(timefrom, 1, 7) = %s
                )
            """
            params = list(xm_params) + [f"{month_str}%", f"{month_str}%", month_str]
        else:
            query = f"""
                SELECT id, bz, xm, qjfs, timefrom, timeto, qjtime, tian, xiaoshi, qjzt, content, spr, spr2, `2j`, bhyy
                FROM qj WHERE {xm_where}
                AND (timefrom LIKE %s OR timefromdate LIKE %s OR SUBSTR(timefrom, 1, 4) = %s)
            """
            params = list(xm_params) + [f"{year}%", f"{year}%", str(year)]
        if status == "approved":
            query += " AND qjzt = 4"
        elif status == "processing":
            query += " AND qjzt IN (0, 1, 3, 22)"
        query += " ORDER BY timefrom DESC"
        try:
            rows = db.execute_query(query, tuple(params))
        except Exception:
            # 兼容无 bhyy 列：用不含 bhyy 的查询
            query_no_bhyy = query.replace(", bhyy", "")
            rows = db.execute_query(query_no_bhyy, tuple(params))

        # 状态映射: 0=待审批, 1=审批中, 4=已通过, 22=已驳回
        status_map = {0: "待审批", 1: "审批中", 3: "审批中", 4: "已通过", 22: "已驳回"}
        status_class_map = {0: "status-processing", 1: "status-processing", 3: "status-processing", 4: "status-approved", 22: "status-rejected"}

        records = []
        for row in rows:
            rid = row.get("id")
            if rid is None:
                continue
            qjzt = row.get("qjzt")
            if qjzt == 1:
                current_approver = (row.get("spr") or "").strip()
            elif qjzt == 3:
                current_approver = (row.get("spr2") or "").strip()
            else:
                current_approver = ""
            records.append({
                "id": rid,
                "applicant": (row.get("xm") or "").strip(),
                "type": row.get("qjfs") or "请假",
                "startTime": format_datetime_plain(row.get("timefrom")) or "",
                "endTime": format_datetime_plain(row.get("timeto")) or "",
                "duration": _safe_float(row.get("tian"), 0.0),
                "hours": _safe_float(row.get("xiaoshi"), 0.0),
                "reason": (row.get("content") or "").strip(),
                "applyTime": format_datetime_plain(row.get("qjtime")) or "",
                "status": status_map.get(qjzt, "已驳回"),
                "statusClass": status_class_map.get(qjzt, "status-rejected"),
                "currentApprover": current_approver,
                "rejectReason": (row.get("bhyy") or "").strip()
            })

        return {
            "success": True,
            "data": records,
            "total": len(records),
            "scope": (scope or "self").strip().lower(),
            "meta": meta,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询请假记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/leave/all-records")
async def get_leave_all_records(
    name: str = Query(..., description="当前用户姓名"),
    year: Optional[int] = Query(None, description="按年份筛选，不传则全部"),
    month: Optional[int] = Query(None, description="按月份筛选，不传则全年"),
):
    """
    全部请假记录（按权限）：
    系统管理员/部长/副部长/综合技术室主任与副主任：全员；组长/主任/副主任：本科室。
    仅返回已通过(qjzt=4)的记录，按请假开始时间倒序。
    """
    from routers.approvers import _get_user_info, _jb_match, is_zonghe_tech_director
    from routers.db_manager import _get_admin1
    try:
        user = _get_user_info(name)
        if not user:
            return {"success": True, "data": [], "total": 0, "scope": "none"}
        name_stripped = (name or "").strip()
        admin1 = _get_admin1()
        # 打卡管理员同等权限
        try:
            _dk_rows = db.execute_query("SELECT dakaman FROM webconfig WHERE id = %s LIMIT 1", ("1",))
            _dakaman = (_dk_rows[0].get("dakaman") or "").strip() if _dk_rows else ""
        except Exception:
            _dakaman = ""
        is_dk = bool(_dakaman and name_stripped == _dakaman)
        if (admin1 and name_stripped == admin1) or is_dk:
            is_leader = True
            lsys = ""
        else:
            jb = (user.get("jb") or "").strip()
            lsys = (user.get("lsys") or "").strip()
            is_leader = (
                _jb_match(jb, "部长")
                or _jb_match(jb, "副部长")
                or is_zonghe_tech_director(user)
            )

        where_parts = ["qjzt = 4"]
        params = []

        if not is_leader:
            if not lsys:
                return {"success": True, "data": [], "total": 0, "scope": "dept"}
            where_parts.append("lsys = %s")
            params.append(lsys)

        if year is not None:
            if month is not None:
                month_prefix = f"{year}-{month:02d}"
                where_parts.append("(timefrom LIKE %s OR timefromdate LIKE %s)")
                params.extend([f"{month_prefix}%", f"{month_prefix}%"])
            else:
                where_parts.append("(timefrom LIKE %s OR timefromdate LIKE %s OR SUBSTR(timefrom, 1, 4) = %s)")
                params.extend([f"{year}%", f"{year}%", str(year)])

        sql = f"""
            SELECT id, lsys, xm, qjfs, timefrom, timeto, tian, xiaoshi, qjtime, qjzt, content, spr, spr2
            FROM qj WHERE {' AND '.join(where_parts)}
            ORDER BY timefrom DESC
        """
        rows = db.execute_query(sql, tuple(params))

        records = []
        for row in rows:
            rid = row.get("id")
            if rid is None:
                continue
            records.append({
                "id": rid,
                "department": (row.get("lsys") or "").strip(),
                "name": (row.get("xm") or "").strip(),
                "type": row.get("qjfs") or "请假",
                "startTime": format_datetime_plain(row.get("timefrom")) or "",
                "endTime": format_datetime_plain(row.get("timeto")) or "",
                "duration": _safe_float(row.get("tian"), 0.0),
                "hours": _safe_float(row.get("xiaoshi"), 0.0),
                "applyTime": format_datetime_plain(row.get("qjtime")) or "",
                "reason": (row.get("content") or "").strip(),
            })
        scope = "all" if is_leader else "dept"
        return {"success": True, "data": records, "total": len(records), "scope": scope}
    except Exception as e:
        logger.error(f"查询全部请假记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.delete("/leave/{item_id}")
async def delete_leave_rejected(item_id: str, name: str):
    """删除本人已驳回的请假记录（仅 qjzt=22 可删），数据库物理删除"""
    try:
        rows = db.execute_query("SELECT id, qjzt, xm FROM qj WHERE id = %s", (item_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="记录不存在")
        r = rows[0]
        if (r.get("qjzt") or 0) != 22:
            raise HTTPException(status_code=400, detail="仅可删除已驳回的请假记录")
        if (r.get("xm") or "").strip() != (name or "").strip():
            raise HTTPException(status_code=403, detail="只能删除本人的记录")
        n = db.execute_update("DELETE FROM qj WHERE id = %s AND qjzt = 22 AND xm = %s", (item_id, name.strip()))
        if n <= 0:
            raise HTTPException(status_code=500, detail="删除未生效")
        return {"success": True, "message": "已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除请假记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除失败")


# ==================== 加班登记 ====================

class OvertimeRegisterRequest(BaseModel):
    """加班登记请求"""
    department: str  # 班组 bz
    name: str  # 姓名 xm
    gender: str = "男"  # 性别 xb
    level: str  # 级别 jb: 平时加班/值班
    registerMethod: str = "补报"  # 登记方式 jiabanfs
    needExchangeTicket: str = "是"  # 是否要换休票 hx
    date: str  # 加班日期 timedate
    startTime: str  # 开始时间 timefrom
    endTime: str  # 结束时间 timeto
    content: str  # 加班内容 content
    approver: str  # 审批人 spr


def _recalc_overtime_hours_from_row(row: dict) -> float:
    """从 timefrom/timeto 重新计算加班时长，避免依赖旧算法写入的 tian1/jbf。"""
    tf = row.get("timefrom")
    tt = row.get("timeto")
    date_val = row.get("timedate")
    if not tf or not tt:
        raw = row.get("tian1")
        if raw is None or raw == "" or raw == 0:
            raw = row.get("jbf") or 0
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0
    try:
        if isinstance(tf, datetime):
            tf_str = tf.strftime("%H:%M:%S")
            date_str = tf.strftime("%Y-%m-%d")
        else:
            tf_str = str(tf).strip()
            if " " in tf_str:
                date_str, tf_str = tf_str.split(" ", 1)
            else:
                date_str = str(date_val or "")[:10]
        if isinstance(tt, datetime):
            tt_str = tt.strftime("%H:%M:%S")
        else:
            tt_str = str(tt).strip()
            if " " in tt_str:
                tt_str = tt_str.split(" ", 1)[1]
        hours = _calc_hours(tf_str, tt_str, date_str)
        return round_overtime_hours_down(hours)
    except Exception:
        raw = row.get("tian1")
        if raw is None or raw == "" or raw == 0:
            raw = row.get("jbf") or 0
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0


def _calc_hours(start_time: str, end_time: str, date_str: str) -> float:
    """计算加班时长(小时)，扣除午休 12:00-13:00 实际重叠部分，原始值（未取整）。"""
    try:
        start_str = f"{date_str} {start_time}" if len(start_time) <= 8 else start_time
        end_str = f"{date_str} {end_time}" if len(end_time) <= 8 else end_time
        start_str = start_str.replace(" ", "T")[:19]
        end_str = end_str.replace(" ", "T")[:19]
        from datetime import datetime as dt
        t1 = dt.strptime(start_str.replace("T", " "), "%Y-%m-%d %H:%M:%S")
        t2 = dt.strptime(end_str.replace("T", " "), "%Y-%m-%d %H:%M:%S")
        total_mins = (t2 - t1).total_seconds() / 60
        if total_mins <= 0:
            return 0.0
        start_mins = t1.hour * 60 + t1.minute + t1.second / 60
        end_mins = t2.hour * 60 + t2.minute + t2.second / 60
        lunch_start = 12 * 60
        lunch_end = 13 * 60
        if start_mins < lunch_end and end_mins > lunch_start:
            overlap = min(end_mins, lunch_end) - max(start_mins, lunch_start)
            total_mins = max(0, total_mins - overlap)
        return round(total_mins / 60, 4)
    except Exception:
        return 0.0


def round_overtime_hours_down(hours: float) -> float:
    """
    加班时长向下取整到 0.5 小时。
    最小单位 0.5 小时，如 3.22 -> 3.0，3.7 -> 3.5。
    """
    if hours <= 0:
        return 0.0
    return math.floor(hours * 2) / 2.0


@router.post("/overtime/register")
async def register_overtime(req: OvertimeRegisterRequest):
    """
    加班登记 - 插入 jiaban 表
    jiabanzt: 0=待审批, 4=已通过
    """
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 补齐时间为完整格式 HH:MM:SS，与 DATETIME(0) 兼容
        st = req.startTime if ":" in req.startTime else req.startTime + ":00"
        et = req.endTime if ":" in req.endTime else req.endTime + ":00"
        if st.count(":") == 1:
            st += ":00"
        if et.count(":") == 1:
            et += ":00"
        # timefrom/timeto 已改为 DATETIME(0)，写入必须为 YYYY-MM-DD HH:MM:SS，避免报错
        date_part = (req.date or "").strip()[:10]
        if len(date_part) < 10:
            date_part = datetime.now().strftime("%Y-%m-%d")
        time_from = f"{date_part} {st}"
        time_to = f"{date_part} {et}"
        # 加班开始时间不能早于 8:00，8:00 之前不计入加班
        try:
            from datetime import datetime as dt_parse
            start_dt = dt_parse.strptime(st, "%H:%M:%S")
            if start_dt.hour < 8:
                raise HTTPException(status_code=400, detail="加班开始时间不能早于 8:00，8:00 之前不计入加班")
        except HTTPException:
            raise
        except Exception:
            pass  # 非时间格式时跳过，由后续逻辑处理
        hours = _calc_hours(st, et, req.date)
        hours = round_overtime_hours_down(hours)

        # 部门 bz 为空时从 yggl 按姓名补全，避免审批详情显示空
        bz = (req.department or "").strip()
        if not bz and (req.name or "").strip():
            try:
                rows = db.execute_query("SELECT lsys FROM yggl WHERE name = %s LIMIT 1", (req.name.strip(),))
                if rows and (rows[0].get("lsys") or "").strip():
                    bz = (rows[0].get("lsys") or "").strip()
            except Exception:
                pass
        if not bz:
            bz = "未知"
        # 要换休票(hx=是)与要其他绩效激励(jbf)二选一：hx=是 只写 tian1/hxp，jbf 不写(0)；hx=否 写 jbf，hxp=0
        hx_raw = (req.needExchangeTicket or "是").strip()
        need_exchange = str(hx_raw).lower() in ("是", "1", "true", "yes")
        jbf_val = 0.0 if need_exchange else float(hours)
        hxp_val = 0.0  # 登记时为 0，审批通过且 hx=是 时再写入张数
        tian1_str = str(int(hours)) if hours == int(hours) else str(hours)

        new_id = uuid.uuid4().hex  # jiaban.id 为 VARCHAR(36)，需在插入时提供
        sql = """
            INSERT INTO jiaban (id, bz, xm, xb, jb, jiabanfs, timedate, timefrom, timeto, content, spr, jiabantime, jiabanzt, hx, tian1, jbf, hxp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s)
        """
        params = (
            new_id,
            bz,
            req.name or "",
            req.gender or "男",
            req.level or "平时加班",
            req.registerMethod or "补报",
            req.date,
            time_from,
            time_to,
            req.content or "",
            req.approver or "",
            now,
            "是" if need_exchange else "否",
            tian1_str,
            jbf_val,
            hxp_val,
        )
        db.execute_update(sql, params)

        return {
            "success": True,
            "message": "加班登记已提交",
            "id": new_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"加班登记失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"登记失败: {str(e)}")


@router.get("/overtime/list")
async def get_overtime_list(
    name: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
    status: Optional[str] = Query("processing", description="processing=审核中, approved=已通过, all=全部"),
    all_years: Optional[bool] = Query(False, description="为 true 时不过滤年份，返回全部"),
    scope: str = Query("self", description="self=仅本人，lsys=同属室全员，all=全员（仅综合技术室主任/副主任）"),
):
    """
    获取加班记录列表。默认仅本人；主任/副主任可选 lsys；综合技术室主任/副主任可选 all 查看全员。
    """
    try:
        if year is None and not all_years:
            year = datetime.now().year

        xm_where, xm_params, meta = _record_scope_xm_clause(name, scope, "overtime")

        if all_years:
            query = f"""
                SELECT id, bz, xm, jb, timedate, timefrom, timeto, jiabantime, tian1, jbf, jiabanzt, content, spr, spr2, bhyy, hx
                FROM jiaban WHERE {xm_where}
            """
            params = list(xm_params)
        elif month:
            month_str = f"{year}-{month:02d}"
            query = f"""
                SELECT id, bz, xm, jb, timedate, timefrom, timeto, jiabantime, tian1, jbf, jiabanzt, content, spr, spr2, bhyy, hx
                FROM jiaban WHERE {xm_where}
                AND (timedate LIKE %s OR SUBSTR(timedate, 1, 7) = %s)
            """
            params = list(xm_params) + [f"{month_str}%", month_str]
        else:
            query = f"""
                SELECT id, bz, xm, jb, timedate, timefrom, timeto, jiabantime, tian1, jbf, jiabanzt, content, spr, spr2, bhyy, hx
                FROM jiaban WHERE {xm_where}
                AND (timedate LIKE %s OR SUBSTR(timedate, 1, 4) = %s)
            """
            params = list(xm_params) + [f"{year}%", str(year)]
        if status == "approved":
            query += " AND jiabanzt = 4"
        elif status == "processing":
            # 含已驳回(22)，便于用户在「审批中/已驳回」中看到被驳回的申请
            query += " AND jiabanzt IN (0, 1, 3, 5, 22)"
        # status == "all" 时不加 jiabanzt 条件，返回全部状态（含已驳回）
        query += " ORDER BY timedate DESC, timefrom DESC"
        try:
            rows = db.execute_query(query, tuple(params))
        except Exception:
            query_fallback = query.replace(", bhyy, hx", "").replace(", bhyy", "")
            rows = db.execute_query(query_fallback, tuple(params))

        status_map = {0: "待审批", 1: "审批中", 3: "审批中", 5: "待打卡管理员审批", 4: "已通过", 22: "已驳回"}
        status_class_map = {0: "status-processing", 1: "status-processing", 3: "status-processing", 5: "status-processing", 4: "status-approved", 22: "status-rejected"}

        # 待打卡管理员审批时当前审批人从 webconfig.dakaman 读取
        dakaman = ""
        try:
            wc = db.execute_query("SELECT dakaman FROM webconfig WHERE id = %s LIMIT 1", ("1",))
            if wc and wc[0].get("dakaman") is not None:
                dakaman = (wc[0].get("dakaman") or "").strip()
        except Exception:
            pass

        records = []
        for row in rows:
            jiabanzt = row.get("jiabanzt")
            try:
                jiabanzt = int(jiabanzt) if jiabanzt is not None else None
            except (TypeError, ValueError):
                jiabanzt = None
            if jiabanzt in (0, 1):
                current_approver = (row.get("spr") or "").strip()
            elif jiabanzt == 3:
                current_approver = (row.get("spr2") or "").strip()
            elif jiabanzt == 5:
                current_approver = dakaman
            else:
                current_approver = ""
            hours = _recalc_overtime_hours_from_row(row)
            # 从 timefrom/timeto 提取时间部分（可能为 datetime 或 str）
            tf = row.get("timefrom") or ""
            tt = row.get("timeto") or ""
            tf = str(tf).strip()
            tt = str(tt).strip()
            if " " in tf:
                tf = tf.split(" ")[-1][:8]
            if " " in tt:
                tt = tt.split(" ")[-1][:8]

            # date 为加班日期(timedate)，统一 YYYY-MM-DD，供记录页筛选与首页跳转定位
            _timedate = row.get("timedate")
            date_ymd = (format_datetime_plain(_timedate) or "")[:10] if _timedate else ""
            records.append({
                "id": row["id"],
                "applicant": (row.get("xm") or "").strip(),
                "level": row.get("jb") or "加班",
                "date": date_ymd,
                "startTime": tf,
                "endTime": tt,
                "hours": hours,
                "applyTime": format_datetime_plain(row.get("jiabantime")) or "",
                "status": status_map.get(jiabanzt, "已驳回"),
                "statusClass": status_class_map.get(jiabanzt, "status-rejected"),
                "currentApprover": current_approver,
                "rejectReason": (row.get("bhyy") or "").strip(),
                "content": (row.get("content") or "").strip(),
                "hx": (row.get("hx") or "否").strip(),
            })

        return {
            "success": True,
            "data": records,
            "total": len(records),
            "scope": (scope or "self").strip().lower(),
            "meta": meta,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询加班记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.delete("/overtime/{item_id}")
async def delete_overtime_rejected(item_id: str, name: str):
    """删除本人已驳回的加班记录（仅 jiabanzt=22 可删），数据库物理删除"""
    try:
        rows = db.execute_query("SELECT id, jiabanzt, xm FROM jiaban WHERE id = %s", (item_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="记录不存在")
        r = rows[0]
        if (r.get("jiabanzt") or 0) != 22:
            raise HTTPException(status_code=400, detail="仅可删除已驳回的加班记录")
        if (r.get("xm") or "").strip() != (name or "").strip():
            raise HTTPException(status_code=403, detail="只能删除本人的记录")
        n = db.execute_update("DELETE FROM jiaban WHERE id = %s AND jiabanzt = 22 AND xm = %s", (item_id, name.strip()))
        if n <= 0:
            raise HTTPException(status_code=500, detail="删除未生效")
        return {"success": True, "message": "已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除加班记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除失败")


@router.get("/overtime/webconfig")
async def get_overtime_webconfig():
    """
    获取加班相关配置（用于“否”换休票时计算其他绩效激励）。
    返回 webconfig 表中的 zhibanfei（每小时其他绩效激励，元），若表不存在或无记录则返回默认 15。
    """
    try:
        rows = db.execute_query("SELECT zhibanfei FROM webconfig WHERE id = 1 LIMIT 1")
        if rows and rows[0].get("zhibanfei") is not None:
            try:
                val = float(rows[0]["zhibanfei"])
                return {"success": True, "zhibanfei": val}
            except (TypeError, ValueError):
                pass
    except Exception as e:
        logger.debug(f"webconfig 表不可用: {e}")
    return {"success": True, "zhibanfei": 15}
