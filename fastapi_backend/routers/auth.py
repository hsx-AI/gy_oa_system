# -*- coding: utf-8 -*-
"""
登录认证API路由
"""
import math
import logging
import re
import secrets
import smtplib
import threading
import time
from email.header import Header
from email.mime.text import MIMEText
from fastapi import APIRouter, Query
from pydantic import BaseModel
from database import db, db_demo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])

PASSWORD_RULE_MESSAGE = "密码至少6位，且须包含数字、字母、特殊符号中的至少两类"
_verification_codes = {}
_verification_lock = threading.Lock()


def _password_is_strong(password: str) -> bool:
    if len(password or "") < 6:
        return False
    categories = sum((
        bool(re.search(r"[A-Za-z]", password)),
        bool(re.search(r"\d", password)),
        bool(re.search(r"[^A-Za-z0-9]", password)),
    ))
    return categories >= 2


def _masked_email(address: str) -> str:
    local, sep, domain = address.partition("@")
    if not sep:
        return "***"
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def _get_login_user(name: str):
    rows = db.execute_query(
        "SELECT name, `pass`, lsys, jb, gh, xbie, denglu_zt, gx_gt, enterprise_email "
        "FROM yggl WHERE name=%s AND COALESCE(zaizhi,0)=0 LIMIT 1", (name,)
    )
    return rows[0] if rows else None


def _user_info(user_data: dict) -> dict:
    denglu_zt = user_data.get("denglu_zt")
    show_intro = denglu_zt is None or (isinstance(denglu_zt, str) and not denglu_zt.strip())
    return {
        "name": (user_data.get("name") or "").strip(),
        "dept": (user_data.get("lsys") or "").strip(),
        "jb": (user_data.get("jb") or "").strip(),
        "gh": (user_data.get("gh") or "").strip(),
        "xbie": (user_data.get("xbie") or "").strip(),
        "showIntro": show_intro,
        "unreadNotifications": [],
        "mustChangePassword": not _password_is_strong((user_data.get("pass") or "").strip()),
    }


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
    password: str  # 密码


class LoginResponse(BaseModel):
    """登录响应模型"""
    success: bool
    message: str = ""
    data: dict = {}


class SetLoginStatusRequest(BaseModel):
    """设置登录状态（已读首次登录介绍）"""
    name: str  # 员工姓名


@router.get("/password-status")
async def password_status(name: str = Query(..., description="员工姓名")):
    """供已登录浏览器启动时复核密码安全状态，拦截升级前遗留的本地登录状态。"""
    clean_name = (name or "").strip()
    if not clean_name:
        return {"success": False, "message": "用户名为空"}
    try:
        rows = db.execute_query(
            "SELECT `pass` FROM yggl WHERE name=%s AND COALESCE(zaizhi,0)=0 LIMIT 1",
            (clean_name,),
        )
        if not rows:
            return {"success": False, "message": "用户不存在或已离职"}
        return {
            "success": True,
            "mustChangePassword": not _password_is_strong((rows[0].get("pass") or "").strip()),
        }
    except Exception as e:
        logger.error("检查密码安全状态失败: %s", e)
        return {"success": False, "message": "无法检查登录安全状态"}


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """
    用户登录接口
    
    验证用户名和密码，返回用户信息
    """
    
    try:
        # 验证参数
        if not request.admin or not request.password:
            return LoginResponse(
                success=False,
                message="请输入用户名和密码"
            )
        
        # 先查是否存在该用户（在职），再校验密码，便于区分「无此用户」与「密码错误」
        check_user_sql = "SELECT name, `pass`, lsys, jb, gh, xbie, denglu_zt, gx_gt FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1"
        try:
            user_rows = db.execute_query(check_user_sql, (request.admin,))
        except Exception:
            check_user_sql = "SELECT name, `pass`, lsys, jb, gh, xbie FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1"
            user_rows = db.execute_query(check_user_sql, (request.admin,))
        if not user_rows or len(user_rows) == 0:
            return LoginResponse(
                success=False,
                message="没有该用户，请检查用户名或联系管理员"
            )
        user_data = user_rows[0]
        db_pass = (user_data.get("pass") or "").strip()
        if db_pass != request.password:
            return LoginResponse(
                success=False,
                message="密码错误，请重新输入"
            )
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
            "mustChangePassword": not _password_is_strong(db_pass),
        }
        return LoginResponse(
            success=True,
            message="登录成功",
            data=user_info
        )
            
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        return LoginResponse(
            success=False,
            message=f"登录失败: {str(e)}"
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
def get_profile(name: str = Query(..., description="员工姓名")):
    """获取员工信息：用户名、工号、科室、级别、身份证号、参加工作时间、换休票总数及明细（按过期日分组）"""
    try:
        from utils.hxp_helper import compute_expire_date, parse_expire_for_sort
        sql = (
            "SELECT name, gh, lsys, jb, sfzh, rcnf FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1"
        )
        try:
            rows = db.execute_query(sql, (name,))
        except Exception:
            # 兼容无 sfzh/rcnf 列：仅查基础字段
            rows = db.execute_query(
                "SELECT name, gh, lsys, jb FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1",
                (name,),
            )
        if not rows:
            return {"success": False, "message": "用户不存在或已离职"}
        r = rows[0]
        # 换休票：从 hxp 表按 sl 加和，排除已过期
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        hxp_rows = db.execute_query(
            "SELECT id, sl, sj FROM hxp WHERE name = %s AND sl > 0", (name,)
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
                (name, "换休", "员工换休票"),
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
                    (name, current_year, "%带薪%", "%年休假%", "带薪休假", "年休假"),
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
    except Exception as e:
        logger.error(f"获取员工信息失败: {str(e)}")
        return {"success": False, "message": str(e)}


class ChangePasswordRequest(BaseModel):
    name: str
    oldPassword: str
    newPassword: str


@router.post("/change-password")
def change_password(req: ChangePasswordRequest):
    """修改密码"""
    try:
        if not _password_is_strong(req.newPassword):
            return {"success": False, "message": PASSWORD_RULE_MESSAGE}
        check = db.execute_query(
            "SELECT 1 FROM yggl WHERE name=%s AND `pass`=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1",
            (req.name, req.oldPassword)
        )
        if not check:
            return {"success": False, "message": "原密码错误"}
        db.execute_update(
            "UPDATE yggl SET `pass`=%s WHERE name=%s",
            (req.newPassword, req.name)
        )
        return {"success": True, "message": "密码修改成功"}
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
    newPassword: str


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
        message["Subject"] = Header(f"集成办公平台{action}验证码", "utf-8")
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
        # 邮箱验证码已完成身份校验，不因历史弱密码阻断该登录方式。
        data["mustChangePassword"] = False
        return LoginResponse(success=True, message="登录成功", data=data)
    except Exception as e:
        logger.error("验证码登录失败: %s", e)
        return LoginResponse(success=False, message="登录失败，请稍后重试")


@router.post("/reset-password-by-code")
def reset_password_by_code(req: ResetPasswordByCodeRequest):
    name = (req.name or "").strip()
    if not _password_is_strong(req.newPassword):
        return {"success": False, "message": PASSWORD_RULE_MESSAGE}
    if not _consume_code(name, "reset", req.code):
        return {"success": False, "message": "验证码错误、已过期或尝试次数过多"}
    try:
        updated = db.execute_update(
            "UPDATE yggl SET `pass`=%s WHERE name=%s AND COALESCE(zaizhi,0)=0",
            (req.newPassword, name),
        )
        if not updated:
            return {"success": False, "message": "用户不存在或已离职"}
        return {"success": True, "message": "密码修改成功，请使用新密码登录"}
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
