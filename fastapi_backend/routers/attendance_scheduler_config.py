# -*- coding: utf-8 -*-
"""
打卡报表自动拉取调度配置（存 webconfig，系统管理员页面可改）。
支持多条每日执行时间；每条可单独设置智能建议截止日（今日 / 前一日）。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config import settings
from database import db

logger = logging.getLogger(__name__)

ATTENDANCE_FETCH_CONFIG_COLUMN = "attendance_fetch_config"
MAX_SCHEDULES = 24
# 未在 webconfig 保存过打卡拉取配置时的内置默认（执行时间请在系统管理员页配置）
DEFAULT_SCHEDULER_TIMEZONE = "Asia/Shanghai"
DEFAULT_SCHEDULER_HOUR = 0
DEFAULT_SCHEDULER_MINUTE = 0

_scheduler = None  # AsyncIOScheduler | None


class AttendanceFetchScheduleItem(BaseModel):
    hour: int = Field(0, ge=0, le=23)
    minute: int = Field(0, ge=0, le=59)
    enabled: bool = True
    suggestion_cutoff: str = "yesterday"  # today | yesterday


def _ensure_attendance_fetch_config_column() -> None:
    exists = db.execute_query(
        "SELECT 1 FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'webconfig' AND COLUMN_NAME = %s LIMIT 1",
        (ATTENDANCE_FETCH_CONFIG_COLUMN,),
    )
    if exists:
        return
    db.execute_update(
        f"ALTER TABLE webconfig ADD COLUMN {ATTENDANCE_FETCH_CONFIG_COLUMN} MEDIUMTEXT NULL "
        "COMMENT '打卡自动拉取与建议截止日配置JSON'"
    )


def _normalize_suggestion_cutoff(value: Any) -> str:
    v = (str(value or "")).strip().lower()
    if v in ("today", "今日"):
        return "today"
    return "yesterday"


def _cutoff_label(mode: str) -> str:
    return "今日" if _normalize_suggestion_cutoff(mode) == "today" else "前一日"


def _default_config() -> dict:
    return {
        "timezone": DEFAULT_SCHEDULER_TIMEZONE,
        "schedules": [
            {
                "hour": DEFAULT_SCHEDULER_HOUR,
                "minute": DEFAULT_SCHEDULER_MINUTE,
                "enabled": True,
                "suggestion_cutoff": "yesterday",
            }
        ],
    }


def _normalize_schedules(raw: Any, *, legacy_global_cutoff: str = "yesterday") -> List[dict]:
    if not isinstance(raw, list):
        return []
    out: List[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            hour = int(item.get("hour", 0))
            minute = int(item.get("minute", 0))
        except (TypeError, ValueError):
            continue
        hour = max(0, min(23, hour))
        minute = max(0, min(59, minute))
        enabled = bool(item.get("enabled", True))
        cutoff = _normalize_suggestion_cutoff(
            item.get("suggestion_cutoff", legacy_global_cutoff)
        )
        out.append({
            "hour": hour,
            "minute": minute,
            "enabled": enabled,
            "suggestion_cutoff": cutoff,
        })
        if len(out) >= MAX_SCHEDULES:
            break
    return out


def load_attendance_fetch_config() -> dict:
    """读取配置；未入库时返回 env/config 默认值。"""
    _ensure_attendance_fetch_config_column()
    base = _default_config()
    try:
        rows = db.execute_query(
            f"SELECT {ATTENDANCE_FETCH_CONFIG_COLUMN} FROM webconfig WHERE id = %s LIMIT 1",
            ("1",),
        )
        raw = rows[0].get(ATTENDANCE_FETCH_CONFIG_COLUMN) if rows else None
        if raw is None or raw == "":
            return base
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", errors="ignore")
        data = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(data, dict):
            return base
        tz = (data.get("timezone") or "").strip() or base["timezone"]
        legacy_cutoff = _normalize_suggestion_cutoff(data.get("suggestion_cutoff", "yesterday"))
        schedules = _normalize_schedules(data.get("schedules"), legacy_global_cutoff=legacy_cutoff)
        if not schedules:
            schedules = base["schedules"]
        return {"timezone": tz, "schedules": schedules}
    except Exception as e:
        logger.warning("读取打卡拉取配置失败: %s", e)
        return base


def get_manual_upload_default_cutoff() -> str:
    """手动上传页默认截止日：取第一条已启用任务的配置，否则前一日。"""
    for s in load_attendance_fetch_config().get("schedules", []):
        if s.get("enabled", True):
            return s.get("suggestion_cutoff", "yesterday")
    return "yesterday"


def save_attendance_fetch_config(
    schedules: List[dict],
    *,
    updated_by: Optional[str] = None,
) -> dict:
    _ensure_attendance_fetch_config_column()
    cfg = load_attendance_fetch_config()
    normalized_schedules = _normalize_schedules(schedules)
    if not normalized_schedules:
        raise ValueError("请至少保留一条有效的拉取时间")
    payload = {
        "timezone": cfg["timezone"],
        "schedules": normalized_schedules,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_by": (updated_by or "").strip() or None,
    }
    db.execute_update(
        f"UPDATE webconfig SET {ATTENDANCE_FETCH_CONFIG_COLUMN} = %s WHERE id = %s",
        (json.dumps(payload, ensure_ascii=False), "1"),
    )
    reload_attendance_fetch_scheduler()
    return get_attendance_fetch_config_for_api()


def get_attendance_fetch_config_for_api() -> dict:
    cfg = load_attendance_fetch_config()
    enabled = [s for s in cfg["schedules"] if s.get("enabled", True)]
    tz = cfg["timezone"]
    manual_cutoff = get_manual_upload_default_cutoff()
    summary_parts = [
        f"{s['hour']}:{s['minute']:02d}（{_cutoff_label(s.get('suggestion_cutoff'))}）"
        for s in enabled
    ]
    return {
        "timezone": tz,
        "schedules": cfg["schedules"],
        "enabled_schedule_count": len(enabled),
        "schedule_summary": "、".join(summary_parts) if summary_parts else "未启用",
        "manual_suggestion_cutoff": manual_cutoff,
        "manual_suggestion_cutoff_label": _cutoff_label(manual_cutoff),
        "configured_in_db": _is_configured_in_db(),
    }


def _is_configured_in_db() -> bool:
    try:
        rows = db.execute_query(
            f"SELECT {ATTENDANCE_FETCH_CONFIG_COLUMN} FROM webconfig WHERE id = %s LIMIT 1",
            ("1",),
        )
        raw = rows[0].get(ATTENDANCE_FETCH_CONFIG_COLUMN) if rows else None
        return raw is not None and str(raw).strip() != ""
    except Exception:
        return False


def resolve_suggestion_cutoff_date(
    suggestion_cutoff: Optional[str] = None,
    run_at: Optional[datetime] = None,
) -> str:
    """根据「今日/前一日」解析为 YYYY-MM-DD。"""
    mode = _normalize_suggestion_cutoff(
        suggestion_cutoff if suggestion_cutoff is not None else get_manual_upload_default_cutoff()
    )
    now = run_at or datetime.now()
    if mode == "today":
        return now.strftime("%Y-%m-%d")
    return (now - timedelta(days=1)).strftime("%Y-%m-%d")


def get_scheduler_status_message() -> str:
    fetch_url = (getattr(settings, "ATTENDANCE_REPORT_FETCH_URL", None) or "").strip()
    if not fetch_url:
        return "未配置 ATTENDANCE_REPORT_FETCH_URL"
    cfg = load_attendance_fetch_config()
    enabled = [s for s in cfg["schedules"] if s.get("enabled", True)]
    if not enabled:
        return "已配置拉取地址，但未启用任何执行时间"
    parts = [
        f"{s['hour']}:{s['minute']:02d}（建议截止{_cutoff_label(s.get('suggestion_cutoff'))}）"
        for s in enabled
    ]
    return f"每日 {'、'.join(parts)}（{cfg['timezone']}）执行"


def _attendance_fetch_url_ready() -> bool:
    return bool((getattr(settings, "ATTENDANCE_REPORT_FETCH_URL", None) or "").strip())


def init_attendance_fetch_scheduler() -> None:
    """应用启动时注册定时任务。"""
    global _scheduler
    if not _attendance_fetch_url_ready():
        return
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        cfg = load_attendance_fetch_config()
        _scheduler = AsyncIOScheduler(timezone=cfg["timezone"])
        _apply_jobs_to_scheduler(_scheduler, cfg)
        _scheduler.start()
        logger.info("打卡自动拉取任务已启动: %s", get_scheduler_status_message())
        print(f"[System] 打卡自动拉取: {get_scheduler_status_message()}")
    except Exception as e:
        logger.warning("启用打卡自动拉取任务失败: %s", e)
        print(f"[System] 警告: 打卡自动拉取任务未启用: {e}")


def reload_attendance_fetch_scheduler() -> None:
    """保存配置后热更新调度（无需重启服务）。"""
    global _scheduler
    if not _attendance_fetch_url_ready():
        return
    cfg = load_attendance_fetch_config()
    try:
        if _scheduler is None:
            init_attendance_fetch_scheduler()
            return
        for job in list(_scheduler.get_jobs()):
            if (job.id or "").startswith("fetch_attendance_report"):
                _scheduler.remove_job(job.id)
        _apply_jobs_to_scheduler(_scheduler, cfg)
        logger.info("打卡自动拉取任务已更新: %s", get_scheduler_status_message())
    except Exception as e:
        logger.warning("更新打卡自动拉取任务失败: %s", e)


def _apply_jobs_to_scheduler(scheduler, cfg: dict) -> None:
    from apscheduler.triggers.cron import CronTrigger
    from routers.attendance import run_fetch_and_upload_report

    tz = cfg["timezone"]
    enabled = [s for s in cfg.get("schedules", []) if s.get("enabled", True)]
    for idx, sched in enumerate(enabled):
        hour = int(sched["hour"])
        minute = int(sched["minute"])
        cutoff = _normalize_suggestion_cutoff(sched.get("suggestion_cutoff"))
        job_id = f"fetch_attendance_report_{idx}_{hour}_{minute}_{cutoff}"
        scheduler.add_job(
            run_fetch_and_upload_report,
            CronTrigger(hour=hour, minute=minute, timezone=tz),
            kwargs={"suggestion_cutoff": cutoff},
            id=job_id,
            replace_existing=True,
        )

    # 每月 1 日补拉上月完整报表。建议截止到前一日，即上月最后一天。
    # 07:00 首次执行，10:00 再补偿一次，以覆盖早间报表尚未生成或临时拉取失败。
    scheduler.add_job(
        run_fetch_and_upload_report,
        CronTrigger(day=1, hour="7,10", minute=0, timezone=tz),
        kwargs={"suggestion_cutoff": "yesterday", "report_month": "previous"},
        id="fetch_attendance_report_previous_month_day1",
        replace_existing=True,
    )
