# -*- coding: utf-8 -*-
"""
系统管理员页面 - 仅 webconfig.admin1 可访问。
包含：系统配置、数据库、大模型、人事档案系统、思想汇报系统、打卡数据自动获取服务等。
"""
import logging
import asyncio
import os
import platform
import shutil
from typing import Optional, Any, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from database import db
from config import settings
from routers.db_manager import _get_admin1

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health-monitor", tags=["系统管理员"])


class ShiftEmailRecipientItem(BaseModel):
    name: str = ""
    email: str = ""
    unit: str = "其他"


class ShiftEmailDeptSettingsItem(BaseModel):
    department: str
    email_send_weekday: int = 4
    email_recipients: List[ShiftEmailRecipientItem] = Field(default_factory=list)


class ShiftEmailFeatureConfigRequest(BaseModel):
    current_user: str
    enabled_departments: List[str] = Field(default_factory=list)
    departments: Optional[List[ShiftEmailDeptSettingsItem]] = None


class AttendanceFetchScheduleItem(BaseModel):
    hour: int = Field(0, ge=0, le=23)
    minute: int = Field(0, ge=0, le=59)
    enabled: bool = True
    suggestion_cutoff: str = "yesterday"


class AttendanceFetchConfigRequest(BaseModel):
    current_user: str
    schedules: List[AttendanceFetchScheduleItem] = Field(default_factory=list)


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
    """每日拉取任务配置状态（执行时间与建议截止日来自 webconfig）"""
    from routers.attendance_scheduler_config import get_scheduler_status_message

    fetch_url = (getattr(settings, "ATTENDANCE_REPORT_FETCH_URL", None) or "").strip()
    if not fetch_url:
        return {"status": "unconfigured", "message": "未配置 ATTENDANCE_REPORT_FETCH_URL"}
    return {"status": "ok", "message": get_scheduler_status_message()}


def _format_bytes(size: Any) -> str:
    if size is None:
        return "未知"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= 1024
    return f"{value:.1f}TB"


def _read_proc_cpu_times() -> Optional[tuple[int, int]]:
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            parts = f.readline().split()
        if not parts or parts[0] != "cpu":
            return None
        values = [int(v) for v in parts[1:]]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values)
        return idle, total
    except Exception:
        return None


async def _get_cpu_percent() -> Optional[float]:
    first = _read_proc_cpu_times()
    if not first:
        return None
    await asyncio.sleep(0.1)
    second = _read_proc_cpu_times()
    if not second:
        return None
    idle_delta = second[0] - first[0]
    total_delta = second[1] - first[1]
    if total_delta <= 0:
        return None
    return round(max(0.0, min(100.0, (1 - idle_delta / total_delta) * 100)), 1)


def _get_memory_usage() -> Optional[dict[str, float]]:
    try:
        data: dict[str, int] = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                key, value = line.split(":", 1)
                data[key] = int(value.strip().split()[0]) * 1024
        total = data.get("MemTotal")
        available = data.get("MemAvailable")
        if not total or available is None:
            return None
        used = total - available
        return {
            "total": float(total),
            "used": float(used),
            "percent": round(used / total * 100, 1),
        }
    except Exception:
        return None


def _get_uptime_text() -> str:
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as f:
            seconds = int(float(f.readline().split()[0]))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        if days:
            return f"{days}天{hours}小时"
        if hours:
            return f"{hours}小时{minutes}分钟"
        return f"{minutes}分钟"
    except Exception:
        return "未知"


async def _check_server_resources() -> dict:
    """采集运行后端的 Ubuntu/Linux 服务器资源。"""
    system_name = platform.system()
    if system_name != "Linux":
        return {"status": "unconfigured", "message": f"当前后端运行环境为 {system_name}，仅在 Ubuntu/Linux 服务器上采集资源"}

    cpu_percent = await _get_cpu_percent()
    memory = _get_memory_usage()
    disk = shutil.disk_usage("/")
    disk_percent = round(disk.used / disk.total * 100, 1) if disk.total else 0.0
    cpu_count = os.cpu_count() or 1

    try:
        load1, load5, load15 = os.getloadavg()
        load_text = f"{load1:.2f}/{load5:.2f}/{load15:.2f}"
    except OSError:
        load1 = load5 = load15 = 0.0
        load_text = "未知"

    high_items = []
    if cpu_percent is not None and cpu_percent >= 90:
        high_items.append(f"CPU {cpu_percent}%")
    if memory and memory["percent"] >= 90:
        high_items.append(f"内存 {memory['percent']}%")
    if disk_percent >= 90:
        high_items.append(f"磁盘 {disk_percent}%")
    if load5 >= cpu_count * 2:
        high_items.append(f"5分钟负载 {load5:.2f}")

    cpu_text = f"{cpu_percent}%" if cpu_percent is not None else "未知"
    memory_text = (
        f"{memory['percent']}%（{_format_bytes(memory['used'])}/{_format_bytes(memory['total'])}）"
        if memory else "未知"
    )
    disk_text = f"{disk_percent}%（{_format_bytes(disk.used)}/{_format_bytes(disk.total)}）"
    release_text = platform.platform()
    message = (
        f"CPU：{cpu_text}；内存：{memory_text}；根分区：{disk_text}；"
        f"负载(1/5/15)：{load_text}；运行：{_get_uptime_text()}；系统：{release_text}"
    )

    if high_items:
        return {"status": "error", "message": "资源占用偏高：" + "、".join(high_items) + "。" + message}
    return {"status": "ok", "message": message}


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
        ("server_resources", "Ubuntu 服务器资源", _check_server_resources),
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
    """获取各科室排班邮件配置（功能开关、发送时间、收件人）。仅 admin1 可访问。"""
    _require_admin1(current_user)
    from routers.shift_schedule import _get_shift_email_feature_config_items
    data = _get_shift_email_feature_config_items()
    return {"success": True, **data}


@router.post("/shift-email-config")
async def save_shift_email_feature_config(req: ShiftEmailFeatureConfigRequest):
    """保存各科室排班邮件配置（功能开关、发送时间、收件人）。仅 admin1 可访问。"""
    _require_admin1(req.current_user)
    from routers.shift_schedule import _save_shift_email_feature_config
    data = _save_shift_email_feature_config(
        req.enabled_departments,
        department_email_settings=req.departments,
        updated_by=req.current_user,
    )
    return {"success": True, "message": "排班邮件配置已保存", **data}


@router.get("/attendance-fetch-config")
async def get_attendance_fetch_config(
    current_user: str = Query(..., description="当前登录用户，用于权限校验"),
):
    """获取打卡自动拉取与智能建议截止日配置。仅 admin1 可访问。"""
    _require_admin1(current_user)
    from routers.attendance_scheduler_config import get_attendance_fetch_config_for_api

    return {"success": True, **get_attendance_fetch_config_for_api()}


@router.post("/attendance-fetch-config")
async def save_attendance_fetch_config_api(req: AttendanceFetchConfigRequest):
    """保存打卡自动拉取配置（支持多条每日执行时间）。仅 admin1 可访问。"""
    _require_admin1(req.current_user)
    from routers.attendance_scheduler_config import save_attendance_fetch_config

    try:
        data = save_attendance_fetch_config(
            [s.model_dump() for s in req.schedules],
            updated_by=req.current_user,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "message": "打卡配置已保存并已更新定时任务", **data}
