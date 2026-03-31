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


def _get_sixianghuibao_url(name: str) -> str:
    """生成思想汇报系统免登 URL（使用用户名映射，不要求身份证号）。"""
    base_url = (getattr(settings, "SSO_SIXIANGHUIBAO_BASE_URL", None) or "").strip().rstrip("/")
    entry_path = (getattr(settings, "SSO_SIXIANGHUIBAO_ENTRY_PATH", None) or "/sso/entry").strip()
    if not entry_path.startswith("/"):
        entry_path = "/" + entry_path
    expire = getattr(settings, "SSO_TICKET_EXPIRE_SECONDS", 120) or 120
    # 思想汇报按用户名映射：ticket 的 sub 与 name 均传姓名/用户名
    ticket = _make_ticket(name, name, expire)
    return f"{base_url}{entry_path}?ticket={ticket}"


@router.get("/sixianghuibao-todos")
async def get_sixianghuibao_todos(
    name: str = Query(..., description="当前用户姓名，与思想汇报系统 username 一致"),
):
    """
    供 OA 首页待办提醒：代理请求思想汇报系统的 GET /api/integration/oa/todos，
    返回该用户在思想汇报中的待办数量（待审核 + 被退回）。未配置或请求失败时返回 total=0。
    """
    base_url = (getattr(settings, "SSO_SIXIANGHUIBAO_BASE_URL", None) or "").strip().rstrip("/")
    if not base_url:
        return {"username": name, "pending_reviews": 0, "returned_reports": 0, "total": 0}
    import httpx
    url = f"{base_url}/api/integration/oa/todos"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params={"username": (name or "").strip()})
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "username": data.get("username", name),
                    "pending_reviews": data.get("pending_reviews", 0),
                    "returned_reports": data.get("returned_reports", 0),
                    "total": data.get("total", 0),
                    "role": data.get("role", ""),
                    "role_label": data.get("role_label", ""),
                    "action_label": data.get("action_label", ""),
                    "hint": data.get("hint", ""),
                    "author_names": data.get("author_names", []),
                }
    except Exception as e:
        logger.warning("请求思想汇报待办失败: %s", e)
    return {"username": name, "pending_reviews": 0, "returned_reports": 0, "total": 0,
            "role": "", "role_label": "", "action_label": "", "hint": "", "author_names": []}


@router.get("/personnel-pending")
async def get_personnel_pending_count(
    name: str = Query(..., description="当前用户姓名，用于查询 yggl.sfzh"),
):
    """
    代理请求人事档案系统的待办数量接口。
    通过姓名查 yggl.sfzh，再调用 http://10.42.60.230:18080/file/api/message/pending-count?idCard=sfzh
    """
    result = {"myPendingCount": 0, "needAuditCount": 0}
    name = (name or "").strip()
    if not name:
        return {"success": True, **result}
    try:
        rows = db.execute_query(
            "SELECT sfzh FROM yggl WHERE name = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
            (name,),
        )
        sfzh = (rows[0].get("sfzh") or "").strip() if rows else ""
        if not sfzh:
            return {"success": True, **result}
    except Exception as e:
        logger.warning("查询 sfzh 失败: %s", e)
        return {"success": True, **result}

    import httpx
    url = "http://10.42.60.230:18080/file/api/message/pending-count"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params={"idCard": sfzh})
            if resp.status_code == 200:
                data = resp.json()
                inner = data.get("data") or {}
                result["myPendingCount"] = inner.get("myPendingCount", 0)
                result["needAuditCount"] = inner.get("needAuditCount", 0)
    except Exception as e:
        logger.warning("请求人事档案系统待办数失败: %s", e)
    return {"success": True, **result}


@router.get("/link")
async def get_sso_link(
    target: str = Query(..., description="目标系统标识：B=人事档案，sixianghuibao=思想汇报管理"),
    name: str = Query(..., description="当前登录用户姓名，用于校验并生成 ticket"),
):
    """
    生成免登链接：校验当前用户已登录（在 yggl 中存在），生成 ticket 并返回目标系统入口 URL。
    前端拿到 url 后执行 window.location.href = url 或 window.open(url) 即可跳转并带 ticket 单点登录。
    """
    target = (target or "").strip().lower()
    name = (name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="请传入当前用户姓名")

    # 思想汇报管理子系统（用户名映射，不要求身份证号）
    if target == "sixianghuibao":
        if not (getattr(settings, "SSO_SIXIANGHUIBAO_BASE_URL", None) or "").strip():
            raise HTTPException(status_code=503, detail="未配置思想汇报系统地址 SSO_SIXIANGHUIBAO_BASE_URL")
        if not (settings.SSO_SECRET or "").strip():
            raise HTTPException(status_code=503, detail="未配置 SSO 签名密钥 SSO_SECRET")
        try:
            rows = db.execute_query(
                "SELECT name FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1",
                (name,),
            )
            if not rows:
                raise HTTPException(status_code=401, detail="用户不存在或已离职，请先登录本系统")
            url = _get_sixianghuibao_url(name)
            return {"success": True, "url": url}
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("生成思想汇报 SSO 链接失败: %s", e)
            raise HTTPException(status_code=500, detail="生成免登链接失败")

    # 人事档案系统 B（需身份证号）
    if target != "b":
        raise HTTPException(status_code=400, detail="目标系统仅支持：B（人事档案）、sixianghuibao（思想汇报管理）")
    if not (settings.SSO_TARGET_B_BASE_URL or "").strip():
        raise HTTPException(status_code=503, detail="未配置目标系统地址 SSO_TARGET_B_BASE_URL")
    if not (settings.SSO_SECRET or "").strip():
        raise HTTPException(status_code=503, detail="未配置 SSO 签名密钥 SSO_SECRET")

    try:
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
