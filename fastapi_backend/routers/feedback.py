# -*- coding: utf-8 -*-
"""
意见与建议模块
  1. 部门吐槽墙（匿名弹幕，admin1 审核后上墙，支持点赞/领导回复/图片）
  2. 领导匿名信箱（匿名投递，经理/副经理回复）
  3. 系统功能建议（实名提交，admin1 回复）
"""
import uuid
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from database import db
from config import settings
from routers.db_manager import _get_admin1
from routers.email_sender import _build_email_message, _get_email_config, _smtp_send

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["意见与建议"])

_BASE = Path(__file__).resolve().parent.parent
WALL_UPLOAD_DIR = _BASE / settings.UPLOAD_DIR / "feedback_wall_images"
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024

# 已解决吐槽在公开吐槽墙仍保留的天数（从 resolved_at 起算）
WALL_RESOLVED_PUBLIC_VISIBLE_DAYS = 15


def _wall_public_list_where_sql() -> str:
    days = int(WALL_RESOLVED_PUBLIC_VISIBLE_DAYS)
    return (
        "WHERE status = 1 AND (COALESCE(resolved, 0) <> 3 OR ("
        "COALESCE(resolved, 0) = 3 AND resolved_at IS NOT NULL AND "
        f"resolved_at >= DATE_SUB(NOW(), INTERVAL {days} DAY))) "
    )


# ==================== 建表（启动时自动创建） ====================

_INIT_DONE = False


def _ensure_wall_upload_dir():
    WALL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def _save_wall_image(f: UploadFile) -> str:
    _ensure_wall_upload_dir()
    if not f.filename:
        return ""
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {ext}")
    content = await f.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="图片不能超过 5MB")
    safe_name = f"wall_{uuid.uuid4().hex[:12]}{ext}"
    with open(WALL_UPLOAD_DIR / safe_name, "wb") as fp:
        fp.write(content)
    return safe_name


def _ensure_tables():
    global _INIT_DONE
    if _INIT_DONE:
        return
    try:
        db.execute_update("""
            CREATE TABLE IF NOT EXISTS feedback_wall (
                id VARCHAR(36) PRIMARY KEY,
                content TEXT NOT NULL,
                image_url VARCHAR(200) NULL COMMENT '附图文件名',
                like_count INT DEFAULT 0,
                status TINYINT DEFAULT 0 COMMENT '0=待审核 1=已通过 2=已拒绝',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                reviewed_at DATETIME NULL,
                reviewed_by VARCHAR(50) NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        for col, spec in [
            ("image_url", "VARCHAR(200) NULL"),
            ("like_count", "INT DEFAULT 0"),
            ("resolved", "TINYINT DEFAULT 0 COMMENT '0=未处理 1=处理中 2=已回复 3=已解决'"),
            ("resolved_by", "VARCHAR(50) NULL"),
            ("resolved_at", "DATETIME NULL"),
            ("assignee", "VARCHAR(50) NULL COMMENT '吐槽问题负责人'"),
            ("assigned_by", "VARCHAR(50) NULL COMMENT '指派人'"),
            ("assigned_at", "DATETIME NULL COMMENT '指派时间'"),
        ]:
            try:
                db.execute_update(f"ALTER TABLE feedback_wall ADD COLUMN {col} {spec}")
            except Exception:
                pass
        db.execute_update("""
            CREATE TABLE IF NOT EXISTS feedback_wall_likes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                wall_id VARCHAR(36) NOT NULL,
                user_name VARCHAR(50) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_wall_user (wall_id, user_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        db.execute_update("""
            CREATE TABLE IF NOT EXISTS feedback_wall_replies (
                id VARCHAR(36) PRIMARY KEY,
                wall_id VARCHAR(36) NOT NULL,
                reply_by VARCHAR(50) NOT NULL COMMENT '回复领导姓名',
                reply_content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_wall_id (wall_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        db.execute_update("""
            CREATE TABLE IF NOT EXISTS feedback_leader_inbox (
                id VARCHAR(36) PRIMARY KEY,
                target_leader VARCHAR(50) NOT NULL COMMENT '目标领导姓名',
                content TEXT NOT NULL,
                image_url VARCHAR(200) NULL COMMENT '附图文件名',
                reply TEXT NULL,
                reply_at DATETIME NULL,
                status TINYINT DEFAULT 0 COMMENT '0=未回复 1=已回复',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        try:
            db.execute_update("ALTER TABLE feedback_leader_inbox ADD COLUMN image_url VARCHAR(200) NULL")
        except Exception:
            pass
        db.execute_update("""
            CREATE TABLE IF NOT EXISTS feedback_system (
                id VARCHAR(36) PRIMARY KEY,
                submitter VARCHAR(50) NOT NULL COMMENT '提交人姓名',
                department VARCHAR(100) NULL,
                content TEXT NOT NULL,
                image_url VARCHAR(200) NULL COMMENT '附图文件名',
                reply TEXT NULL,
                reply_at DATETIME NULL,
                reply_by VARCHAR(50) NULL,
                status TINYINT DEFAULT 0 COMMENT '0=未回复 1=已回复',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        try:
            db.execute_update("ALTER TABLE feedback_system ADD COLUMN image_url VARCHAR(200) NULL")
        except Exception:
            pass
        _INIT_DONE = True
        logger.info("意见与建议模块: 表初始化完成")
    except Exception as e:
        logger.warning("意见与建议模块: 建表异常 %s", e)


def _require_admin1(current_user: str):
    admin1 = _get_admin1()
    if not admin1 or (current_user or "").strip() != admin1:
        raise HTTPException(status_code=403, detail="仅系统管理员可操作")


def _is_wall_privileged_user(current_user: str) -> bool:
    """吐槽墙全记录权限：管理员或经理/副经理/经理助理/部长/副部长。"""
    name = (current_user or "").strip()
    if not name:
        return False
    admin1 = _get_admin1()
    if admin1 and name == admin1:
        return True
    rows = db.execute_query(
        "SELECT jb FROM yggl WHERE name = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
        (name,),
    )
    jb = (rows[0].get("jb") if rows else "") or ""
    return bool(re.search(r"经理助理|副经理|经理|副部长|部长", jb))


def _unique_email_people(rows) -> list[dict]:
    people = []
    seen = set()
    for row in rows or []:
        email = (row.get("enterprise_email") or row.get("email") or "").strip()
        name = (row.get("name") or "").strip()
        if not email:
            continue
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        people.append({"name": name, "email": email, "jb": (row.get("jb") or "").strip()})
    return people


def _get_wall_mail_leaders() -> list[dict]:
    rows = db.execute_query(
        """
        SELECT name, jb, enterprise_email
        FROM yggl
        WHERE COALESCE(zaizhi,0) = 0
          AND name IS NOT NULL AND TRIM(name) != ''
          AND enterprise_email IS NOT NULL AND TRIM(enterprise_email) != ''
          AND (jb = %s OR jb = %s)
        ORDER BY jb, name
        """,
        ("经理", "副经理"),
    )
    return _unique_email_people(rows)


def _get_wall_mail_person(name: str) -> dict | None:
    person_name = (name or "").strip()
    if not person_name:
        return None
    rows = db.execute_query(
        """
        SELECT name, jb, enterprise_email
        FROM yggl
        WHERE name = %s AND COALESCE(zaizhi,0) = 0
        LIMIT 1
        """,
        (person_name,),
    )
    people = _unique_email_people(rows)
    return people[0] if people else None


def _send_wall_mail(to_people: list[dict], cc_people: list[dict], subject: str, content: str) -> dict:
    cfg = _get_email_config()
    sender = cfg.get("address") or ""
    password = cfg.get("auth_code") or ""
    if not sender or not password:
        return {"sent": False, "message": "系统邮箱未配置，未发送邮件", "toCount": 0, "ccCount": 0}

    to = [p["email"] for p in _unique_email_people(to_people)]
    cc = [p["email"] for p in _unique_email_people(cc_people) if p["email"].lower() not in {x.lower() for x in to}]
    if not to:
        return {"sent": False, "message": "未找到可用收件人企业邮箱", "toCount": 0, "ccCount": len(cc)}

    try:
        message = _build_email_message(sender, to, cc, subject, content, "plain", None)
        _smtp_send(sender, password, list(set(to + cc)), message)
        cc_part = f"，抄送 {len(cc)} 人" if cc else ""
        return {"sent": True, "message": f"邮件已发送给 {len(to)} 人{cc_part}", "toCount": len(to), "ccCount": len(cc)}
    except HTTPException as e:
        return {"sent": False, "message": str(e.detail), "toCount": len(to), "ccCount": len(cc)}
    except Exception as e:  # noqa: BLE001
        logger.warning("吐槽墙邮件发送失败: %s", e)
        return {"sent": False, "message": f"邮件发送失败: {e}", "toCount": len(to), "ccCount": len(cc)}


def _get_wall_item(item_id: str) -> dict:
    rows = db.execute_query(
        "SELECT id, content, image_url, created_at FROM feedback_wall WHERE id = %s LIMIT 1",
        (item_id,),
    )
    return rows[0] if rows else {}


def _send_wall_approved_notice(item: dict, reviewer: str, reviewed_at: str) -> dict:
    leaders = _get_wall_mail_leaders()
    content = (
        "各位领导：\n\n"
        "有一条新的吐槽已通过审核并上墙，请关注处理。\n\n"
        f"吐槽内容：{item.get('content') or ''}\n"
        f"审核人：{reviewer}\n"
        f"审核时间：{reviewed_at}\n\n"
        "此邮件由 OA 系统自动发送，请勿直接回复。"
    )
    return _send_wall_mail(leaders, [], "【OA吐槽墙】新吐槽已上墙", content)


def _send_wall_assignment_notice(item: dict, reply_content: str, assignee: str, assigner: str, assigned_at: str) -> dict:
    assignee_person = _get_wall_mail_person(assignee)
    leaders = _get_wall_mail_leaders()
    to_people = [assignee_person] if assignee_person else []
    content = (
        f"{assignee}：\n\n"
        "领导已在 OA 吐槽墙指派你处理一条吐槽事项，请及时跟进。\n\n"
        f"吐槽内容：{item.get('content') or ''}\n"
        f"领导回复/处理意见：{reply_content}\n"
        f"指派人：{assigner}\n"
        f"指派时间：{assigned_at}\n\n"
        "此邮件由 OA 系统自动发送，请勿直接回复。"
    )
    return _send_wall_mail(to_people, leaders, "【OA吐槽墙】吐槽任务指派提醒", content)


# ==================== 1. 部门吐槽墙 ====================

class WallReview(BaseModel):
    action: str  # approve / reject
    current_user: str


@router.post("/wall/submit")
async def wall_submit(
    content: str = Form(...),
    image: UploadFile = File(default=None),
):
    """提交吐槽（匿名，不存任何人员信息，可附一张图片）"""
    _ensure_tables()
    content = (content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="内容不能为空")
    if len(content) > 200:
        raise HTTPException(status_code=400, detail="内容不能超过200字")
    img_name = ""
    if image and image.filename:
        img_name = await _save_wall_image(image)
    new_id = uuid.uuid4().hex
    db.execute_update(
        "INSERT INTO feedback_wall (id, content, image_url, status, created_at) VALUES (%s, %s, %s, 0, %s)",
        (new_id, content, img_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    return {"success": True, "message": "已提交，待管理员审核"}


def _wall_resolved_int(val) -> int:
    try:
        if val is None:
            return 0
        return int(val)
    except (TypeError, ValueError):
        return 0


def _resolved_at_display(val) -> str:
    if not val:
        return ""
    return str(val)[:19]


def _build_wall_items(rows):
    """为 wall 列表构建含 replies 信息的数据"""
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    placeholders = ",".join(["%s"] * len(ids))
    reply_rows = db.execute_query(
        f"SELECT wall_id, reply_by, reply_content FROM feedback_wall_replies "
        f"WHERE wall_id IN ({placeholders}) ORDER BY created_at ASC",
        tuple(ids),
    )
    reply_map = {}
    for rr in reply_rows:
        reply_map.setdefault(rr["wall_id"], []).append({
            "replyBy": rr["reply_by"],
            "replyContent": rr["reply_content"],
        })
    status_label_map = {0: "正在审核", 1: "已上墙", 2: "已驳回"}
    return [
        {
            "id": r["id"],
            "content": r["content"],
            "imageUrl": r.get("image_url") or "",
            "likeCount": r.get("like_count") or 0,
            "status": r.get("status") if r.get("status") is not None else 1,
            "statusLabel": status_label_map.get(r.get("status") if r.get("status") is not None else 1, "未知"),
            "resolved": _wall_resolved_int(r.get("resolved")),
            "resolvedBy": r.get("resolved_by") or "",
            "resolvedAt": _resolved_at_display(r.get("resolved_at")),
            "assignee": r.get("assignee") or "",
            "assignedBy": r.get("assigned_by") or "",
            "assignedAt": str(r.get("assigned_at") or "")[:19] if r.get("assigned_at") else "",
            "reviewedBy": r.get("reviewed_by") or "",
            "reviewedAt": str(r.get("reviewed_at") or "")[:19] if r.get("reviewed_at") else "",
            "replies": reply_map.get(r["id"], []),
            "createdAt": str(r.get("created_at") or "")[:19],
        }
        for r in rows
    ]


@router.get("/wall/list")
async def wall_list(include_all: bool = Query(False), current_user: str = Query("")):
    """获取吐槽墙列表。

    默认返回已通过：未解决始终展示；已解决自 resolved_at 起保留 WALL_RESOLVED_PUBLIC_VISIBLE_DAYS 天，超时不再出现在公开列表。
    include_all=true 时，管理员/领导可看全部，普通用户仅可看 status=1 的已上墙记录。
    """
    _ensure_tables()
    select_sql = (
        "SELECT id, content, image_url, like_count, status, resolved, resolved_by, resolved_at, assignee, assigned_by, assigned_at, "
        "reviewed_by, reviewed_at, created_at FROM feedback_wall "
    )
    public_where = _wall_public_list_where_sql()
    if include_all:
        if _is_wall_privileged_user(current_user):
            rows = db.execute_query(select_sql + "ORDER BY created_at DESC")
        else:
            rows = db.execute_query(select_sql + public_where + "ORDER BY created_at DESC")
    else:
        rows = db.execute_query(select_sql + public_where + "ORDER BY created_at DESC")
    return {"success": True, "data": _build_wall_items(rows)}


@router.get("/wall/records")
async def wall_records(current_user: str = Query("")):
    """获取吐槽墙记录。管理员/领导可看全部，普通用户与公开列表一致（已解决仅保留 resolved_at 起算若干天内）。"""
    _ensure_tables()
    select_sql = (
        "SELECT id, content, image_url, like_count, status, resolved, resolved_by, resolved_at, assignee, assigned_by, assigned_at, "
        "reviewed_by, reviewed_at, created_at FROM feedback_wall "
    )
    public_where = _wall_public_list_where_sql()
    if _is_wall_privileged_user(current_user):
        rows = db.execute_query(select_sql + "ORDER BY created_at DESC")
    else:
        rows = db.execute_query(select_sql + public_where + "ORDER BY created_at DESC")
    return {"success": True, "data": _build_wall_items(rows)}


@router.get("/wall/assigned")
async def wall_assigned(current_user: str = Query(...)):
    """当前用户被指派处理、且尚未解决的吐槽问题（首页待办使用）"""
    _ensure_tables()
    name = (current_user or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="缺少用户信息")
    rows = db.execute_query(
        "SELECT id, content, image_url, like_count, resolved, resolved_by, resolved_at, assignee, assigned_by, assigned_at, created_at "
        "FROM feedback_wall "
        "WHERE status = 1 AND assignee = %s AND COALESCE(resolved, 0) <> 3 "
        "ORDER BY assigned_at DESC, created_at DESC",
        (name,),
    )
    return {"success": True, "data": _build_wall_items(rows)}


@router.get("/wall/pending")
async def wall_pending(current_user: str = Query(...)):
    """待审核列表（仅 admin1）"""
    _ensure_tables()
    _require_admin1(current_user)
    rows = db.execute_query(
        "SELECT id, content, image_url, created_at FROM feedback_wall WHERE status = 0 ORDER BY created_at DESC"
    )
    return {
        "success": True,
        "data": [
            {
                "id": r["id"],
                "content": r["content"],
                "imageUrl": r.get("image_url") or "",
                "createdAt": str(r.get("created_at") or "")[:19],
            }
            for r in rows
        ],
    }


@router.post("/wall/{item_id}/review")
async def wall_review(item_id: str, req: WallReview):
    """审核吐槽（approve/reject，仅 admin1）"""
    _ensure_tables()
    _require_admin1(req.current_user)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if req.action == "approve":
        n = db.execute_update(
            "UPDATE feedback_wall SET status = 1, reviewed_at = %s, reviewed_by = %s WHERE id = %s AND status = 0",
            (now, req.current_user.strip(), item_id),
        )
    elif req.action == "reject":
        n = db.execute_update(
            "UPDATE feedback_wall SET status = 2, reviewed_at = %s, reviewed_by = %s WHERE id = %s AND status = 0",
            (now, req.current_user.strip(), item_id),
        )
    else:
        raise HTTPException(status_code=400, detail="action 须为 approve 或 reject")
    if not n:
        raise HTTPException(status_code=404, detail="记录不存在或已处理")
    message = "已通过" if req.action == "approve" else "已拒绝"
    email_notice = None
    if req.action == "approve":
        item = _get_wall_item(item_id)
        email_notice = _send_wall_approved_notice(item, req.current_user.strip(), now)
    return {"success": True, "message": message, "emailNotice": email_notice}


class WallLike(BaseModel):
    current_user: str


@router.post("/wall/{item_id}/like")
async def wall_like(item_id: str, req: WallLike):
    """点赞/取消点赞"""
    _ensure_tables()
    name = (req.current_user or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="缺少用户信息")
    wall_rows = db.execute_query(
        "SELECT id FROM feedback_wall WHERE id = %s AND status = 1",
        (item_id,),
    )
    if not wall_rows:
        raise HTTPException(status_code=404, detail="记录不存在或尚未上墙")
    existing = db.execute_query(
        "SELECT id FROM feedback_wall_likes WHERE wall_id = %s AND user_name = %s",
        (item_id, name),
    )
    if existing:
        db.execute_update(
            "DELETE FROM feedback_wall_likes WHERE wall_id = %s AND user_name = %s",
            (item_id, name),
        )
        db.execute_update(
            "UPDATE feedback_wall SET like_count = GREATEST(like_count - 1, 0) WHERE id = %s",
            (item_id,),
        )
        liked = False
    else:
        db.execute_update(
            "INSERT INTO feedback_wall_likes (wall_id, user_name) VALUES (%s, %s)",
            (item_id, name),
        )
        db.execute_update(
            "UPDATE feedback_wall SET like_count = like_count + 1 WHERE id = %s",
            (item_id,),
        )
        liked = True
    row = db.execute_query(
        "SELECT like_count FROM feedback_wall WHERE id = %s", (item_id,)
    )
    like_count = row[0]["like_count"] if row else 0
    return {"success": True, "liked": liked, "likeCount": like_count}


@router.get("/wall/{item_id}/detail")
async def wall_detail(item_id: str, current_user: str = Query("")):
    """获取单条吐槽的详情（含全部领导回复和当前用户是否已点赞）"""
    _ensure_tables()
    rows = db.execute_query(
        "SELECT id, content, image_url, like_count, status, resolved, resolved_by, resolved_at, assignee, assigned_by, assigned_at, "
        "reviewed_by, reviewed_at, created_at "
        "FROM feedback_wall WHERE id = %s",
        (item_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    r = rows[0]
    status_val = r.get("status") if r.get("status") is not None else 1
    if int(status_val) != 1 and not _is_wall_privileged_user(current_user):
        raise HTTPException(status_code=403, detail="无权查看该吐槽记录")
    replies = db.execute_query(
        "SELECT id, reply_by, reply_content, created_at FROM feedback_wall_replies "
        "WHERE wall_id = %s ORDER BY created_at ASC",
        (item_id,),
    )
    liked = False
    name = (current_user or "").strip()
    if name:
        lk = db.execute_query(
            "SELECT id FROM feedback_wall_likes WHERE wall_id = %s AND user_name = %s",
            (item_id, name),
        )
        liked = bool(lk)
    return {
        "success": True,
        "data": {
            "id": r["id"],
            "content": r["content"],
            "imageUrl": r.get("image_url") or "",
            "likeCount": r.get("like_count") or 0,
            "status": r.get("status") if r.get("status") is not None else 1,
            "statusLabel": {0: "正在审核", 1: "已上墙", 2: "已驳回"}.get(r.get("status") if r.get("status") is not None else 1, "未知"),
            "resolved": _wall_resolved_int(r.get("resolved")),
            "resolvedBy": r.get("resolved_by") or "",
            "resolvedAt": _resolved_at_display(r.get("resolved_at")),
            "assignee": r.get("assignee") or "",
            "assignedBy": r.get("assigned_by") or "",
            "assignedAt": str(r.get("assigned_at") or "")[:19] if r.get("assigned_at") else "",
            "reviewedBy": r.get("reviewed_by") or "",
            "reviewedAt": str(r.get("reviewed_at") or "")[:19] if r.get("reviewed_at") else "",
            "liked": liked,
            "createdAt": str(r.get("created_at") or "")[:19],
            "replies": [
                {
                    "id": rr["id"],
                    "replyBy": rr["reply_by"],
                    "replyContent": rr["reply_content"],
                    "createdAt": str(rr.get("created_at") or "")[:19],
                }
                for rr in replies
            ],
        },
    }


class WallReplyReq(BaseModel):
    reply_content: str
    current_user: str
    assignee: Optional[str] = ""


@router.post("/wall/{item_id}/reply")
async def wall_reply(item_id: str, req: WallReplyReq):
    """领导回复吐槽"""
    _ensure_tables()
    name = (req.current_user or "").strip()
    reply_content = (req.reply_content or "").strip()
    assignee = (req.assignee or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="缺少用户信息")
    if not reply_content:
        raise HTTPException(status_code=400, detail="回复内容不能为空")
    rows = db.execute_query("SELECT id, content, image_url, created_at FROM feedback_wall WHERE id = %s AND status = 1", (item_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    if assignee:
        user_rows = db.execute_query(
            "SELECT name FROM yggl WHERE name = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
            (assignee,),
        )
        if not user_rows:
            raise HTTPException(status_code=400, detail="负责人不存在或已离职")
    new_id = uuid.uuid4().hex
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute_update(
        "INSERT INTO feedback_wall_replies (id, wall_id, reply_by, reply_content, created_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        (new_id, item_id, name, reply_content, now),
    )
    if assignee:
        db.execute_update(
            "UPDATE feedback_wall "
            "SET assignee = %s, assigned_by = %s, assigned_at = %s, "
            "resolved = 1 "
            "WHERE id = %s",
            (assignee, name, now, item_id),
        )
    else:
        db.execute_update(
            "UPDATE feedback_wall "
            "SET resolved = CASE WHEN COALESCE(resolved, 0) = 0 THEN 2 ELSE resolved END "
            "WHERE id = %s",
            (item_id,),
        )
    email_notice = None
    if assignee:
        email_notice = _send_wall_assignment_notice(rows[0], reply_content, assignee, name, now)
    return {"success": True, "message": "回复成功", "emailNotice": email_notice}


class WallResolve(BaseModel):
    resolved: int  # 1=处理中 2=已回复 3=已解决
    current_user: str


@router.post("/wall/{item_id}/resolve")
async def wall_resolve(item_id: str, req: WallResolve):
    """领导标记吐槽处理状态"""
    _ensure_tables()
    name = (req.current_user or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="缺少用户信息")
    if req.resolved not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="resolved 须为 1、2 或 3")
    rows = db.execute_query("SELECT id, assignee FROM feedback_wall WHERE id = %s AND status = 1", (item_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    if req.resolved == 3:
        user_rows = db.execute_query(
            "SELECT jb FROM yggl WHERE name = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
            (name,),
        )
        jb = (user_rows[0].get("jb") if user_rows else "") or ""
        admin1 = _get_admin1()
        is_leader = bool(admin1 and name == admin1) or bool(re.search(r"经理|副经理", jb))
        is_assignee = name == ((rows[0].get("assignee") or "").strip())
        if not (is_leader or is_assignee):
            raise HTTPException(status_code=403, detail="仅领导或当前负责人可标记已解决")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute_update(
        "UPDATE feedback_wall SET resolved = %s, resolved_by = %s, resolved_at = %s WHERE id = %s",
        (req.resolved, name, now, item_id),
    )
    message_map = {1: "处理中", 2: "已标记为已回复", 3: "已标记为已解决"}
    return {"success": True, "message": message_map.get(req.resolved, "操作成功")}


@router.get("/wall/image")
async def wall_image(filename: str = Query(...)):
    """获取吐槽墙图片"""
    safe = Path(filename).name
    fpath = WALL_UPLOAD_DIR / safe
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    media_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".bmp": "image/bmp", ".webp": "image/webp",
    }
    ext = Path(safe).suffix.lower()
    return FileResponse(fpath, media_type=media_types.get(ext, "application/octet-stream"))


# ==================== 2. 领导匿名信箱 ====================

LEADER_UPLOAD_DIR = _BASE / settings.UPLOAD_DIR / "feedback_leader_images"


def _ensure_leader_upload_dir():
    LEADER_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def _save_leader_image(f: UploadFile) -> str:
    _ensure_leader_upload_dir()
    if not f.filename:
        return ""
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {ext}")
    content = await f.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="图片不能超过 5MB")
    safe_name = f"leader_{uuid.uuid4().hex[:12]}{ext}"
    with open(LEADER_UPLOAD_DIR / safe_name, "wb") as fp:
        fp.write(content)
    return safe_name


class LeaderReply(BaseModel):
    reply: str
    current_user: str


class LeaderMarkRead(BaseModel):
    current_user: str


@router.get("/leader/targets")
async def leader_targets():
    """获取可选领导列表（yggl.jb 含经理/副经理）"""
    _ensure_tables()
    rows = db.execute_query(
        "SELECT name, jb FROM yggl "
        "WHERE (jb = %s OR jb LIKE %s OR jb = %s OR jb LIKE %s) "
        "AND name IS NOT NULL AND name != '' AND (COALESCE(zaizhi,0)=0) "
        "ORDER BY jb, name",
        ("经理", "经理%", "副经理", "副经理%"),
    )
    return {
        "success": True,
        "data": [{"name": r["name"], "jb": r.get("jb", "")} for r in rows],
    }


@router.post("/leader/submit")
async def leader_submit(
    target_leader: str = Form(...),
    content: str = Form(...),
    image: UploadFile = File(default=None),
):
    """提交匿名意见给领导（可附图片）"""
    _ensure_tables()
    content = (content or "").strip()
    target = (target_leader or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="内容不能为空")
    if not target:
        raise HTTPException(status_code=400, detail="请选择目标领导")
    img_name = ""
    if image and image.filename:
        img_name = await _save_leader_image(image)
    new_id = uuid.uuid4().hex
    db.execute_update(
        "INSERT INTO feedback_leader_inbox (id, target_leader, content, image_url, status, created_at) "
        "VALUES (%s, %s, %s, %s, 0, %s)",
        (new_id, target, content, img_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    return {"success": True, "message": "已匿名提交"}


@router.get("/leader/inbox")
async def leader_inbox(current_user: str = Query(...)):
    """领导查看收到的匿名意见。status：0=未读，1=已读（历史数据中曾回复过的同为 1）。"""
    _ensure_tables()
    name = (current_user or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="缺少用户信息")
    rows = db.execute_query(
        "SELECT id, content, image_url, reply, status, created_at, reply_at FROM feedback_leader_inbox "
        "WHERE target_leader = %s ORDER BY created_at DESC",
        (name,),
    )
    return {
        "success": True,
        "data": [
            {
                "id": r["id"],
                "content": r["content"],
                "imageUrl": r.get("image_url") or "",
                "reply": r.get("reply") or "",
                "status": r["status"],
                "createdAt": str(r.get("created_at") or "")[:19],
                "replyAt": str(r.get("reply_at") or "")[:19] if r.get("reply_at") else "",
            }
            for r in rows
        ],
    }


@router.post("/leader/mark-read")
async def leader_mark_read(req: LeaderMarkRead):
    """将全部匿名意见标记为已读（不再要求回复）。"""
    _ensure_tables()
    name = (req.current_user or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="缺少用户信息")
    db.execute_update(
        "UPDATE feedback_leader_inbox SET status = 1 WHERE target_leader = %s AND COALESCE(status, 0) = 0",
        (name,),
    )
    return {"success": True, "message": "已标记已读"}


@router.post("/leader/{item_id}/reply")
async def leader_reply(item_id: str, req: LeaderReply):
    """领导匿名信箱禁用回复。"""
    raise HTTPException(status_code=403, detail="领导匿名信箱已禁用回复")


@router.get("/leader/public")
async def leader_public():
    """领导匿名信箱不再公示，固定返回空列表。"""
    return {"success": True, "data": []}


@router.get("/leader/image")
async def leader_image(filename: str = Query(...)):
    """获取领导信箱附图"""
    safe = Path(filename).name
    fpath = LEADER_UPLOAD_DIR / safe
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    media_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".bmp": "image/bmp", ".webp": "image/webp",
    }
    ext = Path(safe).suffix.lower()
    return FileResponse(fpath, media_type=media_types.get(ext, "application/octet-stream"))


# ==================== 3. 系统功能建议 ====================

SYSTEM_UPLOAD_DIR = _BASE / settings.UPLOAD_DIR / "feedback_system_images"


def _ensure_system_upload_dir():
    SYSTEM_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def _save_system_image(f: UploadFile) -> str:
    _ensure_system_upload_dir()
    if not f.filename:
        return ""
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {ext}")
    content = await f.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="图片不能超过 5MB")
    safe_name = f"sys_{uuid.uuid4().hex[:12]}{ext}"
    with open(SYSTEM_UPLOAD_DIR / safe_name, "wb") as fp:
        fp.write(content)
    return safe_name


class SystemReply(BaseModel):
    reply: str
    current_user: str


@router.post("/system/submit")
async def system_submit(
    submitter: str = Form(...),
    content: str = Form(...),
    department: str = Form(""),
    image: UploadFile = File(default=None),
):
    """提交系统功能建议（实名，可附图片）"""
    _ensure_tables()
    content = (content or "").strip()
    submitter = (submitter or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="内容不能为空")
    if not submitter:
        raise HTTPException(status_code=400, detail="缺少提交人信息")
    img_name = ""
    if image and image.filename:
        img_name = await _save_system_image(image)
    new_id = uuid.uuid4().hex
    db.execute_update(
        "INSERT INTO feedback_system (id, submitter, department, content, image_url, status, created_at) "
        "VALUES (%s, %s, %s, %s, %s, 0, %s)",
        (new_id, submitter, (department or "").strip(), content, img_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    return {"success": True, "message": "建议已提交"}


@router.get("/system/list")
async def system_list():
    """全部建议列表（含回复）"""
    _ensure_tables()
    rows = db.execute_query(
        "SELECT id, submitter, department, content, image_url, reply, reply_by, reply_at, status, created_at "
        "FROM feedback_system ORDER BY created_at DESC"
    )
    return {
        "success": True,
        "data": [
            {
                "id": r["id"],
                "submitter": r["submitter"],
                "department": r.get("department") or "",
                "content": r["content"],
                "imageUrl": r.get("image_url") or "",
                "reply": r.get("reply") or "",
                "replyBy": r.get("reply_by") or "",
                "replyAt": str(r.get("reply_at") or "")[:19] if r.get("reply_at") else "",
                "status": r["status"],
                "createdAt": str(r.get("created_at") or "")[:19],
            }
            for r in rows
        ],
    }


@router.get("/system/image")
async def system_image(filename: str = Query(...)):
    """获取系统建议附图"""
    safe = Path(filename).name
    fpath = SYSTEM_UPLOAD_DIR / safe
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    media_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".bmp": "image/bmp", ".webp": "image/webp",
    }
    ext = Path(safe).suffix.lower()
    return FileResponse(fpath, media_type=media_types.get(ext, "application/octet-stream"))


@router.post("/system/{item_id}/reply")
async def system_reply(item_id: str, req: SystemReply):
    """admin1 回复系统功能建议"""
    _ensure_tables()
    _require_admin1(req.current_user)
    reply = (req.reply or "").strip()
    if not reply:
        raise HTTPException(status_code=400, detail="回复内容不能为空")
    rows = db.execute_query("SELECT id FROM feedback_system WHERE id = %s", (item_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute_update(
        "UPDATE feedback_system SET reply = %s, reply_by = %s, reply_at = %s, status = 1 WHERE id = %s",
        (reply, req.current_user.strip(), now, item_id),
    )
    return {"success": True, "message": "回复成功"}
