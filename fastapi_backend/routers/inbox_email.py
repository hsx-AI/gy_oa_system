# -*- coding: utf-8 -*-
"""
共用邮箱收件箱 API - 仅系统管理员 (webconfig.admin1) 可使用
基于网易企业邮箱 IMAP SSL 从共用邮箱拉取邮件并存储到 inbox_emails 表
存储字段：主题、发件人、收件人、抄送人、发件时间、全部正文（纯文本 + HTML）
"""
import asyncio
import email
import imaplib
import logging
import re
from datetime import datetime
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime, getaddresses
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inbox-email", tags=["共用邮箱收件箱"])

IMAP_SERVER = "imap.163.com"
IMAP_PORT_SSL = 993

# 后台轮询间隔（秒），可根据需要调整
POLL_INTERVAL_SECONDS = 120
# 单次拉取的最多邮件数（避免首次拉取过多）
MAX_FETCH_PER_POLL = 50


# ==================== 建表 / 字段保障 ====================

def _ensure_inbox_columns():
    """确保 webconfig 表有共用邮箱配置字段。"""
    for col, typedef in [
        ("inbox_email_address", "VARCHAR(200) DEFAULT ''"),
        ("inbox_email_auth_code", "VARCHAR(200) DEFAULT ''"),
    ]:
        try:
            db.execute_update(f"ALTER TABLE webconfig ADD COLUMN {col} {typedef}", ())
        except Exception:
            pass


def _ensure_inbox_table():
    """创建 inbox_emails 表（若不存在）。"""
    sql = """
    CREATE TABLE IF NOT EXISTS inbox_emails (
        id INT AUTO_INCREMENT PRIMARY KEY,
        message_id VARCHAR(500) DEFAULT NULL COMMENT '邮件 Message-ID（用于去重）',
        uid VARCHAR(64) DEFAULT NULL COMMENT 'IMAP 中的 UID（可选）',
        subject VARCHAR(500) DEFAULT '' COMMENT '主题',
        from_addr VARCHAR(500) DEFAULT '' COMMENT '发件人（含姓名 <地址>）',
        to_addrs TEXT COMMENT '收件人（逗号分隔）',
        cc_addrs TEXT COMMENT '抄送人（逗号分隔）',
        email_date DATETIME DEFAULT NULL COMMENT '发件时间（邮件头 Date）',
        body_text LONGTEXT COMMENT '纯文本正文',
        body_html LONGTEXT COMMENT 'HTML 正文',
        received_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
        UNIQUE KEY uk_message_id (message_id),
        INDEX idx_email_date (email_date),
        INDEX idx_received_at (received_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='共用邮箱收件箱';
    """
    try:
        db.execute_update(sql)
    except Exception as e:
        logger.warning("inbox_emails 建表失败: %s", e)


_ensure_inbox_columns()
_ensure_inbox_table()


# ==================== 辅助函数 ====================

def _get_admin1() -> Optional[str]:
    try:
        rows = db.execute_query("SELECT admin1 FROM webconfig WHERE id = %s LIMIT 1", ("1",))
        if rows and rows[0].get("admin1") is not None:
            return (rows[0]["admin1"] or "").strip() or None
    except Exception:
        pass
    return None


def _require_admin(current_user: str):
    admin1 = _get_admin1()
    if not admin1 or (current_user or "").strip() != admin1:
        raise HTTPException(status_code=403, detail="仅系统管理员（webconfig.admin1）可操作")


def _get_inbox_config() -> dict:
    _ensure_inbox_columns()
    try:
        rows = db.execute_query(
            "SELECT inbox_email_address, inbox_email_auth_code FROM webconfig WHERE id = %s LIMIT 1",
            ("1",),
        )
        if rows:
            return {
                "address": (rows[0].get("inbox_email_address") or "").strip(),
                "auth_code": (rows[0].get("inbox_email_auth_code") or "").strip(),
            }
    except Exception as e:
        logger.debug(f"读取共用邮箱配置失败: {e}")
    return {"address": "", "auth_code": ""}


def _decode_mime_header(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:
        try:
            parts = decode_header(value)
            out = []
            for text, charset in parts:
                if isinstance(text, bytes):
                    try:
                        out.append(text.decode(charset or "utf-8", errors="replace"))
                    except Exception:
                        out.append(text.decode("utf-8", errors="replace"))
                else:
                    out.append(text)
            return "".join(out).strip()
        except Exception:
            return str(value).strip()


def _format_address_list(raw: Optional[str]) -> str:
    """解析 To/Cc 头为 '张三 <a@b>, 李四 <c@d>' 形式的字符串。"""
    if not raw:
        return ""
    try:
        pairs = getaddresses([raw])
        formatted = []
        for name, addr in pairs:
            nm = _decode_mime_header(name) if name else ""
            ad = (addr or "").strip()
            if nm and ad:
                formatted.append(f"{nm} <{ad}>")
            elif ad:
                formatted.append(ad)
            elif nm:
                formatted.append(nm)
        return ", ".join(formatted)
    except Exception:
        return _decode_mime_header(raw)


def _parse_email_date(date_header: Optional[str]) -> Optional[datetime]:
    if not date_header:
        return None
    try:
        dt = parsedate_to_datetime(date_header)
        if dt is None:
            return None
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _extract_bodies(msg: email.message.Message) -> (str, str):
    """从邮件对象中提取纯文本与 HTML 正文（递归 multipart）。"""
    text_parts: List[str] = []
    html_parts: List[str] = []

    def _walk(part: email.message.Message):
        if part.is_multipart():
            for sub in part.get_payload() or []:
                _walk(sub)
            return
        ctype = (part.get_content_type() or "").lower()
        cdisp = (part.get("Content-Disposition") or "").lower()
        if "attachment" in cdisp:
            return
        payload = part.get_payload(decode=True)
        if payload is None:
            return
        charset = part.get_content_charset() or "utf-8"
        try:
            text = payload.decode(charset, errors="replace")
        except Exception:
            try:
                text = payload.decode("utf-8", errors="replace")
            except Exception:
                text = ""
        if ctype == "text/plain":
            text_parts.append(text)
        elif ctype == "text/html":
            html_parts.append(text)

    _walk(msg)

    body_text = "\n".join(t for t in text_parts if t).strip()
    body_html = "\n".join(h for h in html_parts if h).strip()

    # 若无纯文本正文，但有 HTML，则尝试把 HTML 转成简单文本作为补充
    if not body_text and body_html:
        body_text = _html_to_text(body_html)

    return body_text, body_html


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_WHITESPACE_RE = re.compile(r"[ \t]+")


def _html_to_text(html: str) -> str:
    if not html:
        return ""
    s = _HTML_STYLE_RE.sub("", html)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"</p\s*>", "\n", s, flags=re.IGNORECASE)
    s = _HTML_TAG_RE.sub("", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    s = _WHITESPACE_RE.sub(" ", s)
    s = re.sub(r"\n\s+\n", "\n\n", s)
    return s.strip()


def _insert_email_row(row: dict) -> bool:
    """写入一条邮件记录，若 message_id 冲突则跳过。返回是否新增。"""
    try:
        affected = db.execute_update(
            """
            INSERT IGNORE INTO inbox_emails
                (message_id, uid, subject, from_addr, to_addrs, cc_addrs,
                 email_date, body_text, body_html)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                row.get("message_id"),
                row.get("uid"),
                row.get("subject") or "",
                row.get("from_addr") or "",
                row.get("to_addrs") or "",
                row.get("cc_addrs") or "",
                row.get("email_date"),
                row.get("body_text") or "",
                row.get("body_html") or "",
            ),
        )
        return affected and affected > 0
    except Exception as e:
        logger.error(f"写入邮件记录失败: {e}")
        return False


# ==================== IMAP 拉取 ====================

def _sync_inbox_once(max_fetch: int = MAX_FETCH_PER_POLL) -> dict:
    """连接 IMAP 拉取邮件。返回 {new, skipped, total, error}"""
    cfg = _get_inbox_config()
    address = cfg["address"]
    auth_code = cfg["auth_code"]
    if not address or not auth_code:
        return {"new": 0, "skipped": 0, "total": 0, "error": "共用邮箱未配置"}

    result = {"new": 0, "skipped": 0, "total": 0, "error": None}
    imap_obj = None
    try:
        imap_obj = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT_SSL, timeout=30)
        imap_obj.login(address, auth_code)
        # 网易企业邮箱 IMAP 第一次登录需发送 ID 命令，否则部分场景收不到邮件
        try:
            imap_obj.xatom(
                "ID",
                '("name" "OA-InboxSync" "version" "1.0" "vendor" "myclient" "contact" "' + address + '")',
            )
        except Exception:
            pass
        imap_obj.select("INBOX", readonly=True)
        typ, data = imap_obj.search(None, "ALL")
        if typ != "OK" or not data or not data[0]:
            return result
        ids = data[0].split()
        result["total"] = len(ids)
        # 只取最新 max_fetch 封
        ids_to_fetch = ids[-max_fetch:] if max_fetch and len(ids) > max_fetch else ids

        # 先批量查 message_id 做去重（减少网络往返）
        existing_mids = set()
        try:
            rows = db.execute_query("SELECT message_id FROM inbox_emails", ())
            for r in rows or []:
                mid = r.get("message_id")
                if mid:
                    existing_mids.add(mid)
        except Exception:
            pass

        for seq_id in ids_to_fetch:
            try:
                # 先只取 header 判断 message-id 是否已存在，避免重复下载大邮件
                typ2, header_data = imap_obj.fetch(
                    seq_id, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])"
                )
                mid = None
                if typ2 == "OK" and header_data and header_data[0]:
                    raw_hdr = header_data[0][1] if isinstance(header_data[0], tuple) else b""
                    if raw_hdr:
                        try:
                            hm = email.message_from_bytes(raw_hdr)
                            mid = (hm.get("Message-ID") or "").strip() or None
                        except Exception:
                            mid = None
                if mid and mid in existing_mids:
                    result["skipped"] += 1
                    continue

                typ3, msg_data = imap_obj.fetch(seq_id, "(RFC822)")
                if typ3 != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw_msg = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
                if not raw_msg:
                    continue
                msg = email.message_from_bytes(raw_msg)

                message_id = (msg.get("Message-ID") or "").strip() or None
                if message_id and message_id in existing_mids:
                    result["skipped"] += 1
                    continue

                subject = _decode_mime_header(msg.get("Subject", ""))
                from_addr = _format_address_list(msg.get("From", ""))
                to_addrs = _format_address_list(msg.get("To", ""))
                cc_addrs = _format_address_list(msg.get("Cc", ""))
                email_dt = _parse_email_date(msg.get("Date"))
                body_text, body_html = _extract_bodies(msg)

                row = {
                    "message_id": message_id,
                    "uid": seq_id.decode() if isinstance(seq_id, bytes) else str(seq_id),
                    "subject": subject,
                    "from_addr": from_addr,
                    "to_addrs": to_addrs,
                    "cc_addrs": cc_addrs,
                    "email_date": email_dt,
                    "body_text": body_text,
                    "body_html": body_html,
                }
                if _insert_email_row(row):
                    result["new"] += 1
                    if message_id:
                        existing_mids.add(message_id)
                else:
                    result["skipped"] += 1
            except Exception as e:
                logger.warning(f"处理邮件 seq={seq_id} 失败: {e}")
                continue
    except imaplib.IMAP4.error as e:
        err = str(e)
        logger.error(f"IMAP 登录/操作失败: {err}")
        result["error"] = f"IMAP 操作失败：{err}"
    except Exception as e:
        logger.error(f"共用邮箱同步异常: {e}")
        result["error"] = str(e)
    finally:
        if imap_obj is not None:
            try:
                imap_obj.logout()
            except Exception:
                pass
    return result


# ==================== API ====================

class InboxConfigRequest(BaseModel):
    current_user: str
    email_address: str
    email_auth_code: str


@router.get("/config")
async def get_inbox_config(current_user: str = Query(...)):
    """获取共用邮箱配置（脱敏）"""
    _require_admin(current_user)
    cfg = _get_inbox_config()
    masked_addr = cfg["address"]
    ac = cfg["auth_code"]
    masked_code = ("*" * (len(ac) - 4) + ac[-4:]) if len(ac) > 4 else ("已配置" if ac else "")
    return {
        "success": True,
        "emailAddress": masked_addr,
        "authCodeMasked": masked_code,
        "configured": bool(cfg["address"] and cfg["auth_code"]),
        "imapServer": IMAP_SERVER,
        "imapPort": IMAP_PORT_SSL,
        "pollIntervalSeconds": POLL_INTERVAL_SECONDS,
    }


@router.post("/config")
async def update_inbox_config(req: InboxConfigRequest):
    """更新共用邮箱配置"""
    _require_admin(req.current_user)
    _ensure_inbox_columns()
    db.execute_update(
        "UPDATE webconfig SET inbox_email_address = %s, inbox_email_auth_code = %s WHERE id = %s",
        (req.email_address.strip(), req.email_auth_code.strip(), "1"),
    )
    return {"success": True, "message": "共用邮箱配置已更新"}


@router.get("/list")
async def list_inbox_emails(
    current_user: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: Optional[str] = Query(None, description="模糊搜索主题/发件人/正文"),
):
    """分页列出共用邮箱收到的邮件"""
    _require_admin(current_user)

    where = []
    params: list = []
    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        where.append("(subject LIKE %s OR from_addr LIKE %s OR to_addrs LIKE %s OR cc_addrs LIKE %s OR body_text LIKE %s)")
        params.extend([kw, kw, kw, kw, kw])

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    total_row = db.execute_query(f"SELECT COUNT(*) AS c FROM inbox_emails {where_sql}", tuple(params))
    total = int(total_row[0]["c"]) if total_row else 0

    offset = (page - 1) * page_size
    rows = db.execute_query(
        f"""
        SELECT id, message_id, subject, from_addr, to_addrs, cc_addrs,
               email_date, received_at,
               CHAR_LENGTH(body_text) AS body_text_len,
               CHAR_LENGTH(body_html) AS body_html_len
          FROM inbox_emails
          {where_sql}
          ORDER BY COALESCE(email_date, received_at) DESC, id DESC
          LIMIT %s OFFSET %s
        """,
        tuple(params) + (page_size, offset),
    )

    items = []
    for r in rows or []:
        items.append({
            "id": r.get("id"),
            "messageId": r.get("message_id") or "",
            "subject": r.get("subject") or "",
            "from": r.get("from_addr") or "",
            "to": r.get("to_addrs") or "",
            "cc": r.get("cc_addrs") or "",
            "emailDate": r["email_date"].strftime("%Y-%m-%d %H:%M:%S") if r.get("email_date") else "",
            "receivedAt": r["received_at"].strftime("%Y-%m-%d %H:%M:%S") if r.get("received_at") else "",
            "bodyTextLen": int(r.get("body_text_len") or 0),
            "bodyHtmlLen": int(r.get("body_html_len") or 0),
        })
    return {
        "success": True,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": items,
    }


@router.get("/detail")
async def inbox_email_detail(
    current_user: str = Query(...),
    id: int = Query(..., ge=1),
):
    """获取单封邮件详情（含全部正文）"""
    _require_admin(current_user)
    rows = db.execute_query(
        """
        SELECT id, message_id, subject, from_addr, to_addrs, cc_addrs,
               email_date, received_at, body_text, body_html
          FROM inbox_emails WHERE id = %s LIMIT 1
        """,
        (id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="邮件不存在")
    r = rows[0]
    return {
        "success": True,
        "item": {
            "id": r.get("id"),
            "messageId": r.get("message_id") or "",
            "subject": r.get("subject") or "",
            "from": r.get("from_addr") or "",
            "to": r.get("to_addrs") or "",
            "cc": r.get("cc_addrs") or "",
            "emailDate": r["email_date"].strftime("%Y-%m-%d %H:%M:%S") if r.get("email_date") else "",
            "receivedAt": r["received_at"].strftime("%Y-%m-%d %H:%M:%S") if r.get("received_at") else "",
            "bodyText": r.get("body_text") or "",
            "bodyHtml": r.get("body_html") or "",
        },
    }


@router.post("/sync")
async def manual_sync(current_user: str = Query(...)):
    """手动触发一次邮件同步"""
    _require_admin(current_user)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _sync_inbox_once, MAX_FETCH_PER_POLL)
    if result.get("error"):
        return {
            "success": False,
            "message": result["error"],
            "new": result.get("new", 0),
            "skipped": result.get("skipped", 0),
            "total": result.get("total", 0),
        }
    return {
        "success": True,
        "message": f"同步完成：新增 {result['new']} 封，跳过 {result['skipped']} 封（邮箱共 {result['total']} 封）",
        "new": result["new"],
        "skipped": result["skipped"],
        "total": result["total"],
    }


# ==================== 后台定时拉取 ====================

async def inbox_email_background_loop():
    """后台循环：按 POLL_INTERVAL_SECONDS 自动拉取共用邮箱"""
    logger.info("[InboxEmail] 后台自动拉取已启动，间隔 %s 秒", POLL_INTERVAL_SECONDS)
    print(f"[System] 共用邮箱自动拉取后台任务已启动（间隔 {POLL_INTERVAL_SECONDS}s）")
    while True:
        try:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            cfg = _get_inbox_config()
            if not cfg["address"] or not cfg["auth_code"]:
                continue
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _sync_inbox_once, MAX_FETCH_PER_POLL)
            if result.get("error"):
                logger.warning(f"[InboxEmail] 自动同步失败: {result['error']}")
            elif result["new"] > 0:
                logger.info(
                    f"[InboxEmail] 自动同步: 新增 {result['new']} 封 / 跳过 {result['skipped']} 封"
                )
        except Exception as e:
            logger.error(f"[InboxEmail] 后台循环异常: {e}")
            await asyncio.sleep(60)
