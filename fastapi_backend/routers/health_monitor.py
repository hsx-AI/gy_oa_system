# -*- coding: utf-8 -*-
"""
系统管理员页面 - 仅 webconfig.admin1 可访问。
包含：系统配置、数据库、大模型、人事档案系统、思想汇报系统、打卡数据自动获取服务等。
"""
import logging
import asyncio
import json
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
    email_include_send_day: bool = False
    email_start_offset_days: int = 1
    holiday_email_days_before: int = -1
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


class DeepseekKeyRequest(BaseModel):
    current_user: str
    deepseek_api_key: str = ""
    clear: bool = False


class LlmModelRequest(BaseModel):
    current_user: str
    name: str
    base_url: str
    model: str
    api_key: str = ""
    use_extra: bool = True


class ActivateRequest(BaseModel):
    current_user: str


class LlmTestRequest(BaseModel):
    current_user: str
    model_id: Optional[int] = None  # 指定本地候选模型；为空则测试当前生效模型


class LlmSceneModelRequest(BaseModel):
    current_user: str
    model_id: Optional[int] = None


class ActionSupervisionItem(BaseModel):
    leader_name: str
    departments: List[str] = Field(default_factory=list)
    work_division: str = ""
    enabled: bool = True


class ActionSupervisionConfigRequest(BaseModel):
    current_user: str
    items: List[ActionSupervisionItem] = Field(default_factory=list)


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


# ==================== 行动项分管领导配置 ====================

def _action_supervision_payload() -> dict:
    from routers.action_items import (
        _action_directory_maps, _load_supervision_configs, ensure_tables,
    )
    from routers.ai_assistant import SHIFT_BUSINESS_DEPARTMENTS

    ensure_tables()
    departments, _, _, _, _ = _action_directory_maps()
    departments = departments.intersection({*SHIFT_BUSINESS_DEPARTMENTS, "部办"})
    rows = db.execute_query(
        "SELECT name,jb FROM yggl WHERE COALESCE(zaizhi,0)=0 "
        "AND name IS NOT NULL AND TRIM(name)<>'' ORDER BY name"
    ) or []
    candidates = []
    seen = set()
    for row in rows:
        name = (row.get("name") or "").strip()
        job = (row.get("jb") or "").strip()
        if not name or name in seen or job not in {"经理", "副经理", "部长", "副部长"}:
            continue
        seen.add(name)
        candidates.append({"leader_name": name, "job": job})
    configs = {
        item["leader_name"]: item for item in _load_supervision_configs(enabled_only=False)
    }
    enabled_configs = [item for item in configs.values() if item.get("enabled")]
    covered_departments = {
        department
        for item in enabled_configs
        for department in item.get("departments") or []
    }
    leaders = []
    for candidate in candidates:
        configured = configs.get(candidate["leader_name"], {})
        leaders.append({
            **candidate,
            "departments": configured.get("departments") or [],
            "work_division": configured.get("work_division") or "",
            "enabled": bool(configured.get("enabled")),
            "updated_by": configured.get("updated_by") or "",
            "updated_at": configured.get("updated_at") or "",
        })
    return {
        "departments": sorted(departments),
        "leaders": leaders,
        "uncovered_departments": sorted(departments - covered_departments),
    }


@router.get("/action-supervision-config")
async def get_action_supervision_config(
    current_user: str = Query(..., description="当前登录用户，用于权限校验"),
):
    """获取行动项科室分管领导及工作分工配置。仅 admin1。"""
    _require_admin1(current_user)
    return {"success": True, **_action_supervision_payload()}


@router.post("/action-supervision-config")
async def save_action_supervision_config(req: ActionSupervisionConfigRequest):
    """批量保存行动项科室分管领导及工作分工配置。仅 admin1。"""
    _require_admin1(req.current_user)
    from routers.action_items import (
        _event, _load_supervision_configs, _normalize_department_name, ensure_tables,
    )

    ensure_tables()
    payload = _action_supervision_payload()
    allowed_leaders = {item["leader_name"] for item in payload["leaders"]}
    allowed_departments = set(payload["departments"])
    requested: dict[str, ActionSupervisionItem] = {}
    for item in req.items:
        leader = (item.leader_name or "").strip()
        if not leader or leader not in allowed_leaders:
            raise HTTPException(status_code=400, detail=f"无效或非在职部门领导：{leader or '未填写'}")
        if leader in requested:
            raise HTTPException(status_code=400, detail=f"主管领导重复：{leader}")
        departments = list(dict.fromkeys(
            _normalize_department_name(name) for name in item.departments
            if (name or "").strip()
        ))
        invalid = [name for name in departments if name not in allowed_departments]
        if invalid:
            raise HTTPException(
                status_code=400, detail=f"{leader} 存在无效科室：{'、'.join(invalid)}"
            )
        division = (item.work_division or "").strip()
        if len(division) > 4000:
            raise HTTPException(status_code=400, detail=f"{leader} 的工作分工不能超过4000字")
        if item.enabled and not departments:
            raise HTTPException(status_code=400, detail=f"{leader} 启用时至少选择一个分管科室")
        requested[leader] = item.model_copy(update={
            "leader_name": leader,
            "departments": departments,
            "work_division": division,
        })

    before = _load_supervision_configs(enabled_only=False)
    for leader in allowed_leaders:
        item = requested.get(leader)
        departments = item.departments if item else []
        work_division = item.work_division if item else ""
        enabled = 1 if item and item.enabled else 0
        db.execute_update(
            "INSERT INTO action_supervision_config "
            "(leader_name,departments,work_division,enabled,updated_by) "
            "VALUES (%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE "
            "departments=VALUES(departments),work_division=VALUES(work_division),"
            "enabled=VALUES(enabled),updated_by=VALUES(updated_by),updated_at=NOW()",
            (
                leader,
                json.dumps(departments, ensure_ascii=False),
                work_division, enabled, req.current_user.strip(),
            ),
        )
    after = _load_supervision_configs(enabled_only=False)
    _event(
        req.current_user.strip(), "系统配置", "更新行动项科室分管领导及工作分工",
        data={"before": before, "after": after},
    )
    return {
        "success": True,
        "message": "行动项分管领导配置已保存，后续 AI 提取将立即使用",
        **_action_supervision_payload(),
    }


# ==================== 大模型配置（DeepSeek 开关 + 多本地模型管理） ====================

def _ensure_column(table: str, column: str, ddl: str) -> None:
    """幂等地为表补列（不同环境的库可能缺列）。"""
    try:
        rows = db.execute_query(
            "SELECT COUNT(*) AS c FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s",
            (table, column),
        )
        if rows and rows[0].get("c"):
            return
        db.execute_update(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        logger.info("已为 %s 增加列 %s", table, column)
    except Exception as e:
        logger.warning("确保列 %s.%s 失败: %s", table, column, e)


def _ensure_llm_models_table() -> None:
    """确保本地大模型候选表存在，并为新增能力补齐字段。

    api_key   : 鉴权 token（如 DeepSeek-V4 网关的 JWT；Ollama 留空即可）
    use_extra : 是否附带 Ollama/qwen 专用的 enable_thinking 参数
                （1=Ollama 本地；0=OpenAI 兼容网关，如本地 DeepSeek-V4）
    """
    db.execute_update(
        """
        CREATE TABLE IF NOT EXISTS llm_models (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            base_url VARCHAR(512) NOT NULL,
            model VARCHAR(128) NOT NULL,
            api_key TEXT NULL,
            use_extra TINYINT NOT NULL DEFAULT 1,
            is_active TINYINT NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    # 兼容已存在的旧表 / 不同环境的库
    _ensure_column("llm_models", "api_key", "TEXT NULL")
    _ensure_column("llm_models", "use_extra", "TINYINT NOT NULL DEFAULT 1")
    # 当前生效本地模型的鉴权与接口类型（写入 webconfig，供 _resolve_llm 读取）
    _ensure_column("webconfig", "llm_api_key", "TEXT NULL")
    _ensure_column("webconfig", "llm_use_extra", "TINYINT NOT NULL DEFAULT 1")


LLM_SCENES = {
    "inbox_tasks": "AI 待办看板",
    "holiday_parse": "假期通知解析",
    "action_items": "行动项提取",
}
ONLINE_DEEPSEEK_MODEL_ID = -1


def _ensure_llm_scene_config_table() -> None:
    _ensure_llm_models_table()
    db.execute_update(
        """
        CREATE TABLE IF NOT EXISTS llm_scene_config (
            scene VARCHAR(50) PRIMARY KEY,
            model_id INT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def _model_row_to_public(row: Optional[dict]) -> Optional[dict]:
    if not row:
        return None
    mk = (row.get("api_key") or "").strip()
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "base_url": row.get("base_url"),
        "model": row.get("model"),
        "use_extra": bool(row.get("use_extra")),
        "has_key": bool(mk),
        "key_masked": _mask_key(mk),
        "is_active": bool(row.get("is_active")),
    }


def _get_llm_model_row(model_id: Optional[int]) -> Optional[dict]:
    if not model_id:
        return None
    rows = db.execute_query(
        "SELECT id, name, base_url, model, api_key, use_extra, is_active FROM llm_models WHERE id=%s LIMIT 1",
        (int(model_id),),
    )
    return rows[0] if rows else None


def _get_llm_scene_configs() -> List[dict]:
    _ensure_llm_scene_config_table()
    rows = db.execute_query("SELECT scene, model_id FROM llm_scene_config", ()) or []
    by_scene = {(r.get("scene") or "").strip(): r.get("model_id") for r in rows}
    out = []
    for scene, label in LLM_SCENES.items():
        model_id = by_scene.get(scene)
        model_row = (
            _get_llm_model_row(model_id)
            if model_id and int(model_id) != ONLINE_DEEPSEEK_MODEL_ID else None
        )
        out.append({
            "scene": scene,
            "label": label,
            "model_id": model_id or 0,
            "model": _model_row_to_public(model_row),
            "provider": "deepseek" if model_id == ONLINE_DEEPSEEK_MODEL_ID else (
                "configured" if model_row else "follow"
            ),
        })
    return out


def get_local_llm_model_for_scene(scene: str) -> dict:
    """返回指定功能场景绑定的本地模型；未绑定时回退 webconfig.llm_base_url / llm_model。"""
    _ensure_llm_scene_config_table()
    model_row = None
    try:
        rows = db.execute_query(
            "SELECT model_id FROM llm_scene_config WHERE scene=%s LIMIT 1",
            ((scene or "").strip(),),
        ) or []
        model_id = rows[0].get("model_id") if rows else None
        model_row = _get_llm_model_row(model_id) if model_id else None
    except Exception as e:
        logger.debug("读取场景大模型配置失败 scene=%s: %s", scene, e)
    if model_row:
        return {
            "base_url": (model_row.get("base_url") or "").strip(),
            "model": (model_row.get("model") or "").strip(),
        }

    rows = db.execute_query("SELECT llm_base_url, llm_model FROM webconfig WHERE id=%s LIMIT 1", ("1",)) or []
    if rows:
        return {
            "base_url": (rows[0].get("llm_base_url") or "").strip(),
            "model": (rows[0].get("llm_model") or "").strip(),
        }
    return {"base_url": "", "model": ""}


def _mask_key(key: str) -> str:
    k = (key or "").strip()
    if not k:
        return ""
    if len(k) <= 8:
        return "****"
    return f"{k[:4]}****{k[-4:]}"


@router.get("/llm-config")
async def get_llm_config_api(current_user: str = Query(..., description="当前登录用户，用于权限校验")):
    """获取大模型配置：DeepSeek 开关状态 + 本地候选模型列表 + 当前生效模型。仅 admin1。"""
    _require_admin1(current_user)
    _ensure_llm_models_table()

    key = ""
    base_url = ""
    model = ""
    rows = db.execute_query(
        "SELECT deepseek_api_key, llm_base_url, llm_model FROM webconfig WHERE id=%s LIMIT 1", ("1",)
    )
    if rows:
        key = (rows[0].get("deepseek_api_key") or "").strip()
        base_url = (rows[0].get("llm_base_url") or "").strip()
        model = (rows[0].get("llm_model") or "").strip()

    def _list_models():
        rows2 = db.execute_query(
            "SELECT id, name, base_url, model, api_key, use_extra, is_active FROM llm_models ORDER BY id"
        ) or []
        out = []
        for m in rows2:
            out.append(_model_row_to_public(m))
        return out

    models = _list_models()

    # 首次访问且候选表为空时，把 webconfig 中已有的本地模型作为初始候选并标记为选中（默认 Ollama 接口）
    if not models and base_url and model:
        db.execute_update(
            "INSERT INTO llm_models (name, base_url, model, api_key, use_extra, is_active) "
            "VALUES (%s, %s, %s, '', 1, 1)",
            (f"本地 {model}", base_url, model),
        )
        models = _list_models()

    return {
        "success": True,
        "deepseek_configured": bool(key),
        "deepseek_key_masked": _mask_key(key),
        "provider": "deepseek" if key else "local",
        "active": {"base_url": base_url, "model": model},
        "models": models,
        "scene_configs": _get_llm_scene_configs(),
    }


@router.post("/llm-config")
async def save_llm_config_api(req: DeepseekKeyRequest):
    """保存/清空 DeepSeek API Key（webconfig.deepseek_api_key）。为空时系统使用本地模型。仅 admin1。"""
    _require_admin1(req.current_user)
    key = (req.deepseek_api_key or "").strip()
    if req.clear:
        db.execute_update("UPDATE webconfig SET deepseek_api_key='' WHERE id=%s", ("1",))
        return {"success": True, "deepseek_configured": False,
                "message": "已清空 DeepSeek 密钥，系统将使用本地模型"}
    if not key:
        raise HTTPException(status_code=400, detail="请输入要保存的 DeepSeek 密钥；如需停用请点击清空")
    db.execute_update("UPDATE webconfig SET deepseek_api_key=%s WHERE id=%s", (key, "1"))
    return {"success": True, "deepseek_configured": True,
            "message": "DeepSeek 密钥已更新，系统将优先使用联网 DeepSeek 模型"}


@router.post("/llm-models")
async def add_llm_model_api(req: LlmModelRequest):
    """新增一个本地大模型候选。仅 admin1。"""
    _require_admin1(req.current_user)
    _ensure_llm_models_table()
    name = (req.name or "").strip()
    base_url = (req.base_url or "").strip()
    model = (req.model or "").strip()
    api_key = (req.api_key or "").strip()
    use_extra = 1 if req.use_extra else 0
    if not (name and base_url and model):
        raise HTTPException(status_code=400, detail="请填写完整：名称 / base_url / 模型名")
    db.execute_update(
        "INSERT INTO llm_models (name, base_url, model, api_key, use_extra, is_active) "
        "VALUES (%s, %s, %s, %s, %s, 0)",
        (name, base_url, model, api_key, use_extra),
    )
    return {"success": True, "message": f"已添加本地模型「{name}」"}


@router.delete("/llm-models/{model_id}")
async def delete_llm_model_api(
    model_id: int,
    current_user: str = Query(..., description="当前登录用户，用于权限校验"),
):
    """删除一个本地大模型候选。仅 admin1。"""
    _require_admin1(current_user)
    _ensure_llm_models_table()
    db.execute_update("DELETE FROM llm_models WHERE id=%s", (model_id,))
    return {"success": True, "message": "已删除该本地模型"}


@router.post("/llm-models/{model_id}/activate")
async def activate_llm_model_api(model_id: int, req: ActivateRequest):
    """将某个本地模型设为当前生效模型（写入 webconfig.llm_base_url / llm_model）。仅 admin1。
    注意：仅当 DeepSeek 密钥为空时，本地模型才会实际生效。"""
    _require_admin1(req.current_user)
    _ensure_llm_models_table()
    rows = db.execute_query(
        "SELECT name, base_url, model, api_key, use_extra FROM llm_models WHERE id=%s LIMIT 1", (model_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="该本地模型不存在")
    name = (rows[0].get("name") or "").strip()
    base_url = (rows[0].get("base_url") or "").strip()
    model = (rows[0].get("model") or "").strip()
    api_key = (rows[0].get("api_key") or "").strip()
    use_extra = 1 if rows[0].get("use_extra") else 0
    db.execute_update("UPDATE llm_models SET is_active=0", ())
    db.execute_update("UPDATE llm_models SET is_active=1 WHERE id=%s", (model_id,))
    db.execute_update(
        "UPDATE webconfig SET llm_base_url=%s, llm_model=%s, llm_api_key=%s, llm_use_extra=%s WHERE id=%s",
        (base_url, model, api_key, use_extra, "1"),
    )

    deepseek_key = ""
    drows = db.execute_query("SELECT deepseek_api_key FROM webconfig WHERE id=%s LIMIT 1", ("1",))
    if drows:
        deepseek_key = (drows[0].get("deepseek_api_key") or "").strip()
    extra = "（当前 DeepSeek 密钥非空，仍会优先使用联网模型；清空密钥后本地模型即生效）" if deepseek_key else "，已立即生效"
    return {"success": True, "message": f"已切换本地模型为「{name}」{extra}"}


@router.post("/llm-scenes/{scene}/model")
async def save_llm_scene_model_api(scene: str, req: LlmSceneModelRequest):
    """为指定功能场景绑定模型；0 跟随全局，-1 为联网 DeepSeek，正数为候选模型。"""
    _require_admin1(req.current_user)
    _ensure_llm_scene_config_table()
    scene_key = (scene or "").strip()
    if scene_key not in LLM_SCENES:
        raise HTTPException(status_code=404, detail="未知的大模型功能场景")
    model_id = int(req.model_id or 0)
    if model_id == ONLINE_DEEPSEEK_MODEL_ID:
        if scene_key != "action_items":
            raise HTTPException(status_code=400, detail="该功能场景暂不支持联网 DeepSeek")
        rows = db.execute_query(
            "SELECT deepseek_api_key FROM webconfig WHERE id=%s LIMIT 1", ("1",)
        ) or []
        if not rows or not (rows[0].get("deepseek_api_key") or "").strip():
            raise HTTPException(status_code=400, detail="请先保存联网 DeepSeek API Key")
    elif model_id < 0:
        raise HTTPException(status_code=400, detail="无效的模型选项")
    elif model_id:
        row = _get_llm_model_row(model_id)
        if not row:
            raise HTTPException(status_code=404, detail="选择的模型不存在")
    db.execute_update(
        "INSERT INTO llm_scene_config (scene, model_id) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE model_id=VALUES(model_id), updated_at=CURRENT_TIMESTAMP",
        (scene_key, model_id or None),
    )
    return {
        "success": True,
        "message": f"{LLM_SCENES[scene_key]}模型配置已保存",
        "scene_configs": _get_llm_scene_configs(),
    }


def _estimate_tokens(s: str) -> int:
    """粗略估算 token 数（当网关不返回 usage 时使用）：中文按字计，其余按约 4 字符/词折算。"""
    import re
    if not s:
        return 0
    cjk = len(re.findall(r"[\u4e00-\u9fff]", s))
    other = len(re.sub(r"[\u4e00-\u9fff]", "", s))
    return cjk + max(0, round(other / 4))


def _run_llm_benchmark(cfg: dict) -> dict:
    """对给定模型配置发起一次测试对话，统计首字延迟与生成速度（tokens/s）。"""
    import time
    try:
        from openai import OpenAI
    except ImportError:
        return {"ok": False, "message": "服务端未安装 openai SDK"}

    base_url = cfg.get("base_url") or ""
    model = cfg.get("model") or ""
    if not base_url or not model:
        return {"ok": False, "message": "该模型未配置 base_url 或模型名"}

    prompt = "请用一段话简要介绍你自己，并说明你能为工艺部门员工提供哪些帮助。约80字。"
    messages = [{"role": "user", "content": prompt}]
    extra_body = {"chat_template_kwargs": {"enable_thinking": False}} if cfg.get("use_extra") else None

    try:
        client = OpenAI(base_url=base_url, api_key=cfg.get("api_key") or "ollama", timeout=60.0)
    except Exception as e:
        return {"ok": False, "message": f"初始化客户端失败：{e}"}

    def _do_stream(with_usage: bool):
        kwargs = dict(model=model, messages=messages, stream=True, temperature=0.5)
        if with_usage:
            kwargs["stream_options"] = {"include_usage": True}
        if extra_body:
            kwargs["extra_body"] = extra_body
        return client.chat.completions.create(**kwargs)

    t0 = time.perf_counter()
    ttft = None
    pieces: list[str] = []
    usage = None
    try:
        try:
            stream = _do_stream(True)
        except Exception:
            stream = _do_stream(False)  # 部分网关不支持 stream_options
        for ev in stream:
            u = getattr(ev, "usage", None)
            if u:
                usage = u
            if not getattr(ev, "choices", None):
                continue
            delta = ev.choices[0].delta
            piece = getattr(delta, "content", None) or ""
            if piece:
                if ttft is None:
                    ttft = time.perf_counter() - t0
                pieces.append(piece)
    except Exception as e:
        return {"ok": False, "message": f"调用失败：{e}"}

    elapsed = time.perf_counter() - t0
    content = "".join(pieces)
    comp_tokens = None
    if usage is not None:
        comp_tokens = getattr(usage, "completion_tokens", None)
    estimated = False
    if not comp_tokens:
        comp_tokens = _estimate_tokens(content)
        estimated = True
    gen_time = elapsed - (ttft or 0)
    denom = gen_time if gen_time and gen_time > 0.05 else elapsed
    tps = round(comp_tokens / denom, 1) if denom > 0 and comp_tokens else 0.0

    sample = content.strip().replace("\n", " ")
    if len(sample) > 120:
        sample = sample[:120] + "…"

    return {
        "ok": True,
        "tokens_per_sec": tps,
        "completion_tokens": comp_tokens,
        "estimated": estimated,
        "ttft_ms": round((ttft or 0) * 1000),
        "elapsed_ms": round(elapsed * 1000),
        "sample": sample,
    }


@router.post("/llm-test")
async def llm_test_api(req: LlmTestRequest):
    """对当前生效模型或指定本地候选模型做一次连通/速度测试，返回 tokens/s 等指标。仅 admin1。"""
    _require_admin1(req.current_user)
    _ensure_llm_models_table()

    try:
        from routers.ai_assistant import _resolve_llm, _normalize_llm_base_url, _model_label
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载大模型配置失败：{e}")

    if req.model_id:
        rows = db.execute_query(
            "SELECT name, base_url, model, api_key, use_extra FROM llm_models WHERE id=%s LIMIT 1",
            (req.model_id,),
        )
        if not rows:
            raise HTTPException(status_code=404, detail="该本地模型不存在")
        r = rows[0]
        cfg = {
            "provider": "local",
            "base_url": _normalize_llm_base_url((r.get("base_url") or "").strip()),
            "model": (r.get("model") or "").strip(),
            "api_key": (r.get("api_key") or "").strip() or "ollama",
            "use_extra": bool(r.get("use_extra")),
        }
        label = (r.get("name") or cfg["model"]).strip()
    else:
        cfg = _resolve_llm()
        label = _model_label(cfg)

    result = await asyncio.to_thread(_run_llm_benchmark, cfg)
    result["label"] = label
    result["model"] = cfg.get("model")
    if not result.get("ok"):
        return {"success": True, **result}
    return {"success": True, **result}
