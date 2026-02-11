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
from utils.helpers import format_datetime_plain, normalize_datetime_for_db
import logging
import math
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(tags=["请假与加班"])

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

        dur = float(duration) if duration else 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        xiaoshi = str(round(dur * 8, 2))
        # 1天=2张，最小0.5张(0.25天)，四舍五入到0.5
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
        xiaoshi = str(round(req.duration * 8, 2))
        # 1天=2张，最小0.5张(0.25天)，四舍五入到0.5
        hxpxh = round(round(req.duration * 4) / 2, 2) if req.type in ("员工换休票", "换休") and req.duration and req.duration > 0 else 0
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
            str(req.duration), xiaoshi, now, req.approver1 or "", need_2j, spr2_val,
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


@router.get("/leave/list")
async def get_leave_list(
    name: str,
    year: Optional[int] = None,
    status: Optional[str] = Query("processing", description="processing=审核中, approved=已通过, all=全部"),
    all_years: Optional[bool] = Query(False, description="为 true 时不过滤年份，返回全部"),
):
    """
    获取本人请假记录列表
    用于 Leave.vue 的请假记录表格。全年筛选。all_years=true 时返回全部年份。
    """
    try:
        if year is None and not all_years:
            year = datetime.now().year

        if all_years:
            query = """
                SELECT id, bz, xm, qjfs, timefrom, timeto, qjtime, tian, xiaoshi, qjzt, content, spr, spr2, `2j`, bhyy
                FROM qj WHERE xm = %s
            """
            params = [name]
        else:
            query = """
                SELECT id, bz, xm, qjfs, timefrom, timeto, qjtime, tian, xiaoshi, qjzt, content, spr, spr2, `2j`, bhyy
                FROM qj WHERE xm = %s
                AND (timefrom LIKE %s OR timefromdate LIKE %s OR SUBSTR(timefrom, 1, 4) = %s)
            """
            params = [name, f"{year}%", f"{year}%", str(year)]
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
            qjzt = row.get("qjzt")
            if qjzt == 1:
                current_approver = (row.get("spr") or "").strip()
            elif qjzt == 3:
                current_approver = (row.get("spr2") or "").strip()
            else:
                current_approver = ""
            records.append({
                "id": row["id"],
                "type": row.get("qjfs") or "请假",
                "startTime": format_datetime_plain(row.get("timefrom")) or "",
                "endTime": format_datetime_plain(row.get("timeto")) or "",
                "duration": float(row.get("tian") or 0),
                "applyTime": format_datetime_plain(row.get("qjtime")) or "",
                "status": status_map.get(qjzt, "已驳回"),
                "statusClass": status_class_map.get(qjzt, "status-rejected"),
                "currentApprover": current_approver,
                "rejectReason": (row.get("bhyy") or "").strip()
            })

        return {"success": True, "data": records, "total": len(records)}
    except Exception as e:
        logger.error(f"查询请假记录失败: {str(e)}")
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


def _calc_hours(start_time: str, end_time: str, date_str: str) -> float:
    """计算加班时长(小时)，原始值（未取整）。"""
    try:
        start_str = f"{date_str} {start_time}" if len(start_time) <= 8 else start_time
        end_str = f"{date_str} {end_time}" if len(end_time) <= 8 else end_time
        start_str = start_str.replace(" ", "T")[:19]
        end_str = end_str.replace(" ", "T")[:19]
        from datetime import datetime as dt
        t1 = dt.strptime(start_str.replace("T", " "), "%Y-%m-%d %H:%M:%S")
        t2 = dt.strptime(end_str.replace("T", " "), "%Y-%m-%d %H:%M:%S")
        return (t2 - t1).total_seconds() / 3600
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
        hours = _calc_hours(st, et, req.date)
        hours = round_overtime_hours_down(hours)  # 时长最小单位 0.5 小时，向下取整后写入

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
        # 要换休票(hx=是)与要加班费(jbf)二选一：hx=是 只写 tian1/hxp，jbf 不写(0)；hx=否 写 jbf，hxp=0
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
):
    """
    获取本人加班记录列表
    用于 Overtime.vue 的加班记录表格。按月筛选。all_years=true 时返回全部年份。
    """
    try:
        if year is None and not all_years:
            year = datetime.now().year

        if all_years:
            query = """
                SELECT id, bz, xm, jb, timedate, timefrom, timeto, jiabantime, tian1, jbf, jiabanzt, content, spr, spr2, bhyy
                FROM jiaban WHERE xm = %s
            """
            params = [name]
        elif month:
            month_str = f"{year}-{month:02d}"
            query = """
                SELECT id, bz, xm, jb, timedate, timefrom, timeto, jiabantime, tian1, jbf, jiabanzt, content, spr, spr2, bhyy
                FROM jiaban WHERE xm = %s
                AND (timedate LIKE %s OR SUBSTR(timedate, 1, 7) = %s)
            """
            params = [name, f"{month_str}%", month_str]
        else:
            query = """
                SELECT id, bz, xm, jb, timedate, timefrom, timeto, jiabantime, tian1, jbf, jiabanzt, content, spr, spr2, bhyy
                FROM jiaban WHERE xm = %s
                AND (timedate LIKE %s OR SUBSTR(timedate, 1, 4) = %s)
            """
            params = [name, f"{year}%", str(year)]
        if status == "approved":
            query += " AND jiabanzt = 4"
        elif status == "processing":
            query += " AND jiabanzt IN (0, 1, 3, 5, 22)"
        query += " ORDER BY timedate DESC, timefrom DESC"
        try:
            rows = db.execute_query(query, tuple(params))
        except Exception:
            query_no_bhyy = query.replace(", bhyy", "")
            rows = db.execute_query(query_no_bhyy, tuple(params))

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
            if jiabanzt in (0, 1):
                current_approver = (row.get("spr") or "").strip()
            elif jiabanzt == 3:
                current_approver = (row.get("spr2") or "").strip()
            elif jiabanzt == 5:
                current_approver = dakaman
            else:
                current_approver = ""
            hours = row.get("jbf") or row.get("tian1") or 0
            try:
                hours = float(hours)
            except (TypeError, ValueError):
                hours = 0
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
                "level": row.get("jb") or "加班",
                "date": date_ymd,
                "startTime": tf,
                "endTime": tt,
                "hours": hours,
                "applyTime": format_datetime_plain(row.get("jiabantime")) or "",
                "status": status_map.get(jiabanzt, "已驳回"),
                "statusClass": status_class_map.get(jiabanzt, "status-rejected"),
                "currentApprover": current_approver,
                "rejectReason": (row.get("bhyy") or "").strip()
            })

        return {"success": True, "data": records, "total": len(records)}
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
    获取加班相关配置（用于“否”换休票时计算加班费）。
    返回 webconfig 表中的 zhibanfei（每小时加班费，元），若表不存在或无记录则返回默认 15。
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
