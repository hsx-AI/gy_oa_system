# -*- coding: utf-8 -*-
"""
打卡异常申请 API
=================
业务背景:
  考勤页"智能建议"识别到某天某时段缺勤时，员工可在该建议旁发起"打卡异常申请"。
  审批流程:
    1) 一级审批: 同 lsys 的 主任/副主任/班组长（dropdown 选择）
    2) 二级审批: 经理/副经理（即数据库 jb=部长/副部长，dropdown 选择）
    二级通过后:
      - 自动将该时段写入该员工的市内公出 (gcsqb), bldzt/szrzt=2 已通过
      - 给 webconfig.dakaman 推一条待"已读确认"的待办

字段含义参见 _ensure_table()。
"""
from fastapi import APIRouter, HTTPException, Query, Form, File, UploadFile
from fastapi.responses import FileResponse
from typing import Optional, List
from datetime import datetime
from pathlib import Path
from database import db
from config import settings
from routers.approvers import (
    _jb_match,
    _jb_sql_conditions,
    _get_user_info,
)
from routers.db_manager import _get_admin1
from routers.holiday import _get_dakaman
import logging
import os
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attendance-exception", tags=["打卡异常申请"])

_BASE = Path(__file__).resolve().parent.parent
UPLOAD_KQYC_DIR = _BASE / settings.UPLOAD_DIR / "kqyc_attachments"

ALLOWED_EXTENSIONS = {
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".pdf", ".txt", ".csv",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    ".zip", ".rar", ".7z",
    ".odt", ".ods", ".odp", ".wps", ".et",
}

REASON_TYPES = {"忘记刷脸", "错误刷脸", "24:00之后离厂", "打卡机器异常"}


def _ensure_upload_dir():
    UPLOAD_KQYC_DIR.mkdir(parents=True, exist_ok=True)


def _init_table():
    """首次调用建表（若不存在）。
    数据状态机:
        first_status / second_status: 0=待审批 1=通过 2=驳回
        审批顺序: first 先， first=1 后 second 才可审批; 任一环节驳回则整单驳回
        processed_to_trip: 0=未处理为公出 1=已处理（二级通过后由后端自动写入）
        dakaman_confirmed: 0=dakaman 未读确认 1=已确认
    """
    sql = """
    CREATE TABLE IF NOT EXISTS attendance_exception (
        id INT AUTO_INCREMENT PRIMARY KEY,
        applicant VARCHAR(50) NOT NULL COMMENT '申请人姓名',
        department VARCHAR(100) DEFAULT '' COMMENT '申请人科室(lsys)',
        attendance_date DATE NOT NULL COMMENT '异常日期',
        time_from TIME NOT NULL COMMENT '异常时段-开始',
        time_to TIME NOT NULL COMMENT '异常时段-结束',
        reason_type VARCHAR(50) NOT NULL DEFAULT '' COMMENT '事由类型',
        description TEXT NOT NULL COMMENT '情况说明',
        attachment VARCHAR(500) NOT NULL DEFAULT '' COMMENT '附件存储名',
        attachment_original VARCHAR(500) NOT NULL DEFAULT '' COMMENT '附件原始文件名',
        first_approver VARCHAR(50) NOT NULL DEFAULT '' COMMENT '一级审批人(主任/副主任/班组长)',
        second_approver VARCHAR(50) NOT NULL DEFAULT '' COMMENT '二级审批人(经理/副经理)',
        first_status TINYINT NOT NULL DEFAULT 0 COMMENT '一级状态 0=待 1=通过 2=驳回',
        second_status TINYINT NOT NULL DEFAULT 0 COMMENT '二级状态 0=待 1=通过 2=驳回',
        first_approve_time DATETIME NULL,
        second_approve_time DATETIME NULL,
        reject_reason VARCHAR(500) NOT NULL DEFAULT '',
        processed_to_trip TINYINT NOT NULL DEFAULT 0 COMMENT '0=未处理 1=已写入公出',
        processed_at DATETIME NULL,
        gcsqb_id VARCHAR(36) NOT NULL DEFAULT '' COMMENT '写入公出表的记录ID',
        dakaman_confirmed TINYINT NOT NULL DEFAULT 0 COMMENT '0=待读确认 1=已确认',
        dakaman_confirmed_by VARCHAR(50) NOT NULL DEFAULT '',
        dakaman_confirmed_at DATETIME NULL,
        apply_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_applicant (applicant),
        INDEX idx_department (department),
        INDEX idx_first_approver (first_approver),
        INDEX idx_second_approver (second_approver),
        INDEX idx_status (first_status, second_status),
        INDEX idx_date (attendance_date),
        INDEX idx_dakaman (dakaman_confirmed)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='打卡异常申请表';
    """
    try:
        db.execute_update(sql)
        logger.info("attendance_exception 表已就绪")
    except Exception as e:
        logger.warning("attendance_exception 建表跳过（可能已存在）: %s", e)


_table_ready = False


def _ensure_table():
    global _table_ready
    if not _table_ready:
        _init_table()
        _table_ready = True


# ==================== 工具函数 ====================

def _row_overall_status(first_status: int, second_status: int, processed_to_trip: int = 0) -> tuple:
    """根据一级、二级状态返回 (status_text, status_class)"""
    fs = int(first_status or 0)
    ss = int(second_status or 0)
    if fs == 2 or ss == 2:
        return "已驳回", "status-rejected"
    if fs == 1 and ss == 1:
        if int(processed_to_trip or 0) == 1:
            return "已通过", "status-approved"
        return "已通过(待入账)", "status-approved"
    if fs == 1 and ss == 0:
        return "一级已通过 待二级审批", "status-processing"
    return "待一级审批", "status-processing"


def _fmt_dt(d) -> str:
    if d is None:
        return ""
    if hasattr(d, "strftime"):
        return d.strftime("%Y-%m-%d %H:%M:%S")
    return str(d)[:19]


def _fmt_date(d) -> str:
    if d is None:
        return ""
    if hasattr(d, "strftime"):
        return d.strftime("%Y-%m-%d")
    return str(d)[:10]


def _fmt_time(t) -> str:
    if t is None:
        return ""
    if hasattr(t, "strftime"):
        return t.strftime("%H:%M:%S")
    s = str(t)
    # MySQL TIME 字段可能返回 timedelta 字符串
    if ":" in s:
        return s.split(".")[0]
    return s


def _attach_display_fields(row: dict) -> dict:
    fs = int(row.get("first_status") or 0)
    ss = int(row.get("second_status") or 0)
    pt = int(row.get("processed_to_trip") or 0)
    text, cls = _row_overall_status(fs, ss, pt)
    row["status_text"] = text
    row["status_class"] = cls
    row["attendance_date"] = _fmt_date(row.get("attendance_date"))
    row["time_from"] = _fmt_time(row.get("time_from"))
    row["time_to"] = _fmt_time(row.get("time_to"))
    row["apply_time"] = _fmt_dt(row.get("apply_time"))
    row["first_approve_time"] = _fmt_dt(row.get("first_approve_time"))
    row["second_approve_time"] = _fmt_dt(row.get("second_approve_time"))
    row["processed_at"] = _fmt_dt(row.get("processed_at"))
    row["dakaman_confirmed_at"] = _fmt_dt(row.get("dakaman_confirmed_at"))
    return row


def _is_admin1_or_dakaman(name: str) -> bool:
    n = (name or "").strip()
    if not n:
        return False
    admin1 = (_get_admin1() or "").strip()
    dakaman = (_get_dakaman() or "").strip()
    return (admin1 and n == admin1) or (dakaman and n == dakaman)


def _active_dept_deputy_directors(lsys: str, exclude_name: str = "") -> list:
    lsys = (lsys or "").strip()
    if not lsys:
        return []
    fzr_cond, fzr_p = _jb_sql_conditions("副主任")
    rows = db.execute_query(
        f"""
        SELECT name, jb, lsys
        FROM yggl
        WHERE lsys = %s
          AND {fzr_cond}
          AND name IS NOT NULL AND name != ''
          AND name != %s
          AND (COALESCE(zaizhi,0)=0)
        ORDER BY jb, name
        """,
        (lsys,) + fzr_p + ((exclude_name or "").strip(),),
    )
    return rows or []


def _active_dept_first_approvers(lsys: str, exclude_name: str = "") -> list:
    lsys = (lsys or "").strip()
    if not lsys:
        return []
    zz_cond, zz_p = _jb_sql_conditions("组长")
    zr_cond, zr_p = _jb_sql_conditions("主任")
    fzr_cond, fzr_p = _jb_sql_conditions("副主任")
    cond = f"({zz_cond[1:-1]} OR {zr_cond[1:-1]} OR {fzr_cond[1:-1]})"
    rows = db.execute_query(
        f"""
        SELECT name, jb, lsys
        FROM yggl
        WHERE lsys = %s
          AND {cond}
          AND name IS NOT NULL AND name != ''
          AND name != %s
          AND (COALESCE(zaizhi,0)=0)
        ORDER BY jb, name
        """,
        (lsys,) + zz_p + zr_p + fzr_p + ((exclude_name or "").strip(),),
    )
    return rows or []


def _can_skip_first_approval(user: dict, applicant_name: str = "") -> bool:
    """主任无副主任、经理/副经理无科室一级审批人时，打卡异常申请跳过一级审批。"""
    if not user:
        return False
    jb = (user.get("jb") or "").strip()
    lsys = (user.get("lsys") or "").strip()
    name = (applicant_name or user.get("name") or "").strip()
    is_director = _jb_match(jb, "主任") and not _jb_match(jb, "副主任")
    if is_director:
        return len(_active_dept_deputy_directors(lsys, name)) == 0
    if _jb_match(jb, "部长") or _jb_match(jb, "副部长"):
        return len(_active_dept_first_approvers(lsys, name)) == 0
    return False


# ==================== 审批人列表 ====================

@router.get("/approvers")
def get_kqyc_approvers(
    name: str = Query(..., description="申请人姓名"),
    level: str = Query("first", description="first=一级(同室主任/副主任/班组长) second=二级(经理/副经理)"),
):
    """获取打卡异常申请可选审批人列表"""
    user = _get_user_info(name)
    if not user:
        return {"success": True, "approvers": [], "message": "未在 yggl 中找到该员工"}
    lsys = (user.get("lsys") or "").strip()

    level = (level or "first").lower().strip()
    if level == "second":
        bz_cond, bz_p = _jb_sql_conditions("部长")
        fbz_cond, fbz_p = _jb_sql_conditions("副部长")
        cond = f"({bz_cond[1:-1]} OR {fbz_cond[1:-1]})"
        rows = db.execute_query(
            f"SELECT name, jb, lsys FROM yggl WHERE {cond} AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) ORDER BY jb, name",
            bz_p + fbz_p,
        )
    else:
        # 一级: 同 lsys 的 主任/副主任/班组长（排除本人）
        if not lsys:
            return {
                "success": True,
                "level": level,
                "approvers": [],
                "skip_first_approval": _can_skip_first_approval(user, name),
            }
        skip_first_approval = _can_skip_first_approval(user, name)
        jb = (user.get("jb") or "").strip()
        if _jb_match(jb, "主任") and not _jb_match(jb, "副主任"):
            # 主任的一级审批仅允许同科室副主任；若无副主任则由提交接口跳过一级审批。
            rows = [] if skip_first_approval else _active_dept_deputy_directors(lsys, name)
        else:
            rows = _active_dept_first_approvers(lsys, name)

    seen = set()
    approvers = []
    for r in rows:
        nm = (r.get("name") or "").strip()
        if not nm or nm in seen:
            continue
        seen.add(nm)
        jb = (r.get("jb") or "").strip()
        approvers.append({"name": nm, "jb": jb, "lsys": r.get("lsys") or "", "label": f"{nm}（{jb}）"})

    return {
        "success": True,
        "level": level,
        "approvers": approvers,
        "skip_first_approval": bool(level != "second" and _can_skip_first_approval(user, name)),
    }


# ==================== 提交申请 ====================

@router.post("/apply")
async def submit_kqyc_apply(
    applicant: str = Form(...),
    department: str = Form(""),
    attendance_date: str = Form(...),
    time_from: str = Form(...),
    time_to: str = Form(...),
    reason_type: str = Form(...),
    description: str = Form(...),
    first_approver: str = Form(""),
    second_approver: str = Form(...),
    attachment: UploadFile = File(...),
):
    """提交打卡异常申请（FormData，含必传附件）"""
    _ensure_table()
    _ensure_upload_dir()

    applicant = (applicant or "").strip()
    description = (description or "").strip()
    first_approver = (first_approver or "").strip()
    second_approver = (second_approver or "").strip()
    reason_type = (reason_type or "").strip()
    department = (department or "").strip()
    attendance_date = (attendance_date or "").strip()
    time_from = (time_from or "").strip()
    time_to = (time_to or "").strip()

    if not applicant:
        raise HTTPException(status_code=400, detail="申请人不能为空")
    if not description:
        raise HTTPException(status_code=400, detail="情况说明为必填项")
    if not attachment or not attachment.filename:
        raise HTTPException(status_code=400, detail="佐证材料附件为必传项")
    if reason_type and reason_type not in REASON_TYPES:
        raise HTTPException(status_code=400, detail=f"事由必须为以下之一: {'、'.join(REASON_TYPES)}")
    if not second_approver:
        raise HTTPException(status_code=400, detail="请选择二级审批人(经理/副经理)")
    if first_approver and first_approver == second_approver:
        raise HTTPException(status_code=400, detail="一级与二级审批人不能为同一人")

    # 时间合法性
    try:
        d = datetime.strptime(attendance_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="异常日期格式应为 YYYY-MM-DD")
    # 兼容 HH:MM / HH:MM:SS
    def _norm_time(t: str) -> str:
        parts = t.split(":")
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="时段格式应为 HH:MM:SS")
        if len(parts) == 2:
            parts.append("00")
        return ":".join(p.zfill(2) for p in parts[:3])

    tf = _norm_time(time_from)
    tt = _norm_time(time_to)
    if tt <= tf:
        raise HTTPException(status_code=400, detail="时段结束时间需晚于开始时间")

    # 校验申请人确实存在；自动补齐 department(lsys) 字段
    user = _get_user_info(applicant)
    if not user:
        raise HTTPException(status_code=400, detail="未在 yggl 中找到该员工")
    if not department:
        department = (user.get("lsys") or "").strip()
    skip_first_approval = _can_skip_first_approval(user, applicant)
    if not first_approver and not skip_first_approval:
        raise HTTPException(status_code=400, detail="请选择一级审批人(主任/副主任/班组长)")
    applicant_jb = (user.get("jb") or "").strip()
    if (
        first_approver
        and _jb_match(applicant_jb, "主任")
        and not _jb_match(applicant_jb, "副主任")
    ):
        deputy_names = {
            (r.get("name") or "").strip()
            for r in _active_dept_deputy_directors((user.get("lsys") or "").strip(), applicant)
        }
        if first_approver not in deputy_names:
            raise HTTPException(status_code=400, detail="主任的一级审批人必须为本科室副主任")

    # 校验审批人在 yggl 中存在
    for nm in (first_approver, second_approver):
        if not nm:
            continue
        u = _get_user_info(nm)
        if not u:
            raise HTTPException(status_code=400, detail=f"审批人 {nm} 不存在或已离职")

    # 保存附件
    original_name = attachment.filename
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式 {ext}，请上传 Word/Excel/PPT/PDF/图片/压缩包等常用办公文件",
        )
    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_KQYC_DIR / stored_name
    try:
        content = await attachment.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error("打卡异常附件保存失败: %s", e)
        raise HTTPException(status_code=500, detail="附件保存失败，请重试")

    sql = """
        INSERT INTO attendance_exception
            (applicant, department, attendance_date, time_from, time_to,
             reason_type, description, attachment, attachment_original,
             first_approver, second_approver, first_status, second_status, first_approve_time, apply_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, NOW())
    """
    first_status = 1 if skip_first_approval and not first_approver else 0
    first_approve_time = datetime.now() if first_status == 1 else None
    new_id = db.execute_insert(
        sql,
        (
            applicant, department, attendance_date, tf, tt,
            reason_type, description, stored_name, original_name,
            first_approver, second_approver, first_status, first_approve_time,
        ),
    )
    if new_id is None:
        raise HTTPException(status_code=500, detail="申请提交失败，请重试")
    return {"success": True, "message": "打卡异常申请已提交", "id": new_id}


# ==================== 待审批列表 ====================

@router.get("/pending")
def get_pending_kqyc(approver: str = Query(..., description="审批人姓名")):
    """获取审批人的待审批列表（自动区分一级/二级）"""
    _ensure_table()
    approver = (approver or "").strip()
    if not approver:
        return {"success": True, "data": [], "total": 0}
    sql = """
        SELECT *,
               CASE WHEN first_approver = %s AND first_status = 0 THEN 'first'
                    WHEN second_approver = %s AND first_status = 1 AND second_status = 0 THEN 'second'
                    ELSE '' END AS pending_for
        FROM attendance_exception
        WHERE first_status != 2 AND second_status != 2
          AND (
              (first_approver = %s AND first_status = 0)
              OR (second_approver = %s AND first_status = 1 AND second_status = 0)
          )
        ORDER BY apply_time DESC
    """
    rows = db.execute_query(sql, (approver, approver, approver, approver))
    for r in rows:
        _attach_display_fields(r)
    return {"success": True, "data": rows, "total": len(rows)}


# ==================== 审批操作 ====================

@router.post("/approve")
def approve_kqyc(
    id: int = Form(...),
    approver: str = Form(...),
    action: str = Form(...),
    reject_reason: str = Form(""),
):
    """审批: action=approve/reject。审批人需匹配当前节点。
    二级通过后:
        - 写入市内公出 gcsqb（bldzt=2, szrzt=2）
        - 标记 processed_to_trip=1，dakaman 通过列表查询会看到"已读确认"待办
    """
    _ensure_table()
    action = (action or "").strip().lower()
    approver = (approver or "").strip()
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="无效操作")
    if not approver:
        raise HTTPException(status_code=400, detail="审批人不能为空")

    rows = db.execute_query(
        "SELECT * FROM attendance_exception WHERE id = %s LIMIT 1",
        (id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="申请记录不存在")
    rec = rows[0]
    fs = int(rec.get("first_status") or 0)
    ss = int(rec.get("second_status") or 0)
    first_appr = (rec.get("first_approver") or "").strip()
    second_appr = (rec.get("second_approver") or "").strip()

    # 已驳回/已结束
    if fs == 2 or ss == 2:
        raise HTTPException(status_code=400, detail="该申请已驳回")
    if fs == 1 and ss == 1:
        raise HTTPException(status_code=400, detail="该申请已审批完成")

    # 当前节点判定
    if fs == 0:
        if approver != first_appr:
            raise HTTPException(status_code=403, detail="您不是当前节点的一级审批人")
        node = "first"
    else:
        if approver != second_appr:
            raise HTTPException(status_code=403, detail="您不是当前节点的二级审批人")
        node = "second"

    if action == "reject":
        if not (reject_reason or "").strip():
            raise HTTPException(status_code=400, detail="驳回时必须填写驳回原因")
        col_status = "first_status" if node == "first" else "second_status"
        col_time = "first_approve_time" if node == "first" else "second_approve_time"
        sql_u = f"UPDATE attendance_exception SET {col_status}=2, {col_time}=NOW(), reject_reason=%s WHERE id=%s"
        affected = db.execute_update(sql_u, (reject_reason.strip(), id))
        if affected <= 0:
            raise HTTPException(status_code=500, detail="操作失败，请重试")
        return {"success": True, "message": "已驳回"}

    # approve
    if node == "first":
        affected = db.execute_update(
            "UPDATE attendance_exception SET first_status=1, first_approve_time=NOW() WHERE id=%s AND first_status=0",
            (id,),
        )
        if affected <= 0:
            raise HTTPException(status_code=500, detail="操作失败，请重试")
        return {"success": True, "message": "一级审批已通过，等待二级审批"}

    # second approve
    affected = db.execute_update(
        "UPDATE attendance_exception SET second_status=1, second_approve_time=NOW() WHERE id=%s AND first_status=1 AND second_status=0",
        (id,),
    )
    if affected <= 0:
        raise HTTPException(status_code=500, detail="操作失败，请重试")

    # 写入市内公出（gcsqb），bldzt/szrzt=2 已通过，且该流程已明确了实际时段，
    # 因此直接标记返回登记完成，避免再产生“公出返回登记”待办。
    try:
        rid = uuid.uuid4().hex
        att_date = _fmt_date(rec.get("attendance_date"))
        tf = _fmt_time(rec.get("time_from"))
        tt = _fmt_time(rec.get("time_to"))
        if att_date and tf and tt:
            yjcfsj = f"{att_date} {tf}"
            yjfhsj = f"{att_date} {tt}"
        else:
            yjcfsj = None
            yjfhsj = None
        gcrw = f"由打卡异常申请处理为公出。事由: {rec.get('reason_type') or '—'}; 说明: {(rec.get('description') or '')[:200]}"
        sql_ins = """
            INSERT INTO gcsqb (id, gclx, wpdw, gcr, gzh, gcdw, lxdh, wpsj, yjfhsj, yjcfsj, xmmc,
                tzdbh, bcgczrs, gcdd, qkje, gcrw, szr, bld, gcsj, sjfhtime, bldzt, szrzt, fhdj_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params_ins = (
            rid,
            "市内公出",
            "",  # wpdw
            rec.get("applicant") or "",
            "无",
            rec.get("department") or "",
            "",
            None,
            yjfhsj,
            yjcfsj,
            "无",
            "",
            "1",
            "市内",
            "无",
            gcrw,
            "",  # 室主任，省略
            approver,  # 二级审批人作为部领导（bld）
            yjcfsj,  # 实际出发时间
            yjfhsj,  # 实际返回时间
            2,  # bldzt 已通过
            2,  # szrzt 已通过
            1,  # fhdj_status 已返回登记
        )
        ins_ok = db.execute_update(sql_ins, params_ins)
        if ins_ok > 0:
            db.execute_update(
                "UPDATE attendance_exception SET processed_to_trip=1, processed_at=NOW(), gcsqb_id=%s WHERE id=%s",
                (rid, id),
            )
        else:
            logger.warning("二级审批通过但写入公出失败 id=%s", id)
    except Exception as e:
        logger.error("打卡异常二级审批后写入公出失败 id=%s: %s", id, e)

    return {"success": True, "message": "二级审批已通过，已自动处理为市内公出"}


# ==================== 打卡管理员"已读确认"待办 ====================

@router.get("/pending-dakaman")
def list_dakaman_pending(name: str = Query(..., description="当前用户姓名（应为 dakaman）")):
    """打卡管理员待"已读确认"列表（仅 dakaman 可见有数据，其余返回空）"""
    _ensure_table()
    n = (name or "").strip()
    dakaman = (_get_dakaman() or "").strip()
    admin1 = (_get_admin1() or "").strip()
    if not n or (n != dakaman and n != admin1):
        return {"success": True, "data": [], "total": 0}
    sql = """
        SELECT * FROM attendance_exception
        WHERE first_status=1 AND second_status=1 AND processed_to_trip=1
          AND dakaman_confirmed=0
        ORDER BY second_approve_time DESC
    """
    rows = db.execute_query(sql)
    for r in rows:
        _attach_display_fields(r)
    return {"success": True, "data": rows, "total": len(rows)}


@router.post("/dakaman-confirm")
def dakaman_confirm(
    id: int = Form(...),
    current_user: str = Form(...),
):
    """打卡管理员将某条记录标记为"已读确认"。"""
    _ensure_table()
    n = (current_user or "").strip()
    dakaman = (_get_dakaman() or "").strip()
    admin1 = (_get_admin1() or "").strip()
    if not n or (n != dakaman and n != admin1):
        raise HTTPException(status_code=403, detail="仅打卡管理员或系统管理员可标记已读确认")
    rows = db.execute_query(
        "SELECT id, first_status, second_status, dakaman_confirmed FROM attendance_exception WHERE id=%s LIMIT 1",
        (id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    rec = rows[0]
    if not (int(rec.get("first_status") or 0) == 1 and int(rec.get("second_status") or 0) == 1):
        raise HTTPException(status_code=400, detail="仅二级审批通过后的记录可确认")
    if int(rec.get("dakaman_confirmed") or 0) == 1:
        return {"success": True, "message": "已是已确认状态"}
    affected = db.execute_update(
        "UPDATE attendance_exception SET dakaman_confirmed=1, dakaman_confirmed_by=%s, dakaman_confirmed_at=NOW() WHERE id=%s",
        (n, id),
    )
    if affected <= 0:
        raise HTTPException(status_code=500, detail="操作失败，请重试")
    return {"success": True, "message": "已确认"}


# ==================== 查询记录 ====================

@router.get("/records")
def list_kqyc_records(
    current_user: str = Query(..., description="当前用户姓名（用于权限判断）"),
    year: Optional[int] = Query(None, description="年份过滤"),
    month: Optional[int] = Query(None, description="月份过滤"),
    status: str = Query("all", description="all/pending/approved/rejected"),
    keyword: str = Query("", description="姓名/事由/说明关键字"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    """根据当前用户权限范围返回打卡异常申请记录。
    权限:
        - admin1 / dakaman: 看全部
        - jb=部长/副部长(经理/副经理): 看全部（部门内）
        - jb=主任/副主任/班组长: 看同 lsys 下所有员工
        - 其他员工: 仅看自己
    """
    _ensure_table()
    cu = (current_user or "").strip()
    if not cu:
        raise HTTPException(status_code=400, detail="缺少当前用户")
    user = _get_user_info(cu)
    if not user:
        return {"success": True, "data": [], "total": 0, "scope": "none"}

    where_parts = ["1=1"]
    params: list = []

    # 权限范围
    scope = "self"
    jb = (user.get("jb") or "").strip()
    lsys = (user.get("lsys") or "").strip()
    if _is_admin1_or_dakaman(cu):
        scope = "all"
    elif _jb_match(jb, "部长") or _jb_match(jb, "副部长"):
        scope = "all"
    elif _jb_match(jb, "主任") or _jb_match(jb, "副主任") or _jb_match(jb, "组长"):
        scope = "lsys"
    else:
        scope = "self"

    if scope == "self":
        where_parts.append("applicant = %s")
        params.append(cu)
    elif scope == "lsys":
        if lsys:
            where_parts.append("department = %s")
            params.append(lsys)
        else:
            where_parts.append("applicant = %s")
            params.append(cu)
    # scope=='all': no extra where

    if year:
        where_parts.append("YEAR(attendance_date) = %s")
        params.append(int(year))
    if month:
        where_parts.append("MONTH(attendance_date) = %s")
        params.append(int(month))

    if status == "pending":
        where_parts.append("first_status != 2 AND second_status != 2 AND NOT (first_status=1 AND second_status=1)")
    elif status == "approved":
        where_parts.append("first_status=1 AND second_status=1")
    elif status == "rejected":
        where_parts.append("(first_status=2 OR second_status=2)")

    if (keyword or "").strip():
        kw = f"%{keyword.strip()}%"
        where_parts.append("(applicant LIKE %s OR description LIKE %s OR reason_type LIKE %s)")
        params.extend([kw, kw, kw])

    where_clause = " AND ".join(where_parts)
    count_sql = f"SELECT COUNT(*) AS cnt FROM attendance_exception WHERE {where_clause}"
    total = db.execute_scalar(count_sql, tuple(params)) or 0

    offset = (page - 1) * page_size
    data_sql = (
        f"SELECT * FROM attendance_exception WHERE {where_clause} "
        f"ORDER BY attendance_date DESC, apply_time DESC LIMIT %s OFFSET %s"
    )
    rows = db.execute_query(data_sql, tuple(params) + (page_size, offset))
    for r in rows:
        _attach_display_fields(r)
    return {
        "success": True,
        "data": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "scope": scope,
    }


# ==================== 我的申请 ====================

@router.get("/my-applications")
def my_kqyc_applications(name: str = Query(..., description="申请人姓名")):
    """获取指定用户的全部打卡异常申请"""
    _ensure_table()
    rows = db.execute_query(
        "SELECT * FROM attendance_exception WHERE applicant=%s ORDER BY apply_time DESC",
        ((name or "").strip(),),
    )
    for r in rows:
        _attach_display_fields(r)
    return {"success": True, "data": rows, "total": len(rows)}


# ==================== 附件下载 ====================

@router.get("/attachment")
def download_kqyc_attachment(filename: str = Query(..., description="存储文件名")):
    """下载打卡异常申请附件"""
    _ensure_upload_dir()
    file_path = UPLOAD_KQYC_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="附件不存在")
    original_sql = "SELECT attachment_original FROM attendance_exception WHERE attachment=%s LIMIT 1"
    rows = db.execute_query(original_sql, (filename,))
    original_name = rows[0]["attachment_original"] if rows else filename
    return FileResponse(
        path=str(file_path),
        filename=original_name,
        media_type="application/octet-stream",
    )
