# -*- coding: utf-8 -*-
"""
共用邮箱收件箱 API - 仅系统管理员 (webconfig.admin1) 可使用
基于网易企业邮箱 IMAP SSL 从共用邮箱拉取邮件并存储到 inbox_emails 表
存储字段：主题、发件人、收件人、抄送人、发件时间、全部正文（纯文本 + HTML）
"""
import asyncio
import email
import imaplib
import json
import logging
import os
import re
from datetime import datetime

import httpx
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime, getaddresses
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inbox-email", tags=["共用邮箱收件箱"])

IMAP_SERVER = "imap.qiye.163.com"
#IMAP_SERVER = "imap.163.com"
IMAP_PORT_SSL = 993

# 后台轮询间隔（秒），可根据需要调整
POLL_INTERVAL_SECONDS = 15
# 单次拉取的最多邮件数（仅取最新标旗邮件）
MAX_FETCH_PER_POLL = 50

# LLM 任务抽取相关
ANALYZE_INTERVAL_SECONDS = 60            # 后台分析轮询间隔
ANALYZE_BATCH_SIZE = 5                   # 每轮最多分析多少封
ANALYZE_BODY_MAX_CHARS = 4000            # 送入模型的正文最大字符数
ANALYSIS_STATUS_PENDING = "pending"
ANALYSIS_STATUS_SUCCESS = "success"
ANALYSIS_STATUS_NO_TASK = "no_task"
ANALYSIS_STATUS_FAILED = "failed"

# 联网模型（DeepSeek）兜底配置
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"


# ==================== 建表 / 字段保障 ====================

def _column_exists(table: str, column: str) -> bool:
    """检查表中某列是否已存在。"""
    try:
        rows = db.execute_query(
            "SELECT 1 FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s LIMIT 1",
            (table, column),
        )
        return bool(rows)
    except Exception:
        return False


def _index_exists(table: str, index_name: str) -> bool:
    """检查表中某索引是否已存在。"""
    try:
        rows = db.execute_query(
            "SELECT 1 FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s LIMIT 1",
            (table, index_name),
        )
        return bool(rows)
    except Exception:
        return False


def _safe_add_column(table: str, col: str, typedef: str):
    """仅在列不存在时添加，不会产生 ERROR 日志。"""
    if not _column_exists(table, col):
        try:
            db.execute_update(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}", ())
        except Exception:
            pass


def _ensure_inbox_columns():
    for col, typedef in [
        ("inbox_email_address", "VARCHAR(200) DEFAULT ''"),
        ("inbox_email_auth_code", "VARCHAR(200) DEFAULT ''"),
    ]:
        _safe_add_column("webconfig", col, typedef)


def _ensure_yggl_email_columns():
    for col, typedef in [
        ("enterprise_email", "VARCHAR(255) DEFAULT NULL COMMENT '企业邮箱地址'"),
        ("email_auth_code", "VARCHAR(200) DEFAULT '' COMMENT '企业邮箱IMAP授权码'"),
    ]:
        _safe_add_column("yggl", col, typedef)


def _ensure_inbox_task_columns():
    for col, typedef in [
        ("has_task", "TINYINT(1) DEFAULT 0 COMMENT '是否包含待办任务'"),
        ("task_summary", "TEXT COMMENT '任务摘要（大模型抽取）'"),
        ("task_deadline", "VARCHAR(50) DEFAULT '' COMMENT '任务截止时间（文本）'"),
        ("task_analysis_status", "VARCHAR(20) DEFAULT 'pending' COMMENT '分析状态：pending/success/no_task/failed'"),
        ("task_analyzed_at", "DATETIME DEFAULT NULL COMMENT '最近一次分析时间'"),
        ("task_analysis_error", "TEXT COMMENT '最近一次分析的错误信息（若失败）'"),
    ]:
        _safe_add_column("inbox_emails", col, typedef)


def _ensure_inbox_owner_column():
    _safe_add_column("inbox_emails", "owner", "VARCHAR(100) DEFAULT '' COMMENT '所属用户（yggl.name）'")

    if not _index_exists("inbox_emails", "idx_owner"):
        try:
            db.execute_update("ALTER TABLE inbox_emails ADD INDEX idx_owner (owner)", ())
        except Exception:
            pass

    if _index_exists("inbox_emails", "uk_message_id"):
        try:
            db.execute_update("ALTER TABLE inbox_emails DROP INDEX uk_message_id", ())
        except Exception:
            pass

    if not _index_exists("inbox_emails", "uk_message_id_owner"):
        try:
            db.execute_update(
                "ALTER TABLE inbox_emails ADD UNIQUE KEY uk_message_id_owner (message_id, owner)",
                (),
            )
        except Exception:
            pass

    try:
        admin1 = _get_admin1()
        if admin1:
            db.execute_update(
                "UPDATE inbox_emails SET owner = %s WHERE owner IS NULL OR owner = ''",
                (admin1,),
            )
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
_ensure_yggl_email_columns()
_ensure_inbox_table()
_ensure_inbox_task_columns()
_ensure_inbox_owner_column()


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


def _has_inbox_role(current_user: str) -> bool:
    """
    共用邮箱权限：
    - 系统管理员（admin1）
    - yggl.jb 为 经理/副经理/主任/副主任/组长（含前缀）
    """
    name = (current_user or "").strip()
    if not name:
        return False
    admin1 = _get_admin1()
    if admin1 and name == admin1:
        return True
    try:
        rows = db.execute_query(
            "SELECT jb FROM yggl WHERE TRIM(name) = %s LIMIT 1",
            (name,),
        ) or []
        jb = (rows[0].get("jb") or "").strip() if rows else ""
        if not jb:
            return False
        allowed_prefixes = ("经理", "副经理", "主任", "副主任", "组长")
        return any(jb.startswith(p) for p in allowed_prefixes)
    except Exception:
        return False


def _require_inbox_access(current_user: str):
    if not _has_inbox_role(current_user):
        raise HTTPException(status_code=403, detail="仅系统管理员、经理/副经理、主任/副主任、组长可操作")


def _get_inbox_config(current_user: str) -> dict:
    _ensure_yggl_email_columns()
    name = (current_user or "").strip()
    if not name:
        return {"address": "", "auth_code": ""}
    try:
        rows = db.execute_query(
            "SELECT enterprise_email, email_auth_code FROM yggl WHERE name = %s LIMIT 1",
            (name,),
        )
        if rows:
            return {
                "address": (rows[0].get("enterprise_email") or "").strip(),
                "auth_code": (rows[0].get("email_auth_code") or "").strip(),
            }
    except Exception as e:
        logger.debug(f"读取 yggl 企业邮箱配置失败: {e}")
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


def _insert_email_row(row: dict, owner: str = "") -> bool:
    """写入一条邮件记录，若 (message_id, owner) 冲突则跳过。返回是否新增。"""
    try:
        affected = db.execute_update(
            """
            INSERT IGNORE INTO inbox_emails
                (message_id, uid, subject, from_addr, to_addrs, cc_addrs,
                 email_date, body_text, body_html, owner)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                owner,
            ),
        )
        return affected and affected > 0
    except Exception as e:
        logger.error(f"写入邮件记录失败: {e}")
        return False


# ==================== IMAP 拉取 ====================

def _sync_inbox_once(max_fetch: int = MAX_FETCH_PER_POLL, current_user: str = "") -> dict:
    """
    连接 IMAP 拉取 FLAGGED 邮件。
    单次遍历：逐封取 header 判重，新邮件才下载全文。
    清理逻辑：仅在完整获取了所有旗帜邮件 message_id 后才执行。
    """
    cfg = _get_inbox_config(current_user)
    address = cfg["address"]
    auth_code = cfg["auth_code"]
    if not address or not auth_code:
        return {"new": 0, "skipped": 0, "total": 0, "removed": 0, "error": "邮箱未配置"}

    result = {"new": 0, "skipped": 0, "total": 0, "removed": 0, "error": None}
    owner_name = (current_user or "").strip()
    imap_obj = None
    try:
        imap_obj = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT_SSL, timeout=60)
        imap_obj.login(address, auth_code)
        try:
            imap_obj.xatom(
                "ID",
                '("name" "OA-InboxSync" "version" "1.0" "vendor" "myclient" "contact" "' + address + '")',
            )
        except Exception:
            pass
        imap_obj.select("INBOX", readonly=True)
        typ, data = imap_obj.search(None, "FLAGGED")

        if typ != "OK":
            logger.warning(f"[InboxEmail] [{owner_name}] IMAP SEARCH 异常 typ={typ}，跳过本轮")
            return result

        ids = []
        if data and data[0]:
            ids = data[0].split()
        result["total"] = len(ids)
        ids_to_fetch = ids[-max_fetch:] if max_fetch and len(ids) > max_fetch else ids

        # 数据库中该用户已有的 message_id
        existing_mids = set()
        try:
            rows = db.execute_query(
                "SELECT message_id FROM inbox_emails WHERE owner = %s",
                (owner_name,),
            )
            for r in rows or []:
                mid = r.get("message_id")
                if mid:
                    existing_mids.add(mid)
        except Exception:
            pass

        # 单次遍历：取 header → 判重 → 新邮件下载全文
        flagged_mids_in_imap: set = set()
        scan_failures = 0
        for seq_id in ids_to_fetch:
            try:
                # 先只取 Message-ID header（几十字节，快速）
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

                if mid:
                    flagged_mids_in_imap.add(mid)

                if mid and mid in existing_mids:
                    result["skipped"] += 1
                    continue

                # 新邮件：下载完整内容（可能较大，超时设 60s）
                typ3, msg_data = imap_obj.fetch(seq_id, "(RFC822)")
                if typ3 != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw_msg = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
                if not raw_msg:
                    continue
                msg = email.message_from_bytes(raw_msg)

                message_id = (msg.get("Message-ID") or "").strip() or None
                if message_id:
                    flagged_mids_in_imap.add(message_id)
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
                if _insert_email_row(row, owner=owner_name):
                    result["new"] += 1
                    if message_id:
                        existing_mids.add(message_id)
                else:
                    result["skipped"] += 1
            except Exception as e:
                scan_failures += 1
                logger.warning(f"[InboxEmail] [{owner_name}] 处理邮件 seq={seq_id} 失败: {e}")
                continue

        # 清理已取消旗帜的邮件
        # 安全条件：无扫描失败 且 未被 max_fetch 截断（IMAP 搜索结果完整）
        fetched_all = (len(ids) <= max_fetch) if max_fetch else True
        can_cleanup = scan_failures == 0 and fetched_all
        if can_cleanup and existing_mids:
            unflagged_mids = existing_mids - flagged_mids_in_imap
            if unflagged_mids:
                for uf_mid in unflagged_mids:
                    try:
                        db.execute_update(
                            "DELETE FROM inbox_emails WHERE message_id = %s AND owner = %s",
                            (uf_mid, owner_name),
                        )
                        result["removed"] += 1
                    except Exception as e:
                        logger.warning(f"删除已取消旗帜邮件失败 mid={uf_mid}: {e}")
                if result["removed"]:
                    logger.info(
                        f"[InboxEmail] [{owner_name}] 清理已取消旗帜邮件 {result['removed']} 封"
                    )
        elif existing_mids and scan_failures > 0:
            logger.warning(
                f"[InboxEmail] [{owner_name}] 有 {scan_failures} 封邮件处理失败，跳过旗帜清理（保护现有 {len(existing_mids)} 条数据）"
            )

    except imaplib.IMAP4.error as e:
        err = str(e)
        logger.error(f"[InboxEmail] [{owner_name}] IMAP 登录/操作失败: {err}")
        result["error"] = f"IMAP 操作失败：{err}"
    except (OSError, TimeoutError) as e:
        logger.error(f"[InboxEmail] [{owner_name}] 网络连接异常: {e}")
        result["error"] = f"网络连接异常：{e}"
    except Exception as e:
        logger.error(f"[InboxEmail] [{owner_name}] 邮箱同步异常: {e}")
        result["error"] = str(e)
    finally:
        if imap_obj is not None:
            try:
                imap_obj.logout()
            except Exception:
                pass
    return result


# ==================== LLM 任务抽取 ====================

def _build_task_prompts(row: dict) -> tuple:
    """基于邮件内容构建任务抽取的 system/user prompt（已关闭 Qwen3 思考模式）。"""
    subject = (row.get("subject") or "").strip() or "（无主题）"
    from_addr = (row.get("from_addr") or "").strip() or "（未知发件人）"
    email_date = row.get("email_date")
    date_str = email_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(email_date, datetime) else "（未知）"

    body = (row.get("body_text") or "").strip()
    if not body:
        body = _html_to_text(row.get("body_html") or "")
    if len(body) > ANALYZE_BODY_MAX_CHARS:
        body = body[:ANALYZE_BODY_MAX_CHARS] + "\n……（正文过长已截断）"

    system_prompt = (
        "你是一名企业助理，负责从一封邮件中判断是否存在需要收件人处理的任务或待办事项，"
        "并提取出任务的简要描述和截止时间。\n"
        "判断规则：\n"
        "1. 通知、广告、系统提醒、安全提醒、验证码、订阅推送、聊天寒暄等，均视为无任务；\n"
        "2. 要求收件人完成某项工作、上报资料、回复确认、参加会议、提交审批、在特定时间前完成的，视为有任务；\n"
        "3. 任务摘要尽量简短（不超过 50 个汉字），用一句话说明“谁/什么事”，不要照抄全文。\n"
        "4. 截止时间只输出一个，格式优先 YYYY-MM-DD 或 YYYY-MM-DD HH:mm；若邮件没有明确截止时间，请留空字符串。\n"
        "5. 输出严格的 JSON，不要解释、不要 markdown、不要思考过程，不要使用 <think> 标签。\n"
        "/no_think"
    )
    user_prompt = (
        f"邮件信息：\n"
        f"- 发件人：{from_addr}\n"
        f"- 发件时间：{date_str}\n"
        f"- 主题：{subject}\n"
        f"- 正文：\n{body}\n\n"
        "请严格按下面的 JSON 输出：\n"
        "{\n"
        '  "has_task": true 或 false,\n'
        '  "task": "任务的一句话摘要，若 has_task=false 则为空字符串",\n'
        '  "deadline": "YYYY-MM-DD 或 YYYY-MM-DD HH:mm，若未明确给出则为空字符串"\n'
        "}\n"
        "/no_think"
    )
    return system_prompt, user_prompt


def _parse_llm_task_content(content: str) -> dict:
    """从大模型返回中鲁棒地解析任务 JSON。"""
    text = (content or "").strip()
    if not text:
        raise ValueError("模型返回为空")

    if "<think>" in text.lower() and "</think>" in text.lower():
        end = text.lower().find("</think>") + len("</think>")
        text = text[end:].strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    # 扫描最长的大括号对
    stack: List[int] = []
    best = (-1, -1)
    for i, ch in enumerate(text):
        if ch == "{":
            stack.append(i)
        elif ch == "}" and stack:
            start = stack.pop()
            if not stack and (i - start) > (best[1] - best[0]):
                best = (start, i)
    if best[0] != -1:
        try:
            return json.loads(text[best[0]: best[1] + 1])
        except Exception:
            pass

    # 去除代码块再试一次
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9]*", "", text).strip()
        if text.endswith("```"):
            text = text[:-3].strip()
        try:
            return json.loads(text)
        except Exception:
            pass

    raise ValueError("无法解析为 JSON")


def _analyze_email_with_llm(row: dict) -> dict:
    """调用本地大模型抽取单封邮件的任务信息。返回 dict 或抛异常。"""
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("服务端未安装 openai SDK") from e

    system_prompt, user_prompt = _build_task_prompts(row)
    config = _get_inbox_llm_config()

    data = None
    local_err = None
    use_fallback = False

    # 1) 优先本地大模型
    if config.get("local_base_url") and config.get("local_model"):
        try:
            local_client = OpenAI(
                base_url=config["local_base_url"],
                api_key="ollama",
                max_retries=0,
                timeout=httpx.Timeout(15.0, connect=5.0),
            )
            completion = local_client.chat.completions.create(
                model=config["local_model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                stream=False,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            content = (completion.choices[0].message.content or "").strip()
            data = _parse_llm_task_content(content)
        except Exception as e:
            local_err = str(e)
            use_fallback = True
            logger.warning("[InboxEmail] 本地大模型不可用，尝试 DeepSeek 兜底: %s", e)
    else:
        use_fallback = True

    # 2) 本地不可用时，兜底 DeepSeek 联网模型
    if data is None and use_fallback:
        api_key = config.get("deepseek_api_key")
        if not api_key:
            if local_err:
                raise RuntimeError(f"本地大模型不可用，且未配置 DeepSeek API Key: {local_err}")
            raise RuntimeError("未配置可用大模型：请配置本地 llm_base_url/llm_model 或 deepseek_api_key")
        deepseek_client = OpenAI(
            base_url=DEEPSEEK_BASE_URL,
            api_key=api_key,
            max_retries=1,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        completion = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            stream=False,
        )
        content = (completion.choices[0].message.content or "").strip()
        data = _parse_llm_task_content(content)

    has_task = bool(data.get("has_task"))
    task_summary = str(data.get("task") or "").strip()
    deadline = str(data.get("deadline") or "").strip()
    if not has_task:
        task_summary = ""
        deadline = ""
    # 任务摘要限长，防止模型没遵守提示
    if len(task_summary) > 500:
        task_summary = task_summary[:500]
    return {
        "has_task": 1 if has_task and task_summary else 0,
        "task_summary": task_summary,
        "task_deadline": deadline,
    }


def _normalize_llm_base_url(url: str) -> str:
    """兼容填入 /chat/completions 的情况；OpenAI SDK 只需要根路径，最多到 /v1。"""
    u = (url or "").strip()
    if not u:
        return ""
    u = u.rstrip("/")
    if u.endswith("/chat/completions"):
        u = u[: -len("/chat/completions")].rstrip("/")
    return u


def _get_inbox_llm_config() -> dict:
    """读取 inbox 分析用的大模型配置：本地优先，DeepSeek 作为兜底。"""
    # 复用 holiday 的本地模型配置（有默认值）
    local_base_url = ""
    local_model = ""
    try:
        from routers.holiday import _get_llm_config
        cfg = _get_llm_config() or {}
        local_base_url = _normalize_llm_base_url(cfg.get("base_url") or "")
        local_model = (cfg.get("model") or "").strip()
    except Exception as e:
        logger.debug("读取本地大模型配置失败: %s", e)

    deepseek_api_key = ""
    try:
        rows = db.execute_query(
            "SELECT deepseek_api_key FROM webconfig WHERE id = %s LIMIT 1",
            ("1",),
        )
        if rows:
            deepseek_api_key = (rows[0].get("deepseek_api_key") or "").strip()
    except Exception as e:
        logger.debug("读取 webconfig.deepseek_api_key 失败: %s", e)
    if not deepseek_api_key:
        deepseek_api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()

    return {
        "local_base_url": local_base_url,
        "local_model": local_model,
        "deepseek_api_key": deepseek_api_key,
    }


def _update_email_analysis(
    email_id: int,
    has_task: int,
    task_summary: str,
    task_deadline: str,
    status: str,
    error: str = "",
) -> None:
    try:
        db.execute_update(
            """
            UPDATE inbox_emails SET
              has_task = %s,
              task_summary = %s,
              task_deadline = %s,
              task_analysis_status = %s,
              task_analyzed_at = %s,
              task_analysis_error = %s
            WHERE id = %s
            """,
            (
                int(has_task or 0),
                task_summary or "",
                task_deadline or "",
                status,
                datetime.now(),
                error or "",
                email_id,
            ),
        )
    except Exception as e:
        logger.error(f"更新邮件分析结果失败 id={email_id}: {e}")


def _analyze_pending_emails(limit: int = ANALYZE_BATCH_SIZE, owner: str = "") -> dict:
    """从库里挑出指定用户的 pending 或 failed 邮件，逐封调用大模型分析。"""
    _ensure_inbox_task_columns()
    summary = {"analyzed": 0, "has_task": 0, "no_task": 0, "failed": 0}
    owner_filter = (owner or "").strip()
    try:
        if owner_filter:
            rows = db.execute_query(
                """
                SELECT id, subject, from_addr, email_date, body_text, body_html
                  FROM inbox_emails
                 WHERE owner = %s
                   AND (task_analysis_status IS NULL
                        OR task_analysis_status = %s
                        OR task_analysis_status = %s)
                 ORDER BY COALESCE(email_date, received_at) DESC, id DESC
                 LIMIT %s
                """,
                (owner_filter, ANALYSIS_STATUS_PENDING, ANALYSIS_STATUS_FAILED, int(limit)),
            ) or []
        else:
            rows = db.execute_query(
                """
                SELECT id, subject, from_addr, email_date, body_text, body_html
                  FROM inbox_emails
                 WHERE task_analysis_status IS NULL
                    OR task_analysis_status = %s
                    OR task_analysis_status = %s
                 ORDER BY COALESCE(email_date, received_at) DESC, id DESC
                 LIMIT %s
                """,
                (ANALYSIS_STATUS_PENDING, ANALYSIS_STATUS_FAILED, int(limit)),
            ) or []
    except Exception as e:
        logger.error(f"查询待分析邮件失败: {e}")
        return summary

    for r in rows:
        try:
            result = _analyze_email_with_llm(r)
            if result.get("has_task"):
                _update_email_analysis(
                    r["id"], 1, result["task_summary"], result["task_deadline"],
                    ANALYSIS_STATUS_SUCCESS, "",
                )
                summary["has_task"] += 1
            else:
                _update_email_analysis(
                    r["id"], 0, "", "", ANALYSIS_STATUS_NO_TASK, "",
                )
                summary["no_task"] += 1
            summary["analyzed"] += 1
        except Exception as e:
            msg = str(e)[:500]
            logger.warning(f"[InboxEmail] 邮件 id={r.get('id')} 分析失败: {msg}")
            _update_email_analysis(r["id"], 0, "", "", ANALYSIS_STATUS_FAILED, msg)
            summary["failed"] += 1
    return summary


def _claim_orphan_emails(owner: str):
    """将数据库中 owner 为空的邮件自动归属给当前用户（一次性迁移兜底）。"""
    if not owner:
        return
    try:
        affected = db.execute_update(
            "UPDATE inbox_emails SET owner = %s WHERE owner IS NULL OR owner = ''",
            (owner,),
        )
        if affected and affected > 0:
            logger.info(f"[InboxEmail] 自动认领 {affected} 封无主邮件给 [{owner}]")
    except Exception:
        pass


def _owner_filter_sql() -> str:
    """返回兼容空 owner 的 WHERE 条件片段。"""
    return "(owner = %s OR owner IS NULL OR owner = '')"


# ==================== API ====================

class InboxConfigRequest(BaseModel):
    current_user: str
    email_address: str
    email_auth_code: str


@router.get("/config")
async def get_inbox_config(current_user: str = Query(...)):
    """获取共用邮箱配置（脱敏）"""
    _require_inbox_access(current_user)
    cfg = _get_inbox_config(current_user)
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
    _require_inbox_access(req.current_user)
    _ensure_yggl_email_columns()
    affected = db.execute_update(
        "UPDATE yggl SET enterprise_email = %s, email_auth_code = %s WHERE name = %s",
        (req.email_address.strip(), req.email_auth_code.strip(), req.current_user.strip()),
    )
    if affected is not None and affected <= 0:
        raise HTTPException(status_code=404, detail="未找到当前管理员的员工记录")
    return {"success": True, "message": "共用邮箱配置已更新"}


@router.get("/list")
async def list_inbox_emails(
    current_user: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: Optional[str] = Query(None, description="模糊搜索主题/发件人/正文"),
):
    """分页列出当前用户邮箱收到的邮件"""
    _require_inbox_access(current_user)
    owner = (current_user or "").strip()
    _claim_orphan_emails(owner)

    where = [_owner_filter_sql()]
    params: list = [owner]
    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        where.append("(subject LIKE %s OR from_addr LIKE %s OR to_addrs LIKE %s OR cc_addrs LIKE %s OR body_text LIKE %s)")
        params.extend([kw, kw, kw, kw, kw])

    where_sql = f"WHERE {' AND '.join(where)}"

    total_row = db.execute_query(f"SELECT COUNT(*) AS c FROM inbox_emails {where_sql}", tuple(params))
    total = int(total_row[0]["c"]) if total_row else 0

    offset = (page - 1) * page_size
    rows = db.execute_query(
        f"""
        SELECT id, message_id, subject, from_addr, to_addrs, cc_addrs,
               email_date, received_at,
               CHAR_LENGTH(body_text) AS body_text_len,
               CHAR_LENGTH(body_html) AS body_html_len,
               has_task, task_summary, task_deadline, task_analysis_status, task_analyzed_at
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
            "hasTask": int(r.get("has_task") or 0),
            "taskSummary": r.get("task_summary") or "",
            "taskDeadline": r.get("task_deadline") or "",
            "taskAnalysisStatus": r.get("task_analysis_status") or "pending",
            "taskAnalyzedAt": r["task_analyzed_at"].strftime("%Y-%m-%d %H:%M:%S") if r.get("task_analyzed_at") else "",
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
    _require_inbox_access(current_user)
    owner = (current_user or "").strip()
    rows = db.execute_query(
        f"""
        SELECT id, message_id, subject, from_addr, to_addrs, cc_addrs,
               email_date, received_at, body_text, body_html
          FROM inbox_emails WHERE id = %s AND {_owner_filter_sql()} LIMIT 1
        """,
        (id, owner),
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


@router.get("/tasks")
async def list_inbox_tasks(
    current_user: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
):
    """
    列出已被大模型识别为“含任务”的邮件，按截止时间优先、其次按发件时间排序。
    用于前端看板滚动展示。
    """
    _require_inbox_access(current_user)
    _ensure_inbox_task_columns()
    owner = (current_user or "").strip()
    _claim_orphan_emails(owner)

    sql = f"""
        SELECT id, subject, from_addr, email_date, received_at,
               task_summary, task_deadline, task_analyzed_at
          FROM inbox_emails
         WHERE {_owner_filter_sql()}
           AND has_task = 1 AND task_summary IS NOT NULL AND task_summary <> ''
         ORDER BY
            CASE WHEN task_deadline IS NULL OR task_deadline = '' THEN 1 ELSE 0 END ASC,
            task_deadline ASC,
            COALESCE(email_date, received_at) DESC
         LIMIT %s
    """
    rows = db.execute_query(sql, (owner, int(limit))) or []
    items = []
    for r in rows:
        items.append({
            "id": r.get("id"),
            "subject": r.get("subject") or "",
            "from": r.get("from_addr") or "",
            "emailDate": r["email_date"].strftime("%Y-%m-%d %H:%M:%S") if r.get("email_date") else "",
            "receivedAt": r["received_at"].strftime("%Y-%m-%d %H:%M:%S") if r.get("received_at") else "",
            "taskSummary": r.get("task_summary") or "",
            "taskDeadline": r.get("task_deadline") or "",
            "taskAnalyzedAt": r["task_analyzed_at"].strftime("%Y-%m-%d %H:%M:%S") if r.get("task_analyzed_at") else "",
        })

    stat_rows = db.execute_query(
        f"""
        SELECT
          SUM(CASE WHEN task_analysis_status = 'pending' OR task_analysis_status IS NULL THEN 1 ELSE 0 END) AS pending_count,
          SUM(CASE WHEN task_analysis_status = 'failed' THEN 1 ELSE 0 END) AS failed_count,
          SUM(CASE WHEN has_task = 1 THEN 1 ELSE 0 END) AS task_count,
          COUNT(*) AS total
          FROM inbox_emails
         WHERE {_owner_filter_sql()}
        """,
        (owner,),
    )
    pending_count = int(stat_rows[0].get("pending_count") or 0) if stat_rows else 0
    failed_count = int(stat_rows[0].get("failed_count") or 0) if stat_rows else 0
    task_count = int(stat_rows[0].get("task_count") or 0) if stat_rows else 0
    total = int(stat_rows[0].get("total") or 0) if stat_rows else 0

    return {
        "success": True,
        "items": items,
        "stats": {
            "pending": pending_count,
            "failed": failed_count,
            "taskCount": task_count,
            "total": total,
        },
    }


@router.post("/analyze")
async def analyze_inbox_emails(
    current_user: str = Query(...),
    id: Optional[int] = Query(None, description="指定邮件ID则仅分析该邮件，否则批量分析 pending/failed"),
    limit: int = Query(ANALYZE_BATCH_SIZE, ge=1, le=50),
):
    """手动触发大模型任务抽取。"""
    _require_inbox_access(current_user)
    owner = (current_user or "").strip()
    loop = asyncio.get_event_loop()

    if id is not None:
        def _run_single():
            rows = db.execute_query(
                f"SELECT id, subject, from_addr, email_date, body_text, body_html FROM inbox_emails WHERE id = %s AND {_owner_filter_sql()} LIMIT 1",
                (int(id), owner),
            )
            if not rows:
                return {"error": "邮件不存在"}
            r = rows[0]
            try:
                result = _analyze_email_with_llm(r)
            except Exception as e:
                msg = str(e)[:500]
                _update_email_analysis(r["id"], 0, "", "", ANALYSIS_STATUS_FAILED, msg)
                return {"error": msg}
            if result.get("has_task"):
                _update_email_analysis(
                    r["id"], 1, result["task_summary"], result["task_deadline"],
                    ANALYSIS_STATUS_SUCCESS, "",
                )
            else:
                _update_email_analysis(r["id"], 0, "", "", ANALYSIS_STATUS_NO_TASK, "")
            return {
                "hasTask": int(result.get("has_task") or 0),
                "taskSummary": result.get("task_summary") or "",
                "taskDeadline": result.get("task_deadline") or "",
            }

        res = await loop.run_in_executor(None, _run_single)
        if res.get("error"):
            return {"success": False, "message": res["error"]}
        return {"success": True, "message": "分析完成", **res}

    def _run_batch():
        return _analyze_pending_emails(limit=int(limit), owner=owner)
    summary = await loop.run_in_executor(None, _run_batch)
    return {
        "success": True,
        "message": (
            f"本轮分析完成：新增任务 {summary.get('has_task', 0)} 封 / "
            f"无任务 {summary.get('no_task', 0)} 封 / "
            f"失败 {summary.get('failed', 0)} 封"
        ),
        **summary,
    }


@router.post("/sync")
async def manual_sync(current_user: str = Query(...)):
    """手动触发一次邮件同步，有新邮件则立即分析"""
    _require_inbox_access(current_user)
    owner = (current_user or "").strip()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _sync_inbox_once, MAX_FETCH_PER_POLL, current_user)
    if result.get("error"):
        return {
            "success": False,
            "message": result["error"],
            "new": result.get("new", 0),
            "skipped": result.get("skipped", 0),
            "total": result.get("total", 0),
        }

    analyze_msg = ""
    if result["new"] > 0:
        try:
            def _run_analyze():
                return _analyze_pending_emails(limit=result["new"], owner=owner)
            summary = await loop.run_in_executor(None, _run_analyze)
            analyzed = summary.get("analyzed", 0)
            has_task = summary.get("has_task", 0)
            if analyzed:
                analyze_msg = f"，已自动分析 {analyzed} 封（识别出 {has_task} 个任务）"
        except Exception as e:
            logger.warning(f"[InboxEmail] 手动同步后即时分析失败: {e}")

    # 查询数据库中该用户当前实际邮件数
    db_count = 0
    try:
        cnt_rows = db.execute_query(
            "SELECT COUNT(*) AS cnt FROM inbox_emails WHERE owner = %s",
            (owner,),
        )
        if cnt_rows:
            db_count = cnt_rows[0].get("cnt", 0)
    except Exception:
        pass

    return {
        "success": True,
        "message": f"同步完成：新增 {result['new']} 封，跳过 {result['skipped']} 封，移除 {result.get('removed', 0)} 封（当前库中 {db_count} 封）{analyze_msg}",
        "new": result["new"],
        "skipped": result["skipped"],
        "removed": result.get("removed", 0),
        "total": db_count,
    }


@router.post("/complete")
async def complete_inbox_task(
    current_user: str = Query(...),
    id: int = Query(..., ge=1, description="inbox_emails 表的 id"),
):
    """
    标记任务已完成：
    1. 连接 IMAP 去除该邮件的 \\Flagged 旗帜
    2. 从 inbox_emails 表中删除该记录
    """
    _require_inbox_access(current_user)
    owner = (current_user or "").strip()

    rows = db.execute_query(
        f"SELECT id, message_id FROM inbox_emails WHERE id = %s AND {_owner_filter_sql()} LIMIT 1",
        (int(id), owner),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="邮件记录不存在")
    row = rows[0]
    message_id = (row.get("message_id") or "").strip()

    cfg = _get_inbox_config(current_user)
    imap_error = None
    if cfg["address"] and cfg["auth_code"] and message_id:
        loop = asyncio.get_event_loop()
        imap_error = await loop.run_in_executor(
            None, _unflag_email_imap, cfg["address"], cfg["auth_code"], message_id
        )

    try:
        db.execute_update(
            f"DELETE FROM inbox_emails WHERE id = %s AND {_owner_filter_sql()}",
            (int(id), owner),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除邮件记录失败: {e}")

    msg = "任务已完成，邮件旗帜已移除"
    if imap_error:
        msg = f"任务已完成（数据库已删除，但去除旗帜失败：{imap_error}）"
    return {"success": True, "message": msg}


def _unflag_email_imap(address: str, auth_code: str, message_id: str) -> Optional[str]:
    """连接 IMAP 找到指定 message_id 的邮件并去除 \\Flagged 标记。返回错误信息或 None。"""
    imap_obj = None
    try:
        imap_obj = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT_SSL, timeout=30)
        imap_obj.login(address, auth_code)
        try:
            imap_obj.xatom(
                "ID",
                '("name" "OA-InboxSync" "version" "1.0" "vendor" "myclient" "contact" "' + address + '")',
            )
        except Exception:
            pass
        imap_obj.select("INBOX", readonly=False)

        # 通过 HEADER 搜索 Message-ID
        clean_mid = message_id.strip().strip("<>")
        typ, data = imap_obj.search(None, f'HEADER Message-ID "<{clean_mid}>"')
        if typ != "OK" or not data or not data[0]:
            return f"IMAP 中未找到 Message-ID={message_id}"

        seq_ids = data[0].split()
        for seq_id in seq_ids:
            imap_obj.store(seq_id, "-FLAGS", "\\Flagged")

        return None
    except Exception as e:
        return str(e)
    finally:
        if imap_obj is not None:
            try:
                imap_obj.logout()
            except Exception:
                pass


# ==================== 后台定时拉取 ====================

def _get_all_configured_users() -> list:
    """获取所有已配置企业邮箱的用户列表 [{name, enterprise_email, email_auth_code}]"""
    try:
        rows = db.execute_query(
            """
            SELECT name, enterprise_email, email_auth_code
              FROM yggl
             WHERE enterprise_email IS NOT NULL AND enterprise_email <> ''
               AND email_auth_code IS NOT NULL AND email_auth_code <> ''
            """,
            (),
        )
        return rows or []
    except Exception as e:
        logger.debug(f"查询已配置邮箱用户失败: {e}")
        return []


async def inbox_email_background_loop():
    """后台循环：遍历所有已配置企业邮箱的用户，定期自动拉取邮件，有新邮件则立即分析"""
    logger.info("[InboxEmail] 后台自动拉取+分析已启动，间隔 %s 秒", POLL_INTERVAL_SECONDS)
    print(f"[System] 邮箱自动拉取+分析后台任务已启动（间隔 {POLL_INTERVAL_SECONDS}s）")
    while True:
        try:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            users = _get_all_configured_users()
            if not users:
                continue
            loop = asyncio.get_event_loop()
            total_new = 0
            for u in users:
                uname = (u.get("name") or "").strip()
                if not uname:
                    continue
                try:
                    result = await loop.run_in_executor(
                        None, _sync_inbox_once, MAX_FETCH_PER_POLL, uname
                    )
                    if result.get("error"):
                        logger.warning(f"[InboxEmail] 自动同步 [{uname}] 失败: {result['error']}")
                    elif result["new"] > 0:
                        total_new += result["new"]
                        logger.info(
                            f"[InboxEmail] 自动同步 [{uname}]: 新增 {result['new']} 封 / 跳过 {result['skipped']} 封"
                        )
                except Exception as e:
                    logger.warning(f"[InboxEmail] 自动同步 [{uname}] 异常: {e}")

            # 有新邮件入库则立即触发分析，无需等待下一轮
            if total_new > 0:
                try:
                    summary = await loop.run_in_executor(
                        None, _analyze_pending_emails, max(total_new, ANALYZE_BATCH_SIZE)
                    )
                    if summary.get("analyzed"):
                        logger.info(
                            "[InboxEmail] 同步后即时分析：%s 封（任务 %s / 无任务 %s / 失败 %s）",
                            summary.get("analyzed"),
                            summary.get("has_task"),
                            summary.get("no_task"),
                            summary.get("failed"),
                        )
                except Exception as e:
                    logger.warning(f"[InboxEmail] 同步后即时分析异常: {e}")
        except Exception as e:
            logger.error(f"[InboxEmail] 后台循环异常: {e}")
            await asyncio.sleep(60)


async def inbox_email_analysis_background_loop():
    """后台循环：兜底处理漏网的 pending/failed 邮件（主要由同步循环即时触发分析）"""
    logger.info("[InboxEmail] 后台兜底分析循环已启动，间隔 %s 秒", ANALYZE_INTERVAL_SECONDS)
    while True:
        try:
            await asyncio.sleep(ANALYZE_INTERVAL_SECONDS)
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(None, _analyze_pending_emails, ANALYZE_BATCH_SIZE)
            if summary.get("analyzed"):
                logger.info(
                    "[InboxEmail] 兜底分析：%s 封（任务 %s / 无任务 %s / 失败 %s）",
                    summary.get("analyzed"),
                    summary.get("has_task"),
                    summary.get("no_task"),
                    summary.get("failed"),
                )
        except Exception as e:
            logger.error(f"[InboxEmail] 兜底分析循环异常: {e}")
            await asyncio.sleep(60)
