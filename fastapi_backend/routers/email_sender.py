# -*- coding: utf-8 -*-
"""
邮件发送 API - 仅系统管理员 (webconfig.admin1) 可使用
基于网易企业邮箱 SMTP SSL 发送
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.header import Header
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from database import db
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["邮件发送"])

SMTP_SERVER = "smtp.qiye.163.com"
SMTP_PORT_SSL = 465


def _get_admin1() -> Optional[str]:
    try:
        rows = db.execute_query("SELECT admin1 FROM webconfig WHERE id = %s LIMIT 1", ("1",))
        if rows and rows[0].get("admin1") is not None:
            return (rows[0]["admin1"] or "").strip() or None
    except Exception:
        pass
    return None


def _get_email_config() -> dict:
    """从 webconfig 读取邮箱发送配置 (email_address, email_auth_code)"""
    try:
        rows = db.execute_query(
            "SELECT email_address, email_auth_code FROM webconfig WHERE id = %s LIMIT 1",
            ("1",),
        )
        if rows:
            return {
                "address": (rows[0].get("email_address") or "").strip(),
                "auth_code": (rows[0].get("email_auth_code") or "").strip(),
            }
    except Exception as e:
        logger.debug(f"读取邮箱配置失败（可能无 email_address/email_auth_code 列）: {e}")
    return {"address": "", "auth_code": ""}


def _require_admin(current_user: str):
    admin1 = _get_admin1()
    if not admin1 or (current_user or "").strip() != admin1:
        raise HTTPException(status_code=403, detail="仅系统管理员（webconfig.admin1）可操作")


class SendEmailRequest(BaseModel):
    current_user: str
    to: List[str]
    subject: str
    content: str
    content_type: str = "plain"


@router.get("/config")
async def get_email_config(current_user: str = Query(...)):
    """获取当前邮箱配置（脱敏）及员工通讯录"""
    _require_admin(current_user)
    cfg = _get_email_config()
    masked_addr = cfg["address"] if cfg["address"] else ""
    masked_code = ("*" * (len(cfg["auth_code"]) - 4) + cfg["auth_code"][-4:]) if len(cfg["auth_code"]) > 4 else "未配置"
    employees = []
    try:
        rows = db.execute_query(
            "SELECT name, lsys FROM yggl WHERE name IS NOT NULL AND TRIM(name) != '' ORDER BY lsys, name",
            (),
        )
        for r in rows:
            employees.append({
                "name": (r.get("name") or "").strip(),
                "dept": (r.get("lsys") or "").strip(),
            })
    except Exception as e:
        logger.warning(f"查询员工列表失败: {e}")

    return {
        "success": True,
        "emailAddress": masked_addr,
        "authCodeMasked": masked_code,
        "configured": bool(cfg["address"] and cfg["auth_code"]),
        "employees": employees,
    }


class UpdateEmailConfigRequest(BaseModel):
    current_user: str
    email_address: str
    email_auth_code: str


@router.post("/config")
async def update_email_config(req: UpdateEmailConfigRequest):
    """更新邮箱发送配置（写入 webconfig 表）"""
    _require_admin(req.current_user)
    try:
        db.execute_update(
            "ALTER TABLE webconfig ADD COLUMN email_address VARCHAR(200) DEFAULT '' ",
            (),
        )
    except Exception:
        pass
    try:
        db.execute_update(
            "ALTER TABLE webconfig ADD COLUMN email_auth_code VARCHAR(200) DEFAULT '' ",
            (),
        )
    except Exception:
        pass
    db.execute_update(
        "UPDATE webconfig SET email_address = %s, email_auth_code = %s WHERE id = %s",
        (req.email_address.strip(), req.email_auth_code.strip(), "1"),
    )
    return {"success": True, "message": "邮箱配置已更新"}


@router.post("/send")
async def send_email(req: SendEmailRequest):
    """发送邮件"""
    _require_admin(req.current_user)

    cfg = _get_email_config()
    sender = cfg["address"]
    password = cfg["auth_code"]
    if not sender or not password:
        raise HTTPException(status_code=400, detail="邮箱未配置，请先在「邮箱配置」中设置发件邮箱和授权码")

    recipients = [addr.strip() for addr in req.to if addr.strip()]
    if not recipients:
        raise HTTPException(status_code=400, detail="收件人不能为空")
    if not req.subject.strip():
        raise HTTPException(status_code=400, detail="邮件主题不能为空")

    message = MIMEText(req.content, req.content_type, "utf-8")
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = Header(req.subject, "utf-8")

    smtp_obj = None
    try:
        smtp_obj = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT_SSL, timeout=15)
        smtp_obj.login(sender, password)
        smtp_obj.sendmail(sender, recipients, message.as_string())
        logger.info(f"邮件发送成功: {sender} -> {recipients}, 主题: {req.subject}")
        return {"success": True, "message": f"邮件已发送给 {len(recipients)} 位收件人"}
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=401, detail="SMTP 登录失败，请检查邮箱地址和授权码是否正确")
    except smtplib.SMTPException as e:
        logger.error(f"邮件发送 SMTP 错误: {e}")
        raise HTTPException(status_code=500, detail=f"邮件发送失败: {str(e)}")
    except Exception as e:
        logger.error(f"邮件发送异常: {e}")
        raise HTTPException(status_code=500, detail=f"发送失败: {str(e)}")
    finally:
        if smtp_obj:
            try:
                smtp_obj.quit()
            except Exception:
                pass
