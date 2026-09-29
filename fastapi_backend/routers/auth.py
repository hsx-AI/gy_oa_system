# -*- coding: utf-8 -*-
"""
登录认证API路由
"""
import base64
import html
import json
import math
import logging
import hmac
import hashlib
import random
import re
import secrets
import smtplib
import threading
import time
from email.header import Header as MimeHeader
from email.mime.text import MIMEText
from fastapi import APIRouter, Query, Request, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import db, db_demo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])

PASSWORD_RULE_MESSAGE = (
    "密码至少6位，须包含数字、字母、特殊符号中的至少两类，"
    "且不能是常见弱口令或与用户名相同"
)
ACCESS_TOKEN_TTL_SECONDS = 12 * 3600
ACCESS_TOKEN_TYP = "oa_access"
# 常见弱口令（统一小写比对）；复杂度通过但仍属高风险口令一并拦截
_WEAK_PASSWORDS = {
    "123456", "1234567", "12345678", "123456789", "1234567890",
    "111111", "11111111", "000000", "00000000", "666666", "888888", "88888888",
    "123123", "112233", "121212", "123321", "654321",
    "password", "password1", "password123", "passw0rd", "p@ssw0rd", "p@ssword",
    "admin", "admin1", "admin12", "admin123", "admin888", "admin666", "root", "root123",
    "qwerty", "qwerty123", "qwer1234", "1qaz2wsx", "1q2w3e4r", "qazwsx",
    "abc123", "abcd1234", "a123456", "a1234567", "aa123456", "abc12345",
    "123456a", "123456aa", "1234abcd", "abcdef", "abcdefg",
    "iloveyou", "woaini", "woaini123", "5201314", "1314520",
    "letmein", "welcome", "welcome1", "monkey", "dragon", "master",
    "test", "test123", "guest", "user", "user123", "oa123456", "oaadmin",
    "changeme", "default", "system", "login", "pass123", "pass1234",
}
_FORCE_RESET_TTL_SECONDS = 600
_force_reset_tokens = {}  # name -> {"token": str, "expires": float}
CAPTCHA_FAIL_THRESHOLD = 3  # 连续失败达到该次数后需输入图片验证码
CAPTCHA_TTL_SECONDS = 300
LOGIN_FAIL_TTL_SECONDS = 1800
_CAPTCHA_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

_verification_codes = {}
_verification_lock = threading.Lock()
_login_failures = {}  # ip -> {"count": int, "expires": float}
_captchas = {}  # captcha_id -> {"code": str, "expires": float}
_captcha_lock = threading.Lock()


def _client_ip(http_request: Request) -> str:
    forwarded = (http_request.headers.get("x-forwarded-for") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if http_request.client and http_request.client.host:
        return http_request.client.host
    return "unknown"


def _prune_login_failures(now: float | None = None) -> None:
    now = time.time() if now is None else now
    expired = [k for k, v in _login_failures.items() if v.get("expires", 0) < now]
    for k in expired:
        _login_failures.pop(k, None)


def _get_fail_count(ip: str) -> int:
    now = time.time()
    with _captcha_lock:
        _prune_login_failures(now)
        item = _login_failures.get(ip)
        if not item or item.get("expires", 0) < now:
            _login_failures.pop(ip, None)
            return 0
        return int(item.get("count") or 0)


def _inc_fail_count(ip: str) -> int:
    now = time.time()
    with _captcha_lock:
        _prune_login_failures(now)
        item = _login_failures.get(ip)
        if not item or item.get("expires", 0) < now:
            count = 1
        else:
            count = int(item.get("count") or 0) + 1
        _login_failures[ip] = {
            "count": count,
            "expires": now + LOGIN_FAIL_TTL_SECONDS,
        }
        return count


def _clear_fail_count(ip: str) -> None:
    with _captcha_lock:
        _login_failures.pop(ip, None)


def _need_captcha(ip: str) -> bool:
    return _get_fail_count(ip) >= CAPTCHA_FAIL_THRESHOLD


def _make_captcha_image(code: str) -> str:
    """生成带干扰线的 SVG 图片验证码（data URL）。"""
    width, height = 130, 44
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#eef5ff"/>',
    ]
    for _ in range(5):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        color = f"rgb({random.randint(120, 190)},{random.randint(120, 190)},{random.randint(120, 190)})"
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.2"/>'
        )
    for _ in range(28):
        cx, cy = random.randint(0, width), random.randint(0, height)
        color = f"rgb({random.randint(150, 210)},{random.randint(150, 210)},{random.randint(150, 210)})"
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="1.2" fill="{color}"/>')
    for i, ch in enumerate(code):
        x = 14 + i * 28 + random.randint(-3, 3)
        y = 30 + random.randint(-5, 5)
        rot = random.randint(-28, 28)
        color = f"rgb({random.randint(20, 70)},{random.randint(40, 100)},{random.randint(120, 190)})"
        parts.append(
            f'<text x="{x}" y="{y}" fill="{color}" font-size="26" font-weight="700" '
            f'font-family="Arial,Helvetica,sans-serif" '
            f'transform="rotate({rot} {x} {y})">{html.escape(ch)}</text>'
        )
    parts.append("</svg>")
    svg = "".join(parts)
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _create_captcha() -> dict:
    code = "".join(secrets.choice(_CAPTCHA_CHARS) for _ in range(4))
    captcha_id = secrets.token_urlsafe(16)
    now = time.time()
    with _captcha_lock:
        expired = [k for k, v in _captchas.items() if v.get("expires", 0) < now]
        for k in expired:
            _captchas.pop(k, None)
        _captchas[captcha_id] = {"code": code.lower(), "expires": now + CAPTCHA_TTL_SECONDS}
    return {
        "captchaId": captcha_id,
        "image": _make_captcha_image(code),
    }


def _verify_and_consume_captcha(captcha_id: str, captcha_code: str) -> bool:
    cid = (captcha_id or "").strip()
    code = (captcha_code or "").strip().lower()
    if not cid or not code:
        return False
    now = time.time()
    with _captcha_lock:
        item = _captchas.pop(cid, None)
        if not item or item.get("expires", 0) < now:
            return False
        return secrets.compare_digest(item.get("code") or "", code)


def _ensure_session_ver_column():
    """登录会话版本号：改密后递增，用于作废其它浏览器中的本地登录态。"""
    try:
        db.execute_update(
            "ALTER TABLE yggl ADD COLUMN session_ver INT NOT NULL DEFAULT 1 "
            "COMMENT '登录会话版本，改密后递增'",
            (),
        )
    except Exception:
        pass


_ensure_session_ver_column()


def _read_session_ver(row_or_name) -> int:
    """从查询行或按姓名读取 session_ver；缺列/异常时回退为 1。"""
    if isinstance(row_or_name, dict):
        raw = row_or_name.get("session_ver")
        try:
            return max(1, int(raw or 1))
        except (TypeError, ValueError):
            return 1
    name = (row_or_name or "").strip()
    if not name:
        return 1
    try:
        rows = db.execute_query(
            "SELECT session_ver FROM yggl WHERE name=%s AND COALESCE(zaizhi,0)=0 LIMIT 1",
            (name,),
        )
        if not rows:
            return 1
        return _read_session_ver(rows[0])
    except Exception:
        return 1


def _auth_signing_secret() -> str:
    """访问令牌签名密钥：优先 AUTH_ACCESS_SECRET，其次 SSO / OnlyOffice 密钥。"""
    try:
        from config import settings
        for attr in ("AUTH_ACCESS_SECRET", "SSO_SECRET", "ONLYOFFICE_JWT_SECRET", "SHARED_FILES_SIGNING_SECRET"):
            val = (getattr(settings, attr, None) or "").strip()
            if val:
                return val
    except Exception:
        pass
    return "oa-auth-dev-fallback-change-me"


def _make_access_token(name: str, session_ver: int) -> str:
    secret = _auth_signing_secret()
    payload = {
        "name": (name or "").strip(),
        "sv": max(1, int(session_ver or 1)),
        "exp": int(time.time()) + ACCESS_TOKEN_TTL_SECONDS,
        "typ": ACCESS_TOKEN_TYP,
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def _parse_access_token(token: str) -> Optional[dict]:
    raw = (token or "").strip()
    if not raw or "." not in raw:
        return None
    payload_b64, sig = raw.rsplit(".", 1)
    if not payload_b64 or not sig:
        return None
    secret = _auth_signing_secret()
    expect = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(expect, sig):
        return None
    try:
        pad = "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode((payload_b64 + pad).encode("ascii")).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict) or payload.get("typ") != ACCESS_TOKEN_TYP:
        return None
    try:
        if int(payload.get("exp") or 0) < int(time.time()):
            return None
    except (TypeError, ValueError):
        return None
    name = (payload.get("name") or "").strip()
    if not name:
        return None
    try:
        sv = max(1, int(payload.get("sv") or 1))
    except (TypeError, ValueError):
        return None
    if _read_session_ver(name) != sv:
        return None
    return {"name": name, "sessionVer": sv}


def _extract_bearer_token(authorization: Optional[str], x_oa_token: Optional[str]) -> str:
    auth = (authorization or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return (x_oa_token or "").strip()


def _require_access_user(
    authorization: Optional[str] = None,
    x_oa_token: Optional[str] = None,
) -> str:
    token = _extract_bearer_token(authorization, x_oa_token)
    payload = _parse_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="未登录或登录已失效，请重新登录")
    return payload["name"]


def _attach_access_token(user_info: dict) -> dict:
    data = dict(user_info or {})
    name = (data.get("name") or "").strip()
    if name:
        data["accessToken"] = _make_access_token(name, data.get("sessionVer") or 1)
    return data


def _bump_session_ver(name: str) -> int:
    """密码变更后递增会话版本，返回新版本号。"""
    clean = (name or "").strip()
    if not clean:
        return 1
    _ensure_session_ver_column()
    try:
        db.execute_update(
            "UPDATE yggl SET session_ver = COALESCE(session_ver, 1) + 1 "
            "WHERE name=%s AND COALESCE(zaizhi,0)=0",
            (clean,),
        )
    except Exception as e:
        logger.warning("递增 session_ver 失败（将继续改密）: %s", e)
        return _read_session_ver(clean)
    return _read_session_ver(clean)


def _password_is_strong(password: str, username: str = "") -> bool:
    """复杂度 + 弱口令库校验；不通过则登录后强制改密。"""
    pwd = (password or "").strip()
    if len(pwd) < 6:
        return False
    lower = pwd.lower()
    name = (username or "").strip().lower()
    if name and lower == name:
        return False
    if lower in _WEAK_PASSWORDS:
        return False
    # 同一字符重复（如 aaaaaa / 111111）
    if len(set(pwd)) == 1:
        return False
    # 纯连续升/降序数字（长度>=6）
    if pwd.isdigit() and len(pwd) >= 6:
        asc = all(int(pwd[i]) - int(pwd[i - 1]) == 1 for i in range(1, len(pwd)))
        desc = all(int(pwd[i - 1]) - int(pwd[i]) == 1 for i in range(1, len(pwd)))
        if asc or desc:
            return False
    categories = sum((
        bool(re.search(r"[A-Za-z]", pwd)),
        bool(re.search(r"\d", pwd)),
        bool(re.search(r"[^A-Za-z0-9]", pwd)),
    ))
    return categories >= 2


def _issue_force_reset_token(name: str) -> str:
    clean = (name or "").strip()
    token = secrets.token_urlsafe(24)
    now = time.time()
    with _verification_lock:
        expired = [k for k, v in _force_reset_tokens.items() if v.get("expires", 0) < now]
        for k in expired:
            _force_reset_tokens.pop(k, None)
        _force_reset_tokens[clean] = {"token": token, "expires": now + _FORCE_RESET_TTL_SECONDS}
    return token


def _consume_force_reset_token(name: str, token: str) -> bool:
    clean = (name or "").strip()
    raw = (token or "").strip()
    if not clean or not raw:
        return False
    now = time.time()
    with _verification_lock:
        item = _force_reset_tokens.get(clean)
        if not item or item.get("expires", 0) < now:
            _force_reset_tokens.pop(clean, None)
            return False
        if not secrets.compare_digest(item.get("token") or "", raw):
            return False
        _force_reset_tokens.pop(clean, None)
        return True


def _masked_email(address: str) -> str:
    local, sep, domain = address.partition("@")
    if not sep:
        return "***"
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def _get_login_user(name: str):
    try:
        rows = db.execute_query(
            "SELECT name, `pass`, lsys, jb, gh, xbie, denglu_zt, gx_gt, enterprise_email, session_ver "
            "FROM yggl WHERE name=%s AND COALESCE(zaizhi,0)=0 LIMIT 1", (name,)
        )
    except Exception:
        rows = db.execute_query(
            "SELECT name, `pass`, lsys, jb, gh, xbie, denglu_zt, gx_gt, enterprise_email "
            "FROM yggl WHERE name=%s AND COALESCE(zaizhi,0)=0 LIMIT 1", (name,)
        )
    return rows[0] if rows else None


def _user_info(user_data: dict) -> dict:
    denglu_zt = user_data.get("denglu_zt")
    show_intro = denglu_zt is None or (isinstance(denglu_zt, str) and not denglu_zt.strip())
    info = {
        "name": (user_data.get("name") or "").strip(),
        "dept": (user_data.get("lsys") or "").strip(),
        "jb": (user_data.get("jb") or "").strip(),
        "gh": (user_data.get("gh") or "").strip(),
        "xbie": (user_data.get("xbie") or "").strip(),
        "showIntro": show_intro,
        "unreadNotifications": [],
        "mustChangePassword": not _password_is_strong(
            (user_data.get("pass") or "").strip(),
            (user_data.get("name") or "").strip(),
        ),
        "sessionVer": _read_session_ver(user_data),
    }
    return _attach_access_token(info)


def _format_entry_date(value) -> str:
    """参加工作时间展示：精确到月份（YYYY-MM）；仅有年份时显示 YYYY。"""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        raw = value.strftime("%Y-%m-%d")
    else:
        raw = str(value).strip()[:10]
    if not raw:
        return ""
    if len(raw) >= 7 and raw[4] == "-":
        return raw[:7]
    if len(raw) >= 4 and raw[:4].isdigit():
        return raw[:4]
    return raw


def _parse_entry_date_for_seniority(value):
    """解析参加工作时间用于工龄（精确到日；仅 YYYY-MM 时按当月 1 日）。"""
    from datetime import date as dt_date, datetime as dt_datetime

    if value is None:
        return None
    if isinstance(value, dt_date):
        return value
    if isinstance(value, dt_datetime):
        return value.date()
    if hasattr(value, "year") and hasattr(value, "month"):
        try:
            day = int(getattr(value, "day", 1) or 1)
            return dt_date(int(value.year), int(value.month), day)
        except (TypeError, ValueError):
            return None
    text = str(value).strip()[:10]
    if not text:
        return None
    try:
        if len(text) >= 10 and text[4] == "-":
            return dt_date.fromisoformat(text[:10])
        if len(text) >= 7 and text[4] == "-":
            y, m = int(text[:4]), int(text[5:7])
            return dt_date(y, m, 1)
        if len(text) >= 4 and text[:4].isdigit():
            return dt_date(int(text[:4]), 1, 1)
    except (TypeError, ValueError):
        return None
    return None


def _service_months(entry, today) -> int:
    """参加工作至今完整工龄月数（未满月不计入下一月）。"""
    months = (today.year - entry.year) * 12 + (today.month - entry.month)
    if today.day < entry.day:
        months -= 1
    return max(0, months)


def _paid_leave_entitlement_by_months(service_months: int) -> int:
    """工龄对应带薪年休假应得天数：<1年0；1~9年5；10~19年10；20年及以上15。"""
    if service_months < 12:
        return 0
    if service_months < 120:
        return 5
    if service_months < 240:
        return 10
    return 15


class LoginRequest(BaseModel):
    """登录请求模型"""
    admin: str  # 用户名（姓名）
    password: str = ""  # 明文密码（仅 ALLOW_PLAINTEXT_PASSWORD 时可用）
    passwordCipher: str = ""  # RSA-OAEP 加密后的密码（Base64）
    keyId: str = ""
    captchaId: str = ""
    captchaCode: str = ""


class LoginResponse(BaseModel):
    """登录响应模型"""
    success: bool
    message: str = ""
    data: dict = {}
    requireCaptcha: bool = False
    failCount: int = 0


class SetLoginStatusRequest(BaseModel):
    """设置登录状态（已读首次登录介绍）"""
    name: str  # 员工姓名


@router.get("/public-key")
def get_login_public_key():
    """下发登录/改密用 RSA 公钥，供前端加密密码后再传输。"""
    try:
        from utils.password_crypto import get_public_key_payload
        return get_public_key_payload()
    except Exception as e:
        logger.error("获取登录公钥失败: %s", e)
        return {"success": False, "message": "获取加密公钥失败"}


@router.get("/captcha")
def get_captcha():
    """获取登录图片验证码。"""
    try:
        data = _create_captcha()
        return {"success": True, **data}
    except Exception as e:
        logger.error("生成验证码失败: %s", e)
        return {"success": False, "message": "验证码生成失败，请稍后重试"}


@router.get("/captcha-required")
def captcha_required(http_request: Request):
    """查询当前客户端是否因连续登录失败而需要图片验证码。"""
    ip = _client_ip(http_request)
    count = _get_fail_count(ip)
    return {
        "success": True,
        "requireCaptcha": count >= CAPTCHA_FAIL_THRESHOLD,
        "failCount": count,
    }


@router.get("/password-status")
async def password_status(name: str = Query(..., description="员工姓名")):
    """供已登录浏览器复核密码强度与会话版本；会话版本不一致时前端应强制重新登录。"""
    clean_name = (name or "").strip()
    if not clean_name:
        return {"success": False, "message": "用户名为空"}
    try:
        try:
            rows = db.execute_query(
                "SELECT `pass`, session_ver FROM yggl WHERE name=%s AND COALESCE(zaizhi,0)=0 LIMIT 1",
                (clean_name,),
            )
        except Exception:
            rows = db.execute_query(
                "SELECT `pass` FROM yggl WHERE name=%s AND COALESCE(zaizhi,0)=0 LIMIT 1",
                (clean_name,),
            )
        if not rows:
            return {"success": False, "message": "用户不存在或已离职"}
        return {
            "success": True,
            "mustChangePassword": not _password_is_strong((rows[0].get("pass") or "").strip(), clean_name),
            "sessionVer": _read_session_ver(rows[0]),
        }
    except Exception as e:
        logger.error("检查密码安全状态失败: %s", e)
        return {"success": False, "message": "无法检查登录安全状态"}


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, http_request: Request):
    """
    用户登录接口
    
    验证用户名和密码，返回用户信息。
    同一客户端连续失败达到阈值后，必须先通过图片验证码。
    """
    ip = _client_ip(http_request)
    fail_count = _get_fail_count(ip)
    require_captcha = fail_count >= CAPTCHA_FAIL_THRESHOLD

    def _fail(message: str, *, bump: bool = True) -> LoginResponse:
        count = _inc_fail_count(ip) if bump else _get_fail_count(ip)
        return LoginResponse(
            success=False,
            message=message,
            requireCaptcha=count >= CAPTCHA_FAIL_THRESHOLD,
            failCount=count,
        )

    try:
        from utils.password_crypto import resolve_password
        try:
            password = resolve_password(
                plaintext=request.password,
                cipher=request.passwordCipher,
                key_id=request.keyId,
                field_label="登录密码",
            )
        except HTTPException as he:
            return _fail(he.detail if isinstance(he.detail, str) else "密码传输不安全，请刷新后重试", bump=False)

        # 验证参数
        if not request.admin or not password:
            return _fail("请输入用户名和密码", bump=False)

        if require_captcha and not _verify_and_consume_captcha(request.captchaId, request.captchaCode):
            return _fail("验证码错误或已过期，请重新输入", bump=False)
        
        # 先查是否存在该用户（在职），再校验密码，便于区分「无此用户」与「密码错误」
        check_user_sql = (
            "SELECT name, `pass`, lsys, jb, gh, xbie, denglu_zt, gx_gt, session_ver "
            "FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1"
        )
        try:
            user_rows = db.execute_query(check_user_sql, (request.admin,))
        except Exception:
            try:
                check_user_sql = (
                    "SELECT name, `pass`, lsys, jb, gh, xbie, denglu_zt, gx_gt "
                    "FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1"
                )
                user_rows = db.execute_query(check_user_sql, (request.admin,))
            except Exception:
                check_user_sql = (
                    "SELECT name, `pass`, lsys, jb, gh, xbie FROM yggl "
                    "WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1"
                )
                user_rows = db.execute_query(check_user_sql, (request.admin,))
        if not user_rows or len(user_rows) == 0:
            return _fail("没有该用户，请检查用户名或联系管理员")
        user_data = user_rows[0]
        db_pass = (user_data.get("pass") or "").strip()
        if db_pass != password:
            return _fail("密码错误，请重新输入")
        # 密码正确，构建返回数据；denglu_zt 为空表示未看过首次登录介绍
        denglu_zt = user_data.get("denglu_zt")
        show_intro = denglu_zt is None or (isinstance(denglu_zt, str) and denglu_zt.strip() == "")

        # 查询未读通知：gx_gt 存最后已读通知 ID，NULL/空/'0' 视为 0
        gx_gt_raw = user_data.get("gx_gt")
        try:
            last_read_id = int(gx_gt_raw) if gx_gt_raw and str(gx_gt_raw).strip() not in ("", "0") else 0
        except (ValueError, TypeError):
            last_read_id = 0

        unread_notifications = []
        try:
            unread_rows = db.execute_query(
                "SELECT id, content, publish_time FROM notifications WHERE id > %s ORDER BY id ASC",
                (last_read_id,),
            )
            for nr in (unread_rows or []):
                unread_notifications.append({
                    "id": nr["id"],
                    "content": (nr.get("content") or "").strip(),
                    "time": str(nr.get("publish_time") or ""),
                })
        except Exception:
            pass

        user_info = {
            "name": (user_data.get("name") or "").strip(),
            "dept": (user_data.get("lsys") or "").strip(),
            "jb": (user_data.get("jb") or "").strip(),
            "gh": (user_data.get("gh") or "").strip(),
            "xbie": (user_data.get("xbie") or "").strip(),
            "showIntro": show_intro,
            "unreadNotifications": unread_notifications,
            "mustChangePassword": not _password_is_strong(db_pass, (user_data.get("name") or "").strip()),
            "sessionVer": _read_session_ver(user_data),
        }
        _clear_fail_count(ip)
        return LoginResponse(
            success=True,
            message="登录成功",
            data=_attach_access_token(user_info),
        )
            
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        return LoginResponse(
            success=False,
            message=f"登录失败: {str(e)}",
            requireCaptcha=_need_captcha(ip),
            failCount=_get_fail_count(ip),
        )


@router.post("/set-login-status")
def set_login_status(req: SetLoginStatusRequest):
    """标记用户已看过首次登录介绍，更新 yggl.denglu_zt"""
    name = (req.name or "").strip()
    if not name:
        return {"success": False, "message": "姓名为空"}
    try:
        sql = "UPDATE yggl SET denglu_zt=%s WHERE name=%s AND (COALESCE(zaizhi,0)=0)"
        db.execute_update(sql, ("1", name))
        return {"success": True, "message": "已更新"}
    except Exception as e:
        if "denglu_zt" in str(e).lower() or "unknown column" in str(e).lower():
            return {"success": True, "message": "已更新"}
        logger.error(f"设置登录状态失败: {str(e)}")
        return {"success": False, "message": str(e)}


# ==================== 更新消息推送（多条历史通知） ====================

class PublishNotificationRequest(BaseModel):
    current_user: str
    content: str


class DismissNotificationRequest(BaseModel):
    name: str
    max_id: int


@router.post("/notification/publish")
def publish_notification(req: PublishNotificationRequest):
    """管理员(admin1)发布更新通知：向 notifications 表插入一条新记录"""
    from routers.db_manager import _get_admin1
    from datetime import datetime
    name = (req.current_user or "").strip()
    admin1 = _get_admin1()
    if not admin1 or name != admin1:
        return {"success": False, "message": "仅系统管理员可发布通知"}
    content = (req.content or "").strip()
    if not content:
        return {"success": False, "message": "通知内容不能为空"}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        db.execute_update(
            "INSERT INTO notifications (content, publish_time, publisher) VALUES (%s, %s, %s)",
            (content, now, name),
        )
        return {"success": True, "message": "通知已发布，未读此通知的员工下次登录将看到弹窗"}
    except Exception as e:
        logger.error(f"发布通知失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/notification/dismiss")
def dismiss_notification(req: DismissNotificationRequest):
    """用户关闭通知弹窗后，将 gx_gt 更新为已读的最大通知 ID"""
    name = (req.name or "").strip()
    if not name:
        return {"success": False, "message": "姓名为空"}
    try:
        db.execute_update(
            "UPDATE yggl SET gx_gt = %s WHERE name = %s AND COALESCE(zaizhi,0) = 0",
            (str(req.max_id), name),
        )
        return {"success": True}
    except Exception as e:
        logger.error(f"标记通知已读失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/notification/list")
def list_notifications():
    """获取所有历史通知（供管理页面展示），按时间倒序"""
    try:
        rows = db.execute_query(
            "SELECT id, content, publish_time, publisher FROM notifications ORDER BY id DESC"
        )
        items = []
        for r in (rows or []):
            items.append({
                "id": r["id"],
                "content": (r.get("content") or "").strip(),
                "time": str(r.get("publish_time") or ""),
                "publisher": (r.get("publisher") or "").strip(),
            })
        return {"success": True, "items": items}
    except Exception as e:
        return {"success": True, "items": []}


@router.post("/notification/delete")
def delete_notification(req: dict):
    """管理员删除一条通知"""
    from routers.db_manager import _get_admin1
    name = (req.get("current_user") or "").strip()
    admin1 = _get_admin1()
    if not admin1 or name != admin1:
        return {"success": False, "message": "仅系统管理员可操作"}
    nid = req.get("id")
    if not nid:
        return {"success": False, "message": "缺少通知ID"}
    try:
        db.execute_update("DELETE FROM notifications WHERE id = %s", (nid,))
        return {"success": True, "message": "已删除"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/profile")
def get_profile(
    name: str = Query(..., description="员工姓名"),
    authorization: Optional[str] = Header(None),
    x_oa_token: Optional[str] = Header(None, alias="X-OA-Token"),
):
    """获取本人员工信息。必须携带登录访问令牌，且仅允许查询当前登录用户自己的资料。"""
    actor = _require_access_user(authorization, x_oa_token)
    target = (name or "").strip()
    if not target:
        raise HTTPException(status_code=400, detail="用户名为空")
    if actor != target:
        # 禁止通过改 name 参数读取他人身份证号/手机号等敏感资料
        raise HTTPException(status_code=403, detail="无权查看他人资料")
    try:
        from utils.hxp_helper import compute_expire_date, parse_expire_for_sort
        sql = (
            "SELECT name, gh, lsys, jb, sfzh, rcnf FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1"
        )
        try:
            rows = db.execute_query(sql, (target,))
        except Exception:
            # 兼容无 sfzh/rcnf 列：仅查基础字段
            rows = db.execute_query(
                "SELECT name, gh, lsys, jb FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1",
                (target,),
            )
        if not rows:
            return {"success": False, "message": "用户不存在或已离职"}
        r = rows[0]
        # 换休票：从 hxp 表按 sl 加和，排除已过期
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        hxp_rows = db.execute_query(
            "SELECT id, sl, sj FROM hxp WHERE name = %s AND sl > 0", (target,)
        )
        total = 0.0
        expire_groups = {}
        for row in hxp_rows:
            try:
                sl = float(row.get("sl") or 0)
            except (TypeError, ValueError):
                sl = 0.0
            if sl <= 0:
                continue
            exp = compute_expire_date(row.get("sj"))
            if exp and exp < today:
                continue  # 已过期，不计入
            total += sl
            if exp:
                expire_groups[exp] = expire_groups.get(exp, 0.0) + sl
        details = [
            {"expireDate": k, "count": round(v, 3)}
            for k, v in sorted(expire_groups.items(), key=lambda x: parse_expire_for_sort(x[0]))
        ]
        # 换休票预扣减：正在审核中的换休/员工换休票请假所消耗的张数，从「可用」中扣除，避免多单同时审核导致扣成负数
        hxp_pending = 0.0
        try:
            pending_rows = db.execute_query(
                "SELECT COALESCE(SUM(CAST(COALESCE(hxpxh, tian * 2) AS DECIMAL(10,4))), 0) AS s FROM qj WHERE xm = %s AND qjzt IN (0, 1, 3) AND (TRIM(COALESCE(qjfs,'')) = %s OR TRIM(COALESCE(qjfs,'')) = %s)",
                (target, "换休", "员工换休票"),
            )
            if pending_rows and pending_rows[0].get("s") is not None:
                hxp_pending = float(pending_rows[0]["s"])
        except Exception as e:
            logger.debug(f"换休票预扣减查询失败: {e}")
        hxp_available = max(0.0, total - hxp_pending)
        entry_date = _format_entry_date(r.get("rcnf"))
        entry_raw_for_seniority = r.get("rcnf")
        mobile = ""
        sfzh_clean = (r.get("sfzh") or "").strip().replace(" ", "")
        if sfzh_clean:
            try:
                demo_rows = db_demo.execute_query(
                    "SELECT mobile, work_start_date FROM employee_info WHERE id_card = %s LIMIT 1",
                    (sfzh_clean,),
                )
                if demo_rows:
                    mobile = str(demo_rows[0].get("mobile") or "").strip()
                    wsd = demo_rows[0].get("work_start_date")
                    if wsd is not None:
                        entry_raw_for_seniority = wsd
                        demo_entry = _format_entry_date(wsd)
                        if demo_entry:
                            entry_date = demo_entry
            except Exception as e:
                logger.debug("demo 库 employee_info 查询失败: %s", e)
        # 带薪休假：按参加工作时间精确计算工龄（月），再对应应得天数
        paid_leave_remaining = None
        paid_leave_detail = None
        try:
            from datetime import date

            entry_dt = _parse_entry_date_for_seniority(entry_raw_for_seniority)
            if entry_dt is not None:
                today = date.today()
                service_months = _service_months(entry_dt, today)
                entitlement = _paid_leave_entitlement_by_months(service_months)
                deducted = 3  # 固定高温假公休
                available = max(0, entitlement - deducted)
                current_year = today.year
                qj_rows = db.execute_query(
                    "SELECT COALESCE(SUM(CAST(tian AS DECIMAL(10,4))), 0) AS total FROM qj WHERE xm = %s AND qjzt = 4 AND YEAR(timefrom) = %s AND (TRIM(COALESCE(qjfs,'')) LIKE %s OR TRIM(COALESCE(qjfs,'')) LIKE %s OR TRIM(COALESCE(qjfs,'')) = %s OR TRIM(COALESCE(qjfs,'')) = %s)",
                    (target, current_year, "%带薪%", "%年休假%", "带薪休假", "年休假"),
                )
                used_raw = float(qj_rows[0]["total"]) if qj_rows and qj_rows[0].get("total") is not None else 0.0
                used_rounded = math.ceil(used_raw / 0.25) * 0.25
                remaining = round(max(0, available - used_rounded) * 4) / 4
                paid_leave_remaining = remaining
                paid_leave_detail = {
                    "entitlement": entitlement,
                    "deducted": deducted,
                    "used": round(used_rounded, 2),
                    "remaining": round(remaining, 2),
                    "serviceMonths": service_months,
                    "serviceYears": round(service_months / 12, 1),
                }
        except Exception as e:
            logger.debug(f"带薪休假计算失败: {e}")
        # 仅本人令牌可通过；身份证/手机仍按本人完整返回，供个人中心与请假联系方式使用
        return {
            "success": True,
            "data": {
                "name": (r.get("name") or "").strip(),
                "workNo": (r.get("gh") or "").strip(),
                "department": (r.get("lsys") or "").strip(),
                "level": (r.get("jb") or "").strip(),
                "idNumber": (r.get("sfzh") or "").strip(),
                "mobile": mobile,
                "entryDate": entry_date,
                "exchangeTickets": round(hxp_available, 3),
                "exchangeTicketsTotal": round(total, 3),
                "exchangeTicketsPending": round(hxp_pending, 3),
                "exchangeTicketDetails": details,
                "paidLeaveRemaining": paid_leave_remaining,
                "paidLeaveDetail": paid_leave_detail,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取员工信息失败: {str(e)}")
        return {"success": False, "message": str(e)}


class ChangePasswordRequest(BaseModel):
    name: str
    oldPassword: str = ""
    newPassword: str = ""
    forceResetToken: str = ""
    oldPasswordCipher: str = ""
    newPasswordCipher: str = ""
    keyId: str = ""


@router.post("/change-password")
def change_password(req: ChangePasswordRequest):
    """修改密码；成功后递增 session_ver，使其它已登录浏览器的本地态失效。
    强制改密场景可凭 forceResetToken（邮箱验证码登录后下发）免原密码。
    密码字段支持 RSA 密文传输。
    """
    try:
        from utils.password_crypto import resolve_password
        name = (req.name or "").strip()
        try:
            old_password = resolve_password(
                plaintext=req.oldPassword,
                cipher=req.oldPasswordCipher,
                key_id=req.keyId,
                field_label="原密码",
            ) if ((req.oldPassword or "").strip() or (req.oldPasswordCipher or "").strip()) else ""
            new_password = resolve_password(
                plaintext=req.newPassword,
                cipher=req.newPasswordCipher,
                key_id=req.keyId,
                field_label="新密码",
            )
        except HTTPException as he:
            return {"success": False, "message": he.detail if isinstance(he.detail, str) else "密码传输不安全"}

        if not _password_is_strong(new_password, name):
            return {"success": False, "message": PASSWORD_RULE_MESSAGE}
        if old_password and secrets.compare_digest(old_password, new_password):
            return {"success": False, "message": "新密码不能与原密码相同"}

        token = (req.forceResetToken or "").strip()
        if token:
            if not _consume_force_reset_token(name, token):
                return {"success": False, "message": "强制改密凭证无效或已过期，请重新登录后再改"}
        else:
            check = db.execute_query(
                "SELECT 1 FROM yggl WHERE name=%s AND `pass`=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1",
                (name, old_password),
            )
            if not check:
                return {"success": False, "message": "原密码错误"}
        db.execute_update(
            "UPDATE yggl SET `pass`=%s WHERE name=%s",
            (new_password, name),
        )
        session_ver = _bump_session_ver(name)
        return {
            "success": True,
            "message": "密码修改成功，其它已登录设备需重新登录",
            "sessionVer": session_ver,
            "accessToken": _make_access_token(name, session_ver),
        }
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        return {"success": False, "message": str(e)}


class VerificationCodeRequest(BaseModel):
    name: str
    purpose: str  # login / reset


class CodeLoginRequest(BaseModel):
    name: str
    code: str


class ResetPasswordByCodeRequest(BaseModel):
    name: str
    code: str
    newPassword: str = ""
    newPasswordCipher: str = ""
    keyId: str = ""


def _consume_code(name: str, purpose: str, code: str) -> bool:
    key = (name, purpose)
    now = time.time()
    with _verification_lock:
        item = _verification_codes.get(key)
        if not item or item["expires"] < now or item["attempts"] >= 5:
            _verification_codes.pop(key, None)
            return False
        item["attempts"] += 1
        if not secrets.compare_digest(item["code"], (code or "").strip()):
            return False
        _verification_codes.pop(key, None)
        return True


@router.post("/send-verification-code")
def send_verification_code(req: VerificationCodeRequest):
    name = (req.name or "").strip()
    purpose = (req.purpose or "").strip().lower()
    if purpose not in ("login", "reset"):
        return {"success": False, "message": "验证码用途无效"}
    try:
        user = _get_login_user(name)
        if not user:
            return {"success": False, "message": "没有该用户"}
        recipient = (user.get("enterprise_email") or "").strip()
        if not recipient:
            return {"success": False, "message": "该用户尚未配置企业邮箱，请联系管理员"}
        from routers.email_sender import _get_email_config, SMTP_SERVER, SMTP_PORT_SSL
        cfg = _get_email_config()
        if not cfg["address"] or not cfg["auth_code"]:
            return {"success": False, "message": "系统发信邮箱尚未配置，请联系管理员"}
        key = (name, purpose)
        now = time.time()
        with _verification_lock:
            previous = _verification_codes.get(key)
            if previous and now - previous["sent_at"] < 60:
                return {"success": False, "message": "验证码发送过于频繁，请60秒后再试"}
        code = f"{secrets.randbelow(1000000):06d}"
        action = "登录" if purpose == "login" else "修改密码"
        message = MIMEText(f"您好，{name}：\n\n您正在通过邮箱验证码{action}，验证码为：{code}\n\n验证码5分钟内有效，请勿转发给他人。", "plain", "utf-8")
        message["From"] = cfg["address"]
        message["To"] = recipient
        message["Subject"] = MimeHeader(f"集成办公平台{action}验证码", "utf-8")
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT_SSL, timeout=15) as smtp:
            smtp.login(cfg["address"], cfg["auth_code"])
            smtp.sendmail(cfg["address"], [recipient], message.as_string())
        with _verification_lock:
            _verification_codes[key] = {"code": code, "expires": now + 300, "sent_at": now, "attempts": 0}
        return {"success": True, "message": f"验证码已发送至 {_masked_email(recipient)}"}
    except Exception as e:
        logger.error("发送登录验证码失败: %s", e)
        return {"success": False, "message": "验证码发送失败，请稍后重试或联系管理员"}


@router.post("/login-by-code", response_model=LoginResponse)
def login_by_code(req: CodeLoginRequest):
    name = (req.name or "").strip()
    if not _consume_code(name, "login", req.code):
        return LoginResponse(success=False, message="验证码错误、已过期或尝试次数过多")
    try:
        user = _get_login_user(name)
        if not user:
            return LoginResponse(success=False, message="用户不存在或已离职")
        data = _user_info(user)
        if data.get("mustChangePassword"):
            # 邮箱登录已通过身份校验，下发短期凭证供强制改密（无需原密码）
            data["forceResetToken"] = _issue_force_reset_token(name)
        return LoginResponse(success=True, message="登录成功", data=data)
    except Exception as e:
        logger.error("验证码登录失败: %s", e)
        return LoginResponse(success=False, message="登录失败，请稍后重试")


@router.post("/reset-password-by-code")
def reset_password_by_code(req: ResetPasswordByCodeRequest):
    name = (req.name or "").strip()
    try:
        from utils.password_crypto import resolve_password
        new_password = resolve_password(
            plaintext=req.newPassword,
            cipher=req.newPasswordCipher,
            key_id=req.keyId,
            field_label="新密码",
        )
    except HTTPException as he:
        return {"success": False, "message": he.detail if isinstance(he.detail, str) else "密码传输不安全"}
    if not _password_is_strong(new_password, name):
        return {"success": False, "message": PASSWORD_RULE_MESSAGE}
    if not _consume_code(name, "reset", req.code):
        return {"success": False, "message": "验证码错误、已过期或尝试次数过多"}
    try:
        updated = db.execute_update(
            "UPDATE yggl SET `pass`=%s WHERE name=%s AND COALESCE(zaizhi,0)=0",
            (new_password, name),
        )
        if not updated:
            return {"success": False, "message": "用户不存在或已离职"}
        session_ver = _bump_session_ver(name)
        return {
            "success": True,
            "message": "密码修改成功，请使用新密码登录",
            "sessionVer": session_ver,
            "accessToken": _make_access_token(name, session_ver),
        }
    except Exception as e:
        logger.error("验证码修改密码失败: %s", e)
        return {"success": False, "message": "密码修改失败，请稍后重试"}


# ==================== 用户配色风格 ====================

def _ensure_skin_style_column():
    """确保 yggl 表有 skin_style 列。"""
    try:
        db.execute_update("ALTER TABLE yggl ADD COLUMN skin_style VARCHAR(20) DEFAULT '' COMMENT '用户配色风格'", ())
    except Exception:
        pass


_ensure_skin_style_column()


@router.get("/user-style")
def get_user_style(name: str = Query(..., description="用户姓名")):
    """获取用户保存的配色风格。"""
    try:
        rows = db.execute_query(
            "SELECT skin_style FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1",
            (name,),
        )
        style = (rows[0].get("skin_style") or "").strip() if rows else ""
        return {"success": True, "skinStyle": style}
    except Exception as e:
        logger.error(f"获取用户风格失败: {e}")
        return {"success": False, "message": str(e)}


class UserStyleRequest(BaseModel):
    name: str
    skinStyle: str


@router.post("/user-style")
def save_user_style(req: UserStyleRequest):
    """保存用户配色风格到 yggl.skin_style。"""
    try:
        style = (req.skinStyle or "").strip()
        allowed = {"", "default", "dark", "green", "purple", "blue", "warm"}
        if style not in allowed:
            style = ""
        db.execute_update(
            "UPDATE yggl SET skin_style=%s WHERE name=%s AND (COALESCE(zaizhi,0)=0)",
            (style, req.name),
        )
        return {"success": True, "message": "已保存"}
    except Exception as e:
        logger.error(f"保存用户风格失败: {e}")
        return {"success": False, "message": str(e)}
