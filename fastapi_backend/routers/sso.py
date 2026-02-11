# -*- coding: utf-8 -*-
"""
单点登录：生成免登链接，跳转人事档案等外部系统（B 系统）。
双方约定以员工身份证号为唯一标识，A 系统生成带签名的 ticket，B 系统校验后为对应用户建立登录态。
"""
import json
import base64
import hmac
import hashlib
import time
import logging
from fastapi import APIRouter, Query, HTTPException
from config import settings
from database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sso", tags=["单点登录"])


def _make_ticket(sfzh: str, name: str, expire_seconds: int) -> str:
    """生成 HMAC 签名的 ticket：payload 为 base64(json({sub, name, exp}))，签名用 SSO_SECRET。"""
    secret = (settings.SSO_SECRET or "").strip()
    if not secret:
        raise ValueError("SSO_SECRET 未配置")
    exp = int(time.time()) + expire_seconds
    payload_obj = {"sub": sfzh, "name": name, "exp": exp}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload_obj, ensure_ascii=False).encode()).decode().rstrip("=")
    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


@router.get("/link")
async def get_sso_link(
    target: str = Query(..., description="目标系统标识，如 B 表示人事档案系统"),
    name: str = Query(..., description="当前登录用户姓名，用于校验并生成 ticket"),
):
    """
    生成免登链接：校验当前用户已登录（在 yggl 中存在且有身份证号），生成 ticket 并返回 B 系统入口 URL。
    前端拿到 url 后执行 window.location.href = url 即可跳转并带 ticket 单点登录。
    """
    if not (settings.SSO_TARGET_B_BASE_URL or "").strip():
        raise HTTPException(status_code=503, detail="未配置目标系统地址 SSO_TARGET_B_BASE_URL")
    if not (settings.SSO_SECRET or "").strip():
        raise HTTPException(status_code=503, detail="未配置 SSO 签名密钥 SSO_SECRET")

    target = (target or "").strip().upper()
    if target != "B":
        raise HTTPException(status_code=400, detail="暂仅支持 target=B（人事档案系统）")

    name = (name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="请传入当前用户姓名")

    try:
        # 查 yggl：在职且含身份证号
        try:
            rows = db.execute_query(
                "SELECT name, sfzh FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1",
                (name,),
            )
        except Exception:
            rows = db.execute_query(
                "SELECT name FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1",
                (name,),
            )
            if rows:
                rows = [dict(r) for r in rows]
                rows[0]["sfzh"] = ""
            else:
                rows = []

        if not rows:
            raise HTTPException(status_code=401, detail="用户不存在或已离职，请先登录本系统")
        sfzh = (rows[0].get("sfzh") or "").strip().replace(" ", "")
        if not sfzh:
            raise HTTPException(status_code=400, detail="您的账号未维护身份证号，无法使用单点登录，请联系管理员")

        expire = getattr(settings, "SSO_TICKET_EXPIRE_SECONDS", 120) or 120
        ticket = _make_ticket(sfzh, name, expire)
        base_url = (settings.SSO_TARGET_B_BASE_URL or "").strip().rstrip("/")
        entry_path = (settings.SSO_TARGET_B_ENTRY_PATH or "/sso/entry").strip()
        if not entry_path.startswith("/"):
            entry_path = "/" + entry_path
        url = f"{base_url}{entry_path}?ticket={ticket}"
        return {"success": True, "url": url}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("生成 SSO 链接失败: %s", e)
        raise HTTPException(status_code=500, detail="生成免登链接失败")
