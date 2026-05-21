# -*- coding: utf-8 -*-
"""
系统管理员页面 - 仅 webconfig.admin1 可访问。
包含：系统配置、数据库、大模型、人事档案系统、思想汇报系统、打卡数据自动获取服务等。
"""
import logging
from typing import Optional, Any, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from database import db
from config import settings
from routers.db_manager import _get_admin1

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health-monitor", tags=["系统管理员"])


class ShiftEmailFeatureConfigRequest(BaseModel):
    current_user: str
    enabled_departments: List[str] = Field(default_factory=list)


def _require_admin1(current_user: str) -> None:
    admin1 = _get_admin1()
    if not admin1 or (current_user or "").strip() != admin1:
        raise HTTPException(status_code=403, detail="仅系统管理员（webconfig.admin1）可访问")


@router.get("/permission")
async def health_monitor_permission(
    current_user: str = Query(..., description="当前登录用户姓名"),
):
    """检查当前用户是否有健康监控权限（admin1）。返回 { canAccess: true/false }"""
    admin1 = _get_admin1()
    can = bool(admin1 and (current_user or "").strip() == admin1)
    return {"success": True, "canAccess": can}


async def _check_database() -> dict:
    """数据库连接状态"""
    try:
        db.execute_query("SELECT 1")
        return {"status": "ok", "message": "连接正常"}
    except Exception as e:
        logger.exception("健康检查-数据库异常")
        return {"status": "error", "message": str(e)}


def _get_llm_config() -> dict:
    """从 webconfig 读取大模型配置（与 holiday 逻辑一致）。"""
    try:
        rows = db.execute_query(
            "SELECT llm_base_url, llm_model, deepseek_api_key FROM webconfig WHERE id = %s LIMIT 1",
            ("1",),
        )
        if not rows:
            return {}
        r = rows[0]
        base_url = (r.get("llm_base_url") or "").strip() or None
        model = (r.get("llm_model") or "").strip() or None
        api_key = (r.get("deepseek_api_key") or "").strip() or None
        if not api_key:
            import os
            api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip() or None
        return {"base_url": base_url, "model": model, "api_key": api_key}
    except Exception as e:
        logger.debug("读取大模型配置失败: %s", e)
        return {}


async def _check_llm() -> dict:
    """大模型连接/配置状态"""
    import httpx
    cfg = _get_llm_config()
    base_url = cfg.get("base_url")
    api_key = cfg.get("api_key")
    if base_url:
        url = base_url.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return {"status": "ok", "message": "本地大模型可访问"}
                return {"status": "error", "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    if api_key:
        return {"status": "ok", "message": "已配置公网 API（DeepSeek 等），未做连通性探测"}
    return {"status": "unconfigured", "message": "未配置本地大模型或公网 API"}


async def _check_personnel_archive() -> dict:
    """人事档案系统（PERSONNEL_ARCHIVE_URL）"""
    url = (getattr(settings, "PERSONNEL_ARCHIVE_URL", None) or "").strip()
    if not url:
        return {"status": "unconfigured", "message": "未配置 PERSONNEL_ARCHIVE_URL"}
    import httpx
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if 200 <= resp.status_code < 400:
                return {"status": "ok", "message": "可访问"}
            return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _check_sixianghuibao() -> dict:
    """思想汇报管理系统（SSO_SIXIANGHUIBAO_BASE_URL）。后端路由在 /api 下，根路径可能 404，故探测 /api/sso/entry。"""
    base = (getattr(settings, "SSO_SIXIANGHUIBAO_BASE_URL", None) or "").strip()
    if not base:
        return {"status": "unconfigured", "message": "未配置 SSO_SIXIANGHUIBAO_BASE_URL"}
    import httpx
    # 思想汇报后端入口在 /api/sso/entry，GET 无 ticket 可能返回 422/400，视为服务可达
    entry_path = getattr(settings, "SSO_SIXIANGHUIBAO_ENTRY_PATH", None) or "/api/sso/entry"
    url = base.rstrip("/") + ("/" + entry_path.lstrip("/") if entry_path else "")
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(url)
            # 200/302 正常；400/422 表示接口存在但缺参数，也说明服务在跑
            if resp.status_code in (200, 302, 400, 422):
                return {"status": "ok", "message": "可访问"}
            return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _check_attendance_fetch_service() -> dict:
    """打卡数据自动获取服务（ATTENDANCE_FETCH_HEALTH_URL，期望返回 {"status":"ok"}）"""
    url = (getattr(settings, "ATTENDANCE_FETCH_HEALTH_URL", None) or "").strip()
    if not url:
        return {"status": "unconfigured", "message": "未配置 ATTENDANCE_FETCH_HEALTH_URL"}
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"status": "error", "message": f"HTTP {resp.status_code}"}
            try:
                data = resp.json()
                if data.get("status") == "ok":
                    return {"status": "ok", "message": "服务正常"}
                return {"status": "error", "message": f"响应异常: {data.get('status', data)}"}
            except Exception:
                return {"status": "error", "message": "响应非 JSON 或格式异常"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _check_scheduler() -> dict:
    """每日拉取任务配置状态（不探测实际调度，仅看配置是否就绪；执行时间来自 SCHEDULER_HOUR/SCHEDULER_MINUTE）"""
    fetch_url = (getattr(settings, "ATTENDANCE_REPORT_FETCH_URL", None) or "").strip()
    if not fetch_url:
        return {"status": "unconfigured", "message": "未配置 ATTENDANCE_REPORT_FETCH_URL"}
    tz = getattr(settings, "SCHEDULER_TIMEZONE", "Asia/Shanghai")
    hour = getattr(settings, "SCHEDULER_HOUR", 0)
    minute = getattr(settings, "SCHEDULER_MINUTE", 0)
    time_str = f"{hour}:{minute:02d}"
    return {"status": "ok", "message": f"已配置，每日 {time_str}（{tz}）执行"}


@router.get("/overview")
async def get_health_overview(
    current_user: str = Query(..., description="当前登录用户，用于权限校验"),
):
    """
    获取系统各组件健康状态。仅 admin1 可访问。
    返回: { success, items: [ { id, name, status, message } ] }
    status: ok | error | unconfigured
    """
    _require_admin1(current_user)

    items: list[dict[str, Any]] = []
    checks = [
        ("database", "数据库连接", _check_database),
        ("llm", "大模型服务", _check_llm),
        ("personnel_archive", "人事档案系统", _check_personnel_archive),
        ("sixianghuibao", "思想汇报管理系统", _check_sixianghuibao),
        ("attendance_fetch", "打卡数据自动获取服务", _check_attendance_fetch_service),
        ("scheduler", "定时拉取打卡报表任务配置", _check_scheduler),
    ]
    for id_, name, coro in checks:
        try:
            result = await coro()
            items.append({
                "id": id_,
                "name": name,
                "status": result.get("status", "error"),
                "message": result.get("message", ""),
            })
        except Exception as e:
            logger.exception("健康检查 %s 异常", id_)
            items.append({"id": id_, "name": name, "status": "error", "message": str(e)})

    return {"success": True, "items": items}


@router.get("/shift-email-config")
async def get_shift_email_feature_config(
    current_user: str = Query(..., description="当前登录用户，用于权限校验"),
):
    """获取各科室排班邮件功能开关配置。仅 admin1 可访问。"""
    _require_admin1(current_user)
    from routers.shift_schedule import _get_shift_email_feature_config_items
    data = _get_shift_email_feature_config_items()
    return {"success": True, **data}


@router.post("/shift-email-config")
async def save_shift_email_feature_config(req: ShiftEmailFeatureConfigRequest):
    """保存各科室排班邮件功能开关配置。仅 admin1 可访问。"""
    _require_admin1(req.current_user)
    from routers.shift_schedule import _save_shift_email_feature_config
    data = _save_shift_email_feature_config(req.enabled_departments)
    return {"success": True, "message": "排班邮件功能配置已保存", **data}
