# -*- coding: utf-8 -*-
"""
考勤数据管理API路由 - 新版（使用SQLite）
"""
from fastapi import APIRouter, BackgroundTasks, File, UploadFile, HTTPException, Query, Form
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, date as date_type, timedelta
import os
import tempfile
import logging
from io import BytesIO

from fastapi.responses import StreamingResponse

import uuid
from config import settings
from attendance_db import attendance_db
from database import db
from utils.excel_processor import ExcelProcessor
from routers.suggestions import get_attendance_exception_keys
from routers.approvers import _get_user_info, _jb_match
from routers.db_manager import _get_admin1

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attendance", tags=["考勤管理"])


def _attendance_report_httpx_timeout():
    """打卡服务器 GET 拉取报表：远端生成慢、本机卡顿时可能长时间无字节返回，单独放宽超时（手动「上传最新数据」与定时任务共用）。"""
    import httpx

    # 读超时 20 分钟：允许长时间挂起后仍返回；连接 3 分钟应对极慢网络/系统卡顿
    return httpx.Timeout(connect=180.0, read=1200.0, write=180.0, pool=180.0)


def _get_dakaman() -> Optional[str]:
    """从 webconfig 表读取 dakaman 字段（打卡数据上传权限用户名）。"""
    try:
        rows = db.execute_query("SELECT dakaman FROM webconfig WHERE id = %s LIMIT 1", ("1",))
        if rows and rows[0].get("dakaman") is not None:
            return (rows[0]["dakaman"] or "").strip() or None
    except Exception as e:
        logger.debug(f"读取 webconfig.dakaman 失败: {e}")
    return None




def _can_see_attendance_exceptions(current_user: str) -> tuple:
    """
    判断当前用户是否有权查看考勤异常。
    返回 (allowed: bool, lsys: str|None, is_dakaman: bool)。
    - 系统管理员(admin1)、打卡管理员(dakaman)：可看全部（dakaman 含部办人员）。
    - 班组长/主任/副主任：仅可看本室。
    - 部长/副部长/员工等：无权限。
    """
    current_user = (current_user or "").strip()
    if not current_user:
        return False, None, False
    dakaman = _get_dakaman()
    is_dk = bool(dakaman and current_user == dakaman)
    admin1 = _get_admin1()
    if admin1 and current_user == admin1:
        return True, None, True
    if is_dk:
        return True, None, True
    user = _get_user_info(current_user)
    if not user:
        return False, None, False
    jb = (user.get("jb") or "").strip()
    if _jb_match(jb, "组长") or _jb_match(jb, "主任") or _jb_match(jb, "副主任"):
        lsys = (user.get("lsys") or "").strip()
        return True, lsys if lsys else None, False
    return False, None, False


def _build_attendance_exceptions_data(year: int, month: int, filter_lsys: Optional[str], include_buban: bool = False) -> List[dict]:
    """
    构建指定年月的考勤异常列表原始数据（不做权限检查）。
    filter_lsys 不为空时，仅保留该科室(department)的数据。
    include_buban=True 时包含部办人员。
    """
    import calendar

    _, last_day = calendar.monthrange(year, month)
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day:02d}"
    exception_keys = get_attendance_exception_keys(year, month, include_buban=include_buban)
    if not exception_keys:
        return []
    if filter_lsys:
        exception_keys = [
            (n, d, dt) for n, d, dt in exception_keys
            if (d or "").strip() == filter_lsys
        ]
        if not exception_keys:
            return []
    all_records = attendance_db.get_all_records_by_date_range(start_date, end_date)
    records_by_key = {}
    for r in all_records:
        name = (r.get("employee_name") or "").strip()
        dept = (r.get("department") or "").strip()
        d = (r.get("attendance_date") or "")
        if hasattr(d, "strftime"):
            d = d.strftime("%Y-%m-%d")
        else:
            d = str(d)[:10]
        key = (name, dept, d)
        if key not in records_by_key:
            records_by_key[key] = r
    built: List[dict] = []
    for name, dept, date_str in exception_keys:
        key = (name, dept, date_str)
        if key in records_by_key:
            rec = dict(records_by_key[key])
            rec["full_day_absence"] = False
            built.append(rec)
        else:
            built.append({
                "id": None,
                "employee_id": "",
                "employee_name": name,
                "department": dept,
                "attendance_date": date_str,
                "time_1": None, "time_2": None, "time_3": None, "time_4": None,
                "time_5": None, "time_6": None, "time_7": None, "time_8": None,
                "time_9": None, "time_10": None,
                "full_day_absence": True,
            })
    built.sort(key=lambda x: (x.get("attendance_date") or "", x.get("employee_name") or ""))
    return built


# ==================== 数据模型 ====================

class AttendanceRecord(BaseModel):
    """考勤记录模型"""
    # 数据库中 id 目前为 VARCHAR(36) UUID，因此这里用 str 接收；前端不依赖该字段类型
    id: Optional[str] = None
    employee_id: str
    employee_name: str
    department: str
    attendance_date: str
    time_1: Optional[str] = None
    time_1_mark: Optional[int] = None
    time_2: Optional[str] = None
    time_2_mark: Optional[int] = None
    time_3: Optional[str] = None
    time_3_mark: Optional[int] = None
    time_4: Optional[str] = None
    time_4_mark: Optional[int] = None
    time_5: Optional[str] = None
    time_5_mark: Optional[int] = None
    time_6: Optional[str] = None
    time_6_mark: Optional[int] = None
    time_7: Optional[str] = None
    time_7_mark: Optional[int] = None
    time_8: Optional[str] = None
    time_8_mark: Optional[int] = None
    time_9: Optional[str] = None
    time_9_mark: Optional[int] = None
    time_10: Optional[str] = None
    time_10_mark: Optional[int] = None
    # 考勤异常接口专用：无打卡记录时为 True，前端显示「全天缺勤」
    full_day_absence: Optional[bool] = None


class AttendanceQueryResponse(BaseModel):
    """考勤查询响应"""
    success: bool
    message: Optional[str] = None
    total: int = 0
    data: List[AttendanceRecord] = []
    is_dakaman: bool = False


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool
    message: str
    records_count: int = 0
    success_count: int = 0
    fail_count: int = 0


# ==================== API 路由 ====================


@router.get("/upload/config")
async def get_upload_config():
    """
    获取打卡/人事相关配置。返回 dakaman（打卡管理员）、admin2（人事管理员），前端用于权限展示。
    """
    dakaman = _get_dakaman()
    admin2 = ""
    try:
        wc = db.execute_query("SELECT admin2 FROM webconfig WHERE id = 1 LIMIT 1")
        if wc and wc[0].get("admin2") is not None:
            admin2 = (wc[0]["admin2"] or "").strip() or ""
    except Exception:
        pass
    fetch_url = (getattr(settings, "ATTENDANCE_REPORT_FETCH_URL", None) or "").strip()
    admin1 = _get_admin1()
    personnel_archive_url = (getattr(settings, "PERSONNEL_ARCHIVE_URL", None) or "").strip()
    return {
        "success": True,
        "dakaman": dakaman or "",
        "admin2": admin2,
        "admin1": admin1 or "",
        "fetchReportUrl": fetch_url,
        "personnelArchiveUrl": personnel_archive_url,
    }


def _yggl_employees_for_suggestions() -> List[tuple]:
    """在职、有姓名与隶属科室的员工，与打卡入库时 department=lsys 一致。"""
    try:
        rows = db.execute_query(
            """
            SELECT TRIM(name) AS name, TRIM(lsys) AS lsys FROM yggl
            WHERE name IS NOT NULL AND TRIM(name) != ''
              AND lsys IS NOT NULL AND TRIM(lsys) != ''
              AND (COALESCE(zaizhi, 0) = 0)
            """
        )
    except Exception as e:
        logger.warning(f"[后台] 查询 yggl 员工列表失败: {e}")
        return []
    out = []
    for r in rows or []:
        n = (r.get("name") or "").strip()
        d = (r.get("lsys") or "").strip()
        if n and d:
            out.append((n, d))
    return out


def _generate_suggestions_bg(records: list, cutoff_date_str: str = None):
    """后台任务：上传打卡后，按涉及月份为全员（yggl 在职）重算智能建议，不阻塞上传响应。
    当月库中无打卡记录的人也会生成建议（如工作日全天缺勤），避免仅处理「本次文件里出现过的员工」。
    cutoff_date_str: 'YYYY-MM-DD'，当月仅生成截止到此日期的建议。
    优化：按月份批量查询考勤记录（1条SQL/月），缓存假期数据，批量写入建议。"""
    import time as _time
    from collections import defaultdict
    t0 = _time.time()
    try:
        from routers.suggestions import (generate_suggestions_for_month_with_records,
                                         load_holidays, _parse_record_date)
        attendance_db.ensure_suggestions_table()

        seen = set()
        for rec in records:
            name = (rec.get("employee_name") or "").strip()
            dept = (rec.get("department") or "").strip()
            ad = rec.get("attendance_date")
            if not name or not dept or not ad:
                continue
            y, m = None, None
            if isinstance(ad, datetime):
                y, m = ad.year, ad.month
            elif isinstance(ad, date_type):
                y, m = ad.year, ad.month
            elif isinstance(ad, str):
                parts = ad.replace("/", "-").split("-")
                if len(parts) >= 2:
                    try:
                        y, m = int(parts[0]), int(parts[1])
                    except (ValueError, IndexError):
                        continue
                else:
                    continue
            else:
                continue
            seen.add((name, dept, y, m))

        if not seen:
            return

        months = set()
        for (_, _, y, m) in seen:
            months.add((y, m))

        employees = _yggl_employees_for_suggestions()
        keys_to_process = set()
        for y, m in months:
            for name, dept in employees:
                keys_to_process.add((name, dept, y, m))

        if not keys_to_process:
            return

        # 避免单次 SQL 过长，分批删除旧建议
        key_list = list(keys_to_process)
        _chunk = 400
        for i in range(0, len(key_list), _chunk):
            attendance_db.delete_suggestions_batch(key_list[i : i + _chunk])

        holidays_cache: dict = {}
        month_records: dict = {}
        for (y, m) in months:
            start_date = f"{y}-{m:02d}-01"
            if m == 12:
                end_date = f"{y}-12-31"
            else:
                last = (date_type(y, m + 1, 1) - timedelta(days=1))
                end_date = last.strftime("%Y-%m-%d")
            all_recs = attendance_db.get_all_records_by_date_range(start_date, end_date)
            grouped = defaultdict(list)
            for r in all_recs:
                key = ((r.get("employee_name") or "").strip(),
                       (r.get("department") or "").strip())
                grouped[key].append(r)
            month_records[(y, m)] = grouped

            year_str = str(y)
            if year_str not in holidays_cache:
                holidays_cache[year_str] = load_holidays(year_str)

        for (name, dept, y, m) in keys_to_process:
            try:
                person_records = month_records.get((y, m), {}).get((name, dept), [])
                holidays = holidays_cache[str(y)]
                suggestions_list = generate_suggestions_for_month_with_records(
                    name, dept, y, m, person_records, holidays,
                    cutoff_date_str=cutoff_date_str)
                attendance_db.insert_suggestions(name, dept, y, m, suggestions_list)
            except Exception as e:
                logger.warning(f"[后台] 生成智能建议失败 {(name, dept, y, m)}: {e}")

        elapsed = round(_time.time() - t0, 1)
        logger.info(f"[后台] 智能建议生成完成，共处理 {len(keys_to_process)} 个人月组合，耗时 {elapsed}s")
    except Exception as e:
        logger.warning(f"[后台] 上传后生成智能建议失败: {e}")


def _process_attendance_file_path(temp_file_path: str, filename: str):
    """
    处理考勤文件（Excel），返回 (success, message, records_count, success_count, fail_count, mapped_records)。
    不负责 log_upload、background_tasks、临时文件删除。
    """
    processor = ExcelProcessor(temp_file_path)
    success, merged_records, error_msg = processor.process_file(start_row=6)
    if not success:
        return False, error_msg, 0, 0, 0, []

    mapped_records = []
    skipped_gh = []
    for rec in merged_records:
        gh = (rec.get("employee_id") or "").strip()
        emp = attendance_db.get_employee_by_gh(gh) if gh else None
        if not emp:
            skipped_gh.append(gh or "(空)")
            continue
        rec["employee_name"] = emp.get("name") or ""
        rec["department"] = emp.get("lsys") or ""
        mapped_records.append(rec)
    if skipped_gh:
        unique_gh = sorted(set(skipped_gh))
        logger.warning(
            f"上传跳过未在 yggl 中匹配到的工号，共 {len(skipped_gh)} 条记录涉及 {len(unique_gh)} 个工号。"
            f"未匹配工号完整列表: {unique_gh}"
        )

    success_count, fail_count = attendance_db.batch_insert_records(mapped_records)
    parts = [f"文件处理完成！Excel 合并后 {len(merged_records)} 人天"]
    if skipped_gh:
        parts.append(f"跳过未匹配工号 {len(skipped_gh)} 条（涉及 {len(set(skipped_gh))} 个工号: {', '.join(sorted(set(skipped_gh))[:20])}）")
    parts.append(f"入库成功 {success_count} 条")
    if fail_count:
        parts.append(f"入库失败 {fail_count} 条（详见服务器日志）")
    msg = "，".join(parts)
    return True, msg, len(mapped_records), success_count, fail_count, mapped_records


@router.post("/upload", response_model=UploadResponse)
async def upload_excel(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    uploader: Optional[str] = Form(None),
    attendance_data_date: Optional[str] = Form(None),
):
    """
    上传并处理考勤Excel文件。仅 webconfig 表中 dakaman 对应用户可上传。
    
    文件格式要求：
    - Excel格式（.xls 或 .xlsx）
    - 从第6行开始读取数据
    - 列结构：A~F 员工编号、姓名、部门1、部门2、考勤日期、考勤时间；H 列为进出标记（可选）
    
    处理逻辑：
    - 自动按员工编号和日期合并打卡记录
    - 同一人同一天的多次打卡会合并为一行
    - H 列含「进/入」记为进、含「出」记为出；无关键字则按当日时间顺序与前一条交替（首条视为进）
    """
    dakaman = _get_dakaman()
    admin1 = _get_admin1()
    uploader_name = (uploader or "").strip()
    if not (admin1 and uploader_name == admin1) and not (dakaman and uploader_name == dakaman):
        raise HTTPException(
            status_code=403,
            detail="仅打卡管理员（webconfig.dakaman）或系统管理员（webconfig.admin1）可上传打卡数据"
        )

    cutoff = (attendance_data_date or "").strip() or None

    # 验证文件类型
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="只支持 .xls 或 .xlsx 格式的Excel文件")
    
    # 创建临时文件保存上传的内容
    temp_file = None
    try:
        # 保存上传文件到临时目录
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"开始处理文件: {file.filename}")
        success, message, records_count, success_count, fail_count, mapped_records = _process_attendance_file_path(temp_file_path, file.filename)
        if not success:
            attendance_db.log_upload(file.filename, 0, "失败", message)
            return UploadResponse(success=False, message=message, records_count=0)
        attendance_db.log_upload(file.filename, records_count, "成功", f"成功: {success_count}, 失败: {fail_count}")
        background_tasks.add_task(_generate_suggestions_bg, list(mapped_records), cutoff)
        return UploadResponse(success=True, message=message, records_count=records_count, success_count=success_count, fail_count=fail_count)
    
    except Exception as e:
        error_msg = f"处理失败: {str(e)}"
        logger.error(error_msg)
        attendance_db.log_upload(file.filename, 0, "异常", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass


@router.post("/fetch-and-upload", response_model=UploadResponse)
async def fetch_and_upload(
    background_tasks: BackgroundTasks,
    uploader: Optional[str] = Form(None),
    attendance_data_date: Optional[str] = Form(None),
):
    """
    从打卡服务器 GET 拉取最新报表并导入。仅 dakaman 可操作。
    需在 config 或 .env 中配置 ATTENDANCE_REPORT_FETCH_URL；远端响应可能很慢，服务端 HTTP 读超时约 20 分钟。
    """
    dakaman = _get_dakaman()
    admin1 = _get_admin1()
    uploader_name = (uploader or "").strip()
    if not (admin1 and uploader_name == admin1) and not (dakaman and uploader_name == dakaman):
        raise HTTPException(status_code=403, detail="仅打卡管理员或系统管理员可执行拉取上传")
    cutoff = (attendance_data_date or "").strip() or None
    fetch_url = (getattr(settings, "ATTENDANCE_REPORT_FETCH_URL", None) or "").strip()
    if not fetch_url:
        raise HTTPException(status_code=400, detail="未配置打卡报表拉取地址（ATTENDANCE_REPORT_FETCH_URL）")

    import httpx
    temp_file_path = None
    try:
        logger.info("开始从打卡服务器拉取最新报表: %s", fetch_url[:80] + "..." if len(fetch_url) > 80 else fetch_url)
        async with httpx.AsyncClient(timeout=_attendance_report_httpx_timeout()) as client:
            resp = await client.get(fetch_url)
            resp.raise_for_status()
            content = resp.content
        if not content:
            raise HTTPException(status_code=502, detail="拉取返回为空")
        # 根据 Content-Disposition 或默认使用 .xlsx
        suffix = ".xlsx"
        cd = (resp.headers.get("content-disposition") or "").strip()
        if "filename=" in cd:
            import re
            m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';]+)["\']?', cd, re.I) or re.search(r'filename=([^;\s]+)', cd, re.I)
            if m:
                fn = m.group(1).strip().lower()
                if fn.endswith(".xls") and not fn.endswith(".xlsx"):
                    suffix = ".xls"
                elif fn.endswith(".xlsx"):
                    suffix = ".xlsx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            temp_file_path = tmp.name
        filename = "report" + suffix
        success, message, records_count, success_count, fail_count, mapped_records = _process_attendance_file_path(temp_file_path, filename)
        if not success:
            attendance_db.log_upload(filename, 0, "失败", message)
            return UploadResponse(success=False, message=message, records_count=0)
        attendance_db.log_upload(filename, records_count, "成功", f"成功: {success_count}, 失败: {fail_count}")
        background_tasks.add_task(_generate_suggestions_bg, list(mapped_records), cutoff)
        return UploadResponse(success=True, message=message, records_count=records_count, success_count=success_count, fail_count=fail_count)
    except httpx.HTTPStatusError as e:
        attendance_db.log_upload("report", 0, "失败", str(e.response.status_code))
        raise HTTPException(status_code=502, detail=f"拉取失败: {e.response.status_code}")
    except httpx.RequestError as e:
        attendance_db.log_upload("report", 0, "失败", str(e))
        raise HTTPException(status_code=502, detail=f"拉取请求失败: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass


async def run_fetch_and_upload_report():
    """供定时任务调用（执行时刻见 SCHEDULER_HOUR/MINUTE）：拉取报表并导入，智能建议截止日为「运行当日」。
    建议在当日 24 点前运行，以处理当天打卡数据。失败时最多重试 3 次。"""
    import asyncio
    import httpx
    fetch_url = (getattr(settings, "ATTENDANCE_REPORT_FETCH_URL", None) or "").strip()
    if not fetch_url:
        logger.warning("[定时] 拉取跳过: 未配置 ATTENDANCE_REPORT_FETCH_URL")
        return
    dakaman = _get_dakaman()
    admin1 = _get_admin1()
    if not dakaman and not admin1:
        logger.warning("[定时] 拉取跳过: webconfig 中未配置 dakaman 或 admin1，无法执行定时任务")
        return
    max_attempts = 4  # 1 次首次 + 最多重试 3 次
    retry_delay_seconds = 30  # 每次失败后间隔 30 秒再重试
    last_error = None
    for attempt in range(1, max_attempts + 1):
        temp_file_path = None
        try:
            logger.info("[定时] 拉取打卡报表 第 %d/%d 次: %s", attempt, max_attempts, fetch_url[:80] + "..." if len(fetch_url) > 80 else fetch_url)
            async with httpx.AsyncClient(timeout=_attendance_report_httpx_timeout()) as client:
                resp = await client.get(fetch_url)
                resp.raise_for_status()
                content = resp.content
            if not content:
                last_error = "拉取返回为空"
                logger.warning("[定时] 第 %d 次: %s", attempt, last_error)
                if attempt < max_attempts:
                    await asyncio.sleep(retry_delay_seconds)
                continue
            suffix = ".xlsx"
            cd = (resp.headers.get("content-disposition") or "").strip()
            if "filename=" in cd:
                import re
                m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';]+)["\']?', cd, re.I) or re.search(r'filename=([^;\s]+)', cd, re.I)
                if m:
                    fn = m.group(1).strip().lower()
                    if fn.endswith(".xls") and not fn.endswith(".xlsx"):
                        suffix = ".xls"
                    elif fn.endswith(".xlsx"):
                        suffix = ".xlsx"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(content)
                temp_file_path = tmp.name
            report_name = "report" + suffix
            success, message, records_count, success_count, fail_count, mapped_records = _process_attendance_file_path(temp_file_path, report_name)
            if not success:
                last_error = message
                attendance_db.log_upload(report_name, 0, "失败", message)
                logger.warning("[定时] 第 %d 次 处理失败: %s", attempt, message)
                if attempt < max_attempts:
                    await asyncio.sleep(retry_delay_seconds)
                continue
            attendance_db.log_upload(report_name, records_count, "成功", f"成功: {success_count}, 失败: {fail_count}")
            today_str = datetime.now().strftime("%Y-%m-%d")
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, lambda: _generate_suggestions_bg(list(mapped_records), today_str))
            logger.info("[定时] 拉取上传完成（第 %d 次）: %s", attempt, message)
            return
        except Exception as e:
            last_error = str(e)
            logger.exception("[定时] 第 %d 次 拉取上传异常: %s", attempt, e)
            attendance_db.log_upload("report", 0, "异常", f"第{attempt}次: {last_error}")
            if attempt < max_attempts:
                await asyncio.sleep(retry_delay_seconds)
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass
    logger.error("[定时] 拉取打卡报表已重试 %d 次均失败，最后错误: %s", max_attempts, last_error)


@router.get("/exceptions", response_model=AttendanceQueryResponse)
async def get_attendance_exceptions(
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份 1-12"),
    current_user: Optional[str] = Query(None, description="当前登录用户姓名，用于权限校验"),
):
    """
    考勤异常列表。权限：打卡管理员可看全部（含部办）；各科室班组长/主任/副主任仅可看本室。
    返回指定年月内「智能建议需请假/缺勤且未完成请假或公出」的异常日对应的打卡记录。
    """
    allowed, filter_lsys, is_dakaman = _can_see_attendance_exceptions(current_user or "")
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="仅班组长/主任/副主任或打卡管理员可查看考勤异常",
        )
    try:
        built = _build_attendance_exceptions_data(year, month, filter_lsys, include_buban=is_dakaman)
        if not built:
            msg = "本室无考勤异常" if filter_lsys else "无考勤异常"
            return AttendanceQueryResponse(success=True, message=msg, total=0, data=[], is_dakaman=is_dakaman)
        attendance_records = [AttendanceRecord(**rec) for rec in built]
        return AttendanceQueryResponse(
            success=True,
            message="查询成功",
            total=len(attendance_records),
            data=attendance_records,
            is_dakaman=is_dakaman,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"考勤异常查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/exceptions/export")
async def export_attendance_exceptions(
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份 1-12"),
    current_user: str = Query(..., description="当前登录用户姓名，用于权限校验"),
):
    """
    导出指定月份的考勤异常列表为 Excel。
    权限同 /attendance/exceptions。
    """
    allowed, filter_lsys, is_dakaman = _can_see_attendance_exceptions(current_user or "")
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="仅班组长/主任/副主任或打卡管理员可导出考勤异常",
        )
    try:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment
        except ImportError:
            raise HTTPException(status_code=500, detail="服务端未安装 openpyxl，无法生成 Excel")

        rows = _build_attendance_exceptions_data(year, month, filter_lsys, include_buban=is_dakaman)
        wb = Workbook()
        ws = wb.active
        ws.title = "考勤异常"

        headers = [
            "日期", "姓名", "所在单位",
            "考勤时间1", "考勤时间2", "考勤时间3", "考勤时间4",
            "考勤时间5", "考勤时间6", "考勤时间7", "考勤时间8",
            "是否全天缺勤",
        ]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

        for r in rows:
            date_str = r.get("attendance_date") or ""
            name = (r.get("employee_name") or "").strip()
            dept = (r.get("department") or "").strip()
            t1 = r.get("time_1") or ""
            t2 = r.get("time_2") or ""
            t3 = r.get("time_3") or ""
            t4 = r.get("time_4") or ""
            t5 = r.get("time_5") or ""
            t6 = r.get("time_6") or ""
            t7 = r.get("time_7") or ""
            t8 = r.get("time_8") or ""
            is_full = bool(r.get("full_day_absence")) or all(
                not (v or "").strip() for v in [t1, t2, t3, t4, t5, t6, t7, t8]
            )
            ws.append([
                date_str,
                name,
                dept,
                t1, t2, t3, t4, t5, t6, t7, t8,
                "是" if is_full else "",
            ])

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        filename_ascii = f"attendance_exceptions_{year}{month:02d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename_ascii}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出考勤异常失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


def _parse_datetime_for_excel(val) -> Optional[datetime]:
    """将 DB 返回的 timefrom/timeto 转为 datetime，用于 Excel 的 DATE TIME 列。"""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip()
    if not s:
        return None
    if "." in s:
        s = s.split(".")[0]
    s = s[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


@router.get("/leave-handler-export")
async def export_leave_handler_table(
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份 1-12"),
    current_user: str = Query(..., description="当前登录用户姓名，用于权限校验"),
):
    """
    导出异常处理表：按月全员请假信息 + 公出信息，XLS（Excel）格式。
    列顺序：A 员工代码(string) B 姓名(string) C 部门(string，固定「智能制造工艺部」)
    D 请假/公出开始时间(DATE TIME) E 实际请假/公出结束时间(DATE TIME) F 请假类别(string，公出记为「公出」)。
    数据来源：qj 表（已通过 qjzt=4）+ gcsqb 表（已通过 bldzt=2,szrzt=2，时间用 yjcfsj/yjfhsj）；员工代码来自 yggl.gh。
    """
    import calendar
    allowed, _, _ = _can_see_attendance_exceptions(current_user or "")
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="仅班组长/主任/副主任或打卡管理员可导出异常处理表",
        )
    try:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment
        except ImportError:
            raise HTTPException(status_code=500, detail="服务端未安装 openpyxl，无法生成 Excel")

        month_str = f"{year}-{month:02d}"
        _, last_day = calendar.monthrange(year, month)
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"

        # 全员请假：qj 已通过，按月份筛选；员工代码取 yggl.gh
        sql = """
            SELECT qj.xm AS xm, qj.timefrom AS timefrom, qj.timeto AS timeto, qj.qjfs AS qjfs,
                   TRIM(yggl.gh) AS gh
            FROM qj
            LEFT JOIN yggl ON qj.xm = yggl.name
            WHERE qj.qjzt = 4
              AND (qj.timefrom LIKE %s OR SUBSTRING(qj.timefrom, 1, 7) = %s)
            ORDER BY qj.timefrom ASC
        """
        rows = db.execute_query(sql, (f"{month_str}%", month_str)) or []

        # 公出：gcsqb 已通过，当月 yjcfsj 或 yjfhsj 落在该月即纳入；时间用 yjcfsj、yjfhsj
        try:
            gcsqb_sql = """
                SELECT g.gcr AS xm, g.yjcfsj AS timefrom, g.yjfhsj AS timeto, g.gclx AS gclx, TRIM(y.gh) AS gh
                FROM gcsqb g
                LEFT JOIN yggl y ON g.gcr = y.name
                WHERE g.bldzt = 2 AND g.szrzt = 2
                  AND (g.yjcfsj IS NOT NULL OR g.yjfhsj IS NOT NULL)
                  AND (
                    (g.yjcfsj IS NOT NULL AND DATE(g.yjcfsj) >= %s AND DATE(g.yjcfsj) <= %s)
                    OR (g.yjfhsj IS NOT NULL AND DATE(g.yjfhsj) >= %s AND DATE(g.yjfhsj) <= %s)
                  )
                ORDER BY g.yjcfsj ASC
            """
            gcsqb_rows = db.execute_query(gcsqb_sql, (start_date, end_date, start_date, end_date)) or []
            for r in gcsqb_rows:
                gclx = (r.get("gclx") or "").strip()
                if not gclx:
                    gclx = "公出"
                rows.append({
                    "gh": (r.get("gh") or "").strip(),
                    "xm": (r.get("xm") or "").strip(),
                    "timefrom": r.get("timefrom"),
                    "timeto": r.get("timeto"),
                    "qjfs": gclx,
                })
        except Exception as e:
            logger.warning("导出异常处理表时查询公出失败（可能无 gcsqb/yjcfsj 列）: %s", e)

        # 按开始时间、姓名排序，便于与请假一起统一输出
        rows.sort(key=lambda x: (_parse_datetime_for_excel(x.get("timefrom")) or datetime.min, (x.get("xm") or "")))

        # 3 月导出时，若 3 月 8 日为工作日（非周六日且非系统节假日），为全体女性增加半天请假（13:00-17:00，请假类别「三八节」）
        if month == 3:
            march8 = datetime(year, 3, 8)
            weekday = march8.weekday()  # 0=周一, 5=周六, 6=周日
            is_weekend = weekday >= 5
            is_holiday = False
            try:
                from utils.holiday_loader import load_holidays_dict
                holidays = load_holidays_dict(str(year))
                march8_str = march8.strftime("%Y-%m-%d")
                if march8_str in holidays:
                    t = (holidays[march8_str] or "").strip()
                    if "假" in t or "休" in t:
                        is_holiday = True
            except Exception:
                pass
            if not is_weekend and not is_holiday:
                female_rows = db.execute_query(
                    "SELECT TRIM(gh) AS gh, name AS xm FROM yggl "
                    "WHERE (xbie LIKE %s OR xbie = %s) AND name IS NOT NULL AND TRIM(name) != '' "
                    "AND RIGHT(TRIM(name), 1) != '1' AND (lsys IS NULL OR RIGHT(TRIM(lsys), 1) != '1') "
                    "AND (TRIM(lsys) != %s OR lsys IS NULL) AND (COALESCE(zaizhi, 0) = 0)",
                    ("%女%", "女", "部办"),
                ) or []
                march8_start = datetime(year, 3, 8, 13, 0, 0)
                march8_end = datetime(year, 3, 8, 17, 0, 0)
                for r in female_rows:
                    rows.append({
                        "gh": (r.get("gh") or "").strip(),
                        "xm": (r.get("xm") or "").strip(),
                        "timefrom": march8_start,
                        "timeto": march8_end,
                        "qjfs": "三八节",
                    })
                rows.sort(key=lambda x: (_parse_datetime_for_excel(x.get("timefrom")) or datetime.min, (x.get("xm") or "")))

        wb = Workbook()
        ws = wb.active
        ws.title = "异常处理表"

        headers = ["员工代码", "姓名", "部门", "请假开始时间", "实际请假结束时间", "请假类别"]
        ws.append(headers)
        for col, _ in enumerate(headers, 1):
            c = ws.cell(row=1, column=col)
            c.font = Font(bold=True)
            c.alignment = Alignment(horizontal="center")

        dept_fixed = "智能制造工艺部"
        for r in rows:
            gh = (r.get("gh") or "").strip()
            xm = (r.get("xm") or "").strip()
            timefrom_val = r.get("timefrom")
            timeto_val = r.get("timeto")
            qjfs = (r.get("qjfs") or "").strip()

            dt_start = _parse_datetime_for_excel(timefrom_val)
            dt_end = _parse_datetime_for_excel(timeto_val)

            row_data = [
                gh,
                xm,
                dept_fixed,
                dt_start if dt_start is not None else (timefrom_val if timefrom_val is not None else ""),
                dt_end if dt_end is not None else (timeto_val if timeto_val is not None else ""),
                qjfs,
            ]
            ws.append(row_data)

        # 设置 D、E 列为日期时间格式（对已写入的 datetime 对象生效）
        for row_idx in range(2, ws.max_row + 1):
            for col_letter in ("D", "E"):
                cell = ws[f"{col_letter}{row_idx}"]
                if isinstance(cell.value, datetime):
                    cell.number_format = "yyyy-mm-dd hh:mm:ss"

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        filename_ascii = f"leave_handler_{year}{month:02d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename_ascii}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出异常处理表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.get("/query", response_model=AttendanceQueryResponse)
async def query_attendance(
    name: Optional[str] = Query(None, description="员工姓名"),
    dept: Optional[str] = Query(None, description="部门"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """
    查询考勤记录
    
    参数：
    - name: 员工姓名（可选）
    - dept: 部门（可选）
    - start_date: 开始日期（可选）
    - end_date: 结束日期（可选）
    
    如果不提供日期范围，则查询所有记录
    """
    
    try:
        records = []
        
        if start_date and end_date:
            # 按日期范围查询
            records = attendance_db.query_by_date_range(start_date, end_date, name, dept)
        elif name and dept:
            # 按姓名和部门查询
            records = attendance_db.query_by_name_and_dept(name, dept)
        else:
            return AttendanceQueryResponse(
                success=False,
                message="请提供查询条件：(name + dept) 或 (start_date + end_date)",
                total=0
            )
        
        # 转换为响应模型
        attendance_records = [AttendanceRecord(**record) for record in records]
        
        return AttendanceQueryResponse(
            success=True,
            message="查询成功",
            total=len(attendance_records),
            data=attendance_records
        )
    
    except Exception as e:
        logger.error(f"查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/dates", response_model=dict)
async def get_attendance_dates(
    name: str = Query(..., description="员工姓名"),
    dept: str = Query(..., description="部门")
):
    """
    获取某个员工的所有打卡日期
    
    用于前端判断哪些日期有打卡记录
    """
    
    try:
        dates = attendance_db.get_all_attendance_dates(name, dept)
        
        return {
            "success": True,
            "name": name,
            "dept": dept,
            "dates": dates,
            "total": len(dates)
        }
    
    except Exception as e:
        logger.error(f"查询日期失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.delete("/clear")
async def clear_all_data(confirm: str = Query(..., description="确认码，输入'CONFIRM'以确认删除")):
    """
    清空所有考勤数据（危险操作）
    
    需要确认码：CONFIRM
    """
    
    if confirm != "CONFIRM":
        raise HTTPException(status_code=400, detail="确认码不正确")
    
    try:
        conn = attendance_db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM attendance_records")
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.warning(f"已清空所有考勤数据，共删除 {deleted_count} 条记录")
        
        return {
            "success": True,
            "message": f"已清空所有数据，共删除 {deleted_count} 条记录"
        }
    
    except Exception as e:
        logger.error(f"清空数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


# ==================== 打卡管理员代处理考勤异常 ====================

class DakamanProcessRequest(BaseModel):
    current_user: str
    employee_name: str
    department: str
    attendance_date: str  # YYYY-MM-DD
    process_type: str  # leave | business_trip
    leave_type: str = "事假"  # qjfs: 换休/带薪年休假/事假/病假 etc.
    reason: str = "打卡管理员代处理"


@router.post("/dakaman-process")
async def dakaman_process_exception(req: DakamanProcessRequest):
    """
    打卡管理员(dakaman)代替员工处理考勤异常。
    根据 attendance_suggestions 中该员工当日 status=1 的建议时间段，
    自动创建已审批通过的请假/公出记录。
    """
    current_user = (req.current_user or "").strip()
    dakaman = _get_dakaman()
    admin1 = _get_admin1()
    is_allowed = (dakaman and current_user == dakaman) or (admin1 and current_user == admin1)
    if not is_allowed:
        raise HTTPException(status_code=403, detail="仅打卡管理员或系统管理员可执行此操作")

    emp_name = (req.employee_name or "").strip()
    dept = (req.department or "").strip()
    att_date = (req.attendance_date or "").strip()
    if not emp_name or not dept or not att_date:
        raise HTTPException(status_code=400, detail="参数不完整")

    try:
        date_parts = att_date.split("-")
        year = int(date_parts[0])
        month = int(date_parts[1])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="日期格式错误")

    suggestions = attendance_db.get_suggestions(emp_name, dept, year, month)
    day_suggestions = [
        s for s in suggestions
        if str(s.get("date", ""))[:10] == att_date and s.get("status") == 1
    ]
    if not day_suggestions:
        raise HTTPException(status_code=404, detail="该员工当日无需处理的缺勤异常")

    emp_info = _get_user_info(emp_name)
    lsys = (emp_info.get("lsys") or dept) if emp_info else dept
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    created_ids = []

    for s in day_suggestions:
        start_time = s.get("start_time")
        end_time = s.get("end_time")
        if not start_time or not end_time:
            continue
        st_str = str(start_time)[:19].replace("T", " ")
        et_str = str(end_time)[:19].replace("T", " ")
        if len(st_str) == 10:
            st_str += " 00:00:00"
        if len(et_str) == 10:
            et_str += " 23:59:59"

        new_id = uuid.uuid4().hex

        if req.process_type == "leave":
            from utils.helpers import normalize_datetime_for_db
            st_norm = normalize_datetime_for_db(st_str)
            et_norm = normalize_datetime_for_db(et_str)

            try:
                st_dt = datetime.strptime(st_norm[:19], "%Y-%m-%d %H:%M:%S")
                et_dt = datetime.strptime(et_norm[:19], "%Y-%m-%d %H:%M:%S")
                diff_hours = (et_dt - st_dt).total_seconds() / 3600
                dur_days = round(diff_hours / 8, 2) if diff_hours > 0 else 0.5
            except Exception:
                dur_days = 0.5
            xiaoshi = str(round(dur_days * 8, 2))

            sql = """
                INSERT INTO qj (id, bz, xm, qjfs, bc, gx, jy, smcl, smclwj, timefrom, timeto, timefromdate,
                    tian, xiaoshi, qjtime, qjzt, spr, `2j`, spr2, content, lsys, hxpxh, hxwc, hxps)
                VALUES (%s, %s, %s, %s, '白班', '', %s, '打卡管理员代处理', '', %s, %s, %s,
                    %s, %s, %s, 4, %s, 0, '', %s, %s, 0, 0, 0)
            """
            params = (
                new_id, dept, emp_name, req.leave_type,
                req.reason or "打卡管理员代处理",
                st_norm, et_norm, st_norm[:10],
                str(dur_days), xiaoshi, now,
                current_user, req.reason or "打卡管理员代处理", lsys,
            )
            db.execute_insert(sql, params)
            created_ids.append(new_id)

        elif req.process_type == "business_trip":
            sql = """
                INSERT INTO gcsqb (id, gclx, wpdw, gcr, gzh, gcdw, lxdh, wpsj,
                    yjfhsj, yjcfsj, xmmc, tzdbh, bcgczrs, gcdd, qkje, gcrw,
                    szr, bld, gcsj, sjfhtime, bldzt, szrzt, sqsj, lsysjm)
                VALUES (%s, '境内公出', '', %s, '', %s, '', %s,
                    %s, %s, '', '', '1', '', 0, %s,
                    %s, %s, %s, %s, 2, 2, %s, %s)
            """
            params = (
                new_id, emp_name, dept, now,
                et_str, st_str,
                req.reason or "打卡管理员代处理",
                current_user, current_user, st_str, et_str, now, lsys,
            )
            db.execute_insert(sql, params)
            created_ids.append(new_id)
        else:
            raise HTTPException(status_code=400, detail="process_type 必须为 leave 或 business_trip")

    return {
        "success": True,
        "message": f"已处理 {len(created_ids)} 条异常记录",
        "ids": created_ids,
    }


