# -*- coding: utf-8 -*-
"""
部门用印申请 API
- 任何人可发起用印申请，选择经理/副经理审批（1级审批）
- 审批通过后即可用印
- 全员可查看用印记录（不做鉴权）
"""
from fastapi import APIRouter, HTTPException, Query, Form, File, UploadFile
from fastapi.responses import FileResponse
from database import db
from config import settings
from pathlib import Path
import logging
import uuid
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seal", tags=["部门用印申请"])

_BASE = Path(__file__).resolve().parent.parent
UPLOAD_SEAL_DIR = _BASE / settings.UPLOAD_DIR / "seal_attachments"

ALLOWED_EXTENSIONS = {
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".pdf", ".txt", ".csv",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    ".zip", ".rar", ".7z",
    ".odt", ".ods", ".odp", ".wps", ".et",
}


def _ensure_upload_dir():
    UPLOAD_SEAL_DIR.mkdir(parents=True, exist_ok=True)


def _init_table():
    """首次调用时自动建表（如果不存在）"""
    sql = """
    CREATE TABLE IF NOT EXISTS seal_apply (
        id INT AUTO_INCREMENT PRIMARY KEY,
        applicant VARCHAR(50) NOT NULL COMMENT '申请人姓名',
        department VARCHAR(100) DEFAULT '' COMMENT '申请人科室(lsys)',
        seal_type VARCHAR(100) DEFAULT '' COMMENT '用印类型',
        reason TEXT COMMENT '用印事由',
        attachment VARCHAR(500) DEFAULT '' COMMENT '附件文件名(存储名)',
        attachment_original VARCHAR(500) DEFAULT '' COMMENT '附件原始文件名',
        approver VARCHAR(50) NOT NULL COMMENT '审批人姓名',
        status TINYINT DEFAULT 0 COMMENT '0=待审批 1=已通过 2=已驳回',
        used_stamp TINYINT NOT NULL DEFAULT 0 COMMENT '0=未用印 1=已用印（仅 status=1 有效）',
        reject_reason VARCHAR(500) DEFAULT '' COMMENT '驳回原因',
        apply_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '申请时间',
        approve_time DATETIME NULL COMMENT '审批时间',
        used_time DATETIME NULL COMMENT '标记已用印时间',
        remark VARCHAR(500) DEFAULT '' COMMENT '备注',
        INDEX idx_applicant (applicant),
        INDEX idx_approver (approver),
        INDEX idx_status (status),
        INDEX idx_apply_time (apply_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='部门用印申请表';
    """
    try:
        db.execute_update(sql)
        logger.info("seal_apply 表已就绪")
    except Exception as e:
        logger.warning("seal_apply 建表跳过（可能已存在）: %s", e)


def _migrate_seal_extra_columns():
    """旧表补充 used_stamp、used_time"""
    alters = [
        "ALTER TABLE seal_apply ADD COLUMN used_stamp TINYINT NOT NULL DEFAULT 0 COMMENT '0=未用印 1=已用印' AFTER status",
        "ALTER TABLE seal_apply ADD COLUMN used_time DATETIME NULL COMMENT '标记已用印时间' AFTER approve_time",
    ]
    for sql in alters:
        try:
            db.execute_update(sql)
        except Exception as e:
            msg = str(e).lower()
            if "duplicate" in msg or "1060" in msg or "already exists" in msg:
                continue
            logger.warning("seal_apply 列迁移: %s", e)


_table_ready = False


def _attach_seal_display_fields(row: dict) -> None:
    """补充审批状态文案与用印状态文案"""
    st = row.get("status")
    us = int(row.get("used_stamp") or 0)
    if st == 0:
        row["approval_status_text"] = "待审批"
        row["seal_used_text"] = "—"
    elif st == 2:
        row["approval_status_text"] = "已驳回"
        row["seal_used_text"] = "—"
    else:
        row["approval_status_text"] = "已通过"
        row["seal_used_text"] = "已用印" if us == 1 else "未用印"
    row["status_text"] = row["approval_status_text"]


def _ensure_table():
    global _table_ready
    if not _table_ready:
        _init_table()
        _migrate_seal_extra_columns()
        _table_ready = True


# ==================== 获取可选审批人（经理/副经理）====================

@router.get("/approvers")
async def get_seal_approvers():
    """获取可选的用印审批人列表（yggl 表 jb 为经理/副经理的在职人员）"""
    sql = """
        SELECT name, jb, lsys
        FROM yggl
        WHERE (COALESCE(zaizhi, 0) = 0)
          AND (jb = '经理' OR jb LIKE '经理%' OR jb = '副经理' OR jb LIKE '副经理%'
               OR jb = '部长' OR jb LIKE '部长%' OR jb = '副部长' OR jb LIKE '副部长%')
        ORDER BY FIELD(
            CASE
                WHEN jb = '经理' OR jb LIKE '经理%' OR jb = '部长' OR jb LIKE '部长%' THEN '经理'
                ELSE '副经理'
            END, '经理', '副经理'
        ), name
    """
    rows = db.execute_query(sql)
    result = []
    for r in rows:
        jb_raw = (r.get("jb") or "").strip()
        label = f"{r['name']}（{jb_raw}）"
        result.append({"name": r["name"], "jb": jb_raw, "label": label})
    return {"success": True, "data": result}


# ==================== 提交用印申请 ====================

@router.post("/apply")
async def submit_seal_apply(
    applicant: str = Form(...),
    department: str = Form(""),
    seal_type: str = Form(""),
    reason: str = Form(...),
    approver: str = Form(...),
    remark: str = Form(""),
    attachment: UploadFile = File(...),
):
    """
    提交用印申请（FormData，含附件）
    - attachment: 必传附件，支持常用办公格式
    """
    _ensure_table()
    _ensure_upload_dir()

    if not applicant.strip():
        raise HTTPException(status_code=400, detail="申请人不能为空")
    if not reason.strip():
        raise HTTPException(status_code=400, detail="用印事由不能为空")
    if not approver.strip():
        raise HTTPException(status_code=400, detail="审批人不能为空")

    if not attachment or not attachment.filename:
        raise HTTPException(status_code=400, detail="请上传用印附件")

    original_name = attachment.filename
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式 {ext}，请上传 Word/Excel/PPT/PDF/图片/压缩包等常用办公文件",
        )

    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_SEAL_DIR / stored_name
    try:
        content = await attachment.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error("用印附件保存失败: %s", e)
        raise HTTPException(status_code=500, detail="附件保存失败，请重试")

    insert_sql = """
        INSERT INTO seal_apply
            (applicant, department, seal_type, reason, attachment, attachment_original, approver, status, used_stamp, apply_time, remark)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, NOW(), %s)
    """
    new_id = db.execute_insert(insert_sql, (
        applicant.strip(),
        department.strip(),
        seal_type.strip(),
        reason.strip(),
        stored_name,
        original_name,
        approver.strip(),
        remark.strip(),
    ))
    if new_id is None:
        raise HTTPException(status_code=500, detail="申请提交失败，请重试")

    return {"success": True, "message": "用印申请已提交", "id": new_id}


# ==================== 审批：获取待审批列表 ====================

@router.get("/pending")
async def get_pending_seal(approver: str = Query(..., description="审批人姓名")):
    """获取指定审批人的待审批用印申请列表"""
    _ensure_table()
    sql = """
        SELECT id, applicant, department, seal_type, reason,
               attachment, attachment_original, approver, status, used_stamp,
               apply_time, remark
        FROM seal_apply
        WHERE approver = %s AND status = 0
        ORDER BY apply_time DESC
    """
    rows = db.execute_query(sql, (approver.strip(),))
    for r in rows:
        if r.get("apply_time"):
            r["apply_time"] = str(r["apply_time"])
        _attach_seal_display_fields(r)
    return {"success": True, "data": rows, "total": len(rows)}


# ==================== 待用印：已通过且申请人未点「已用印」====================

@router.get("/pending-use")
async def get_pending_seal_use(applicant: str = Query(..., description="申请人姓名")):
    """当前用户已通过审批、尚未标记已用印的申请（首页待用印待办）"""
    _ensure_table()
    sql = """
        SELECT id, applicant, department, seal_type, reason,
               attachment, attachment_original, approver, status, used_stamp,
               apply_time, approve_time, remark
        FROM seal_apply
        WHERE applicant = %s AND status = 1 AND COALESCE(used_stamp, 0) = 0
        ORDER BY approve_time DESC, apply_time DESC
    """
    rows = db.execute_query(sql, (applicant.strip(),))
    for r in rows:
        if r.get("apply_time"):
            r["apply_time"] = str(r["apply_time"])
        if r.get("approve_time"):
            r["approve_time"] = str(r["approve_time"])
        _attach_seal_display_fields(r)
    return {"success": True, "data": rows, "total": len(rows)}


@router.post("/mark-used")
async def mark_seal_used(
    id: int = Form(...),
    applicant: str = Form(...),
):
    """申请人标记「已用印」"""
    _ensure_table()
    name = applicant.strip()
    if not name:
        raise HTTPException(status_code=400, detail="申请人不能为空")

    rows = db.execute_query(
        "SELECT id, applicant, status, COALESCE(used_stamp,0) AS us FROM seal_apply WHERE id = %s LIMIT 1",
        (id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="申请记录不存在")
    rec = rows[0]
    if (rec.get("applicant") or "").strip() != name:
        raise HTTPException(status_code=403, detail="仅申请人本人可标记已用印")
    if rec.get("status") != 1:
        raise HTTPException(status_code=400, detail="仅已通过的申请可标记已用印")
    if int(rec.get("us") or 0) == 1:
        raise HTTPException(status_code=400, detail="该申请已标记为已用印")

    affected = db.execute_update(
        "UPDATE seal_apply SET used_stamp = 1, used_time = NOW() WHERE id = %s AND status = 1 AND COALESCE(used_stamp,0) = 0",
        (id,),
    )
    if affected <= 0:
        raise HTTPException(status_code=500, detail="标记失败，请重试")
    return {"success": True, "message": "已标记为已用印"}


# ==================== 审批操作（通过/驳回）====================

@router.post("/approve")
async def approve_seal(
    id: int = Form(...),
    approver: str = Form(...),
    action: str = Form(...),
    reject_reason: str = Form(""),
):
    """
    审批用印申请
    - action: approve=通过, reject=驳回
    """
    _ensure_table()
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="无效操作，仅支持 approve / reject")

    check_sql = "SELECT id, status, approver FROM seal_apply WHERE id = %s LIMIT 1"
    rows = db.execute_query(check_sql, (id,))
    if not rows:
        raise HTTPException(status_code=404, detail="申请记录不存在")
    record = rows[0]
    if record["status"] != 0:
        raise HTTPException(status_code=400, detail="该申请已处理，无法重复操作")
    if record["approver"] != approver.strip():
        raise HTTPException(status_code=403, detail="您不是该申请的审批人")

    new_status = 1 if action == "approve" else 2
    if new_status == 1:
        update_sql = """
            UPDATE seal_apply
            SET status = %s, reject_reason = %s, approve_time = NOW(),
                used_stamp = 0, used_time = NULL
            WHERE id = %s AND status = 0
        """
    else:
        update_sql = """
            UPDATE seal_apply
            SET status = %s, reject_reason = %s, approve_time = NOW()
            WHERE id = %s AND status = 0
        """
    affected = db.execute_update(update_sql, (new_status, reject_reason.strip(), id))
    if affected <= 0:
        raise HTTPException(status_code=500, detail="审批操作失败，请重试")

    msg = "已通过" if action == "approve" else "已驳回"
    return {"success": True, "message": f"用印申请{msg}"}


# ==================== 查看全部记录（不做鉴权）====================

@router.get("/records")
async def get_seal_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", description="关键词搜索（申请人/事由/类型）"),
    status: str = Query("", description="状态筛选: all/pending/approved/rejected"),
    seal_used: str = Query("", description="用印筛选: 空/all | unused=已通过未用印 | used=已通过已用印"),
):
    """获取全部用印记录（分页，任何人可查看）"""
    _ensure_table()

    where_parts = ["1=1"]
    params: list = []

    if keyword.strip():
        kw = f"%{keyword.strip()}%"
        where_parts.append("(applicant LIKE %s OR reason LIKE %s OR seal_type LIKE %s)")
        params.extend([kw, kw, kw])

    if status == "pending":
        where_parts.append("status = 0")
    elif status == "approved":
        where_parts.append("status = 1")
    elif status == "rejected":
        where_parts.append("status = 2")

    if seal_used == "unused":
        where_parts.append("status = 1 AND COALESCE(used_stamp, 0) = 0")
    elif seal_used == "used":
        where_parts.append("status = 1 AND COALESCE(used_stamp, 0) = 1")

    where_clause = " AND ".join(where_parts)

    count_sql = f"SELECT COUNT(*) AS cnt FROM seal_apply WHERE {where_clause}"
    total = db.execute_scalar(count_sql, tuple(params)) or 0

    offset = (page - 1) * page_size
    data_sql = f"""
        SELECT id, applicant, department, seal_type, reason,
               attachment, attachment_original, approver, status, used_stamp,
               reject_reason, apply_time, approve_time, used_time, remark
        FROM seal_apply
        WHERE {where_clause}
        ORDER BY apply_time DESC
        LIMIT %s OFFSET %s
    """
    rows = db.execute_query(data_sql, tuple(params) + (page_size, offset))
    for r in rows:
        if r.get("apply_time"):
            r["apply_time"] = str(r["apply_time"])
        if r.get("approve_time"):
            r["approve_time"] = str(r["approve_time"])
        if r.get("used_time"):
            r["used_time"] = str(r["used_time"])
        _attach_seal_display_fields(r)

    return {
        "success": True,
        "data": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ==================== 附件下载 ====================

@router.get("/attachment")
async def download_seal_attachment(filename: str = Query(..., description="存储文件名")):
    """下载用印附件"""
    _ensure_upload_dir()
    file_path = UPLOAD_SEAL_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="附件不存在")

    original_sql = "SELECT attachment_original FROM seal_apply WHERE attachment = %s LIMIT 1"
    rows = db.execute_query(original_sql, (filename,))
    original_name = rows[0]["attachment_original"] if rows else filename

    return FileResponse(
        path=str(file_path),
        filename=original_name,
        media_type="application/octet-stream",
    )


# ==================== 我的用印申请 ====================

@router.get("/my-applications")
async def get_my_seal_applications(name: str = Query(..., description="申请人姓名")):
    """获取指定用户的全部用印申请"""
    _ensure_table()
    sql = """
        SELECT id, applicant, department, seal_type, reason,
               attachment, attachment_original, approver, status, used_stamp,
               reject_reason, apply_time, approve_time, used_time, remark
        FROM seal_apply
        WHERE applicant = %s
        ORDER BY apply_time DESC
    """
    rows = db.execute_query(sql, (name.strip(),))
    for r in rows:
        if r.get("apply_time"):
            r["apply_time"] = str(r["apply_time"])
        if r.get("approve_time"):
            r["approve_time"] = str(r["approve_time"])
        if r.get("used_time"):
            r["used_time"] = str(r["used_time"])
        _attach_seal_display_fields(r)
    return {"success": True, "data": rows}
