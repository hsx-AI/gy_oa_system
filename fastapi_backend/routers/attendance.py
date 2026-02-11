# -*- coding: utf-8 -*-
"""
考勤数据管理API路由 - 新版（使用SQLite）
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Form
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, date as date_type
import os
import tempfile
import logging
from io import BytesIO

from fastapi.responses import StreamingResponse

from attendance_db import attendance_db
from database import db
from utils.excel_processor import ExcelProcessor
from routers.suggestions import get_attendance_exception_keys
from routers.approvers import _get_user_info, _jb_match
from routers.approvers import _get_user_info, _jb_match

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attendance", tags=["考勤管理"])


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
    返回 (allowed: bool, lsys: str|None)。
    - 打卡管理员(dakaman)：可看全部，lsys 为 None 表示不按科室过滤。
    - 班组长/主任/副主任：仅可看本室，返回其 lsys 用于过滤。
    - 部长/副部长/员工等：无权限。
    """
    current_user = (current_user or "").strip()
    if not current_user:
        return False, None
    dakaman = _get_dakaman()
    if dakaman and current_user == dakaman:
        return True, None
    user = _get_user_info(current_user)
    if not user:
        return False, None
    jb = (user.get("jb") or "").strip()
    if _jb_match(jb, "组长") or _jb_match(jb, "主任") or _jb_match(jb, "副主任"):
        lsys = (user.get("lsys") or "").strip()
        return True, lsys if lsys else None
    return False, None


def _build_attendance_exceptions_data(year: int, month: int, filter_lsys: Optional[str]) -> List[dict]:
    """
    构建指定年月的考勤异常列表原始数据（不做权限检查）。
    filter_lsys 不为空时，仅保留该科室(department)的数据。
    """
    import calendar

    _, last_day = calendar.monthrange(year, month)
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day:02d}"
    exception_keys = get_attendance_exception_keys(year, month)
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
    time_2: Optional[str] = None
    time_3: Optional[str] = None
    time_4: Optional[str] = None
    time_5: Optional[str] = None
    time_6: Optional[str] = None
    time_7: Optional[str] = None
    time_8: Optional[str] = None
    time_9: Optional[str] = None
    time_10: Optional[str] = None
    # 考勤异常接口专用：无打卡记录时为 True，前端显示「全天缺勤」
    full_day_absence: Optional[bool] = None


class AttendanceQueryResponse(BaseModel):
    """考勤查询响应"""
    success: bool
    message: Optional[str] = None
    total: int = 0
    data: List[AttendanceRecord] = []


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
    return {"success": True, "dakaman": dakaman or "", "admin2": admin2}


@router.post("/upload", response_model=UploadResponse)
async def upload_excel(
    file: UploadFile = File(...),
    uploader: Optional[str] = Form(None)
):
    """
    上传并处理考勤Excel文件。仅 webconfig 表中 dakaman 对应用户可上传。
    
    文件格式要求：
    - Excel格式（.xls 或 .xlsx）
    - 从第6行（A6:F6）开始读取数据
    - 列结构：员工编号、姓名、部门1、部门2、考勤日期、考勤时间
    
    处理逻辑：
    - 自动按员工编号和日期合并打卡记录
    - 同一人同一天的多次打卡会合并为一行
    """
    dakaman = _get_dakaman()
    if dakaman:
        uploader_name = (uploader or "").strip()
        if uploader_name != dakaman:
            raise HTTPException(
                status_code=403,
                detail="仅打卡管理员（webconfig.dakaman）可上传打卡数据"
            )

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
        
        # 处理Excel文件
        processor = ExcelProcessor(temp_file_path)
        success, merged_records, error_msg = processor.process_file(start_row=6)
        
        if not success:
            attendance_db.log_upload(file.filename, 0, "失败", error_msg)
            return UploadResponse(
                success=False,
                message=error_msg,
                records_count=0
            )

        # 用工号(gh)映射 yggl：employee_name 用 yggl.name，department 用 yggl.lsys；未匹配工号的记录不录入
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
            logger.warning(f"上传跳过未在 yggl 中匹配到工号的记录，工号示例: {skipped_gh[:10]}{'...' if len(skipped_gh) > 10 else ''}")

        # 批量插入数据库
        success_count, fail_count = attendance_db.batch_insert_records(mapped_records)
        
        # 记录上传日志
        attendance_db.log_upload(
            file.filename,
            len(mapped_records),
            "成功",
            f"成功: {success_count}, 失败: {fail_count}"
        )

        # 为本次上传涉及到的每人每月生成智能建议并写入表（选月时只读表，不再实时计算）
        # 先批量删除本批涉及的 (name, dept, year, month)，再生成并插入，避免重复上传导致建议重复
        try:
            from routers.suggestions import generate_suggestions_for_month
            attendance_db.ensure_suggestions_table()
            seen = set()
            for rec in mapped_records:
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
            # 先删除本批所有涉及月份的建议，再统一生成并插入
            for (name, dept, y, m) in seen:
                attendance_db.delete_suggestions_for_month(name, dept, y, m)
            for (name, dept, y, m) in seen:
                try:
                    suggestions_list = generate_suggestions_for_month(name, dept, y, m)
                    attendance_db.insert_suggestions(name, dept, y, m, suggestions_list)
                except Exception as e:
                    logger.warning(f"生成智能建议失败 {(name, dept, y, m)}: {e}")
        except Exception as e:
            logger.warning(f"上传后生成智能建议失败: {e}")
        
        return UploadResponse(
            success=True,
            message=f"文件处理完成！共处理 {len(mapped_records)} 条记录" + (f"，跳过未匹配工号 {len(skipped_gh)} 条" if skipped_gh else ""),
            records_count=len(mapped_records),
            success_count=success_count,
            fail_count=fail_count
        )
    
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


def _can_see_attendance_exceptions(current_user: str) -> tuple:
    """
    判断当前用户是否有权查看考勤异常。
    返回 (allowed: bool, lsys: str|None)。
    - 打卡管理员(dakaman)：可看全部，lsys 为 None 表示不按科室过滤。
    - 班组长/主任/副主任：仅可看本室，返回其 lsys 用于过滤。
    - 部长/副部长/员工等：无权限。
    """
    current_user = (current_user or "").strip()
    if not current_user:
        return False, None
    dakaman = _get_dakaman()
    if dakaman and current_user == dakaman:
        return True, None
    user = _get_user_info(current_user)
    if not user:
        return False, None
    jb = (user.get("jb") or "").strip()
    if _jb_match(jb, "组长") or _jb_match(jb, "主任") or _jb_match(jb, "副主任"):
        lsys = (user.get("lsys") or "").strip()
        return True, lsys if lsys else None
    return False, None


@router.get("/exceptions", response_model=AttendanceQueryResponse)
async def get_attendance_exceptions(
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份 1-12"),
    current_user: Optional[str] = Query(None, description="当前登录用户姓名，用于权限校验"),
):
    """
    考勤异常列表。权限：打卡管理员可看全部；各科室班组长/主任/副主任仅可看本室。
    返回指定年月内「智能建议需请假/缺勤且未完成请假或公出」的异常日对应的打卡记录。
    """
    allowed, filter_lsys = _can_see_attendance_exceptions(current_user or "")
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="仅班组长/主任/副主任或打卡管理员可查看考勤异常",
        )
    try:
        built = _build_attendance_exceptions_data(year, month, filter_lsys)
        if not built:
            msg = "本室无考勤异常" if filter_lsys else "无考勤异常"
            return AttendanceQueryResponse(success=True, message=msg, total=0, data=[])
        attendance_records = [AttendanceRecord(**rec) for rec in built]
        return AttendanceQueryResponse(
            success=True,
            message="查询成功",
            total=len(attendance_records),
            data=attendance_records,
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
    allowed, filter_lsys = _can_see_attendance_exceptions(current_user or "")
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

        rows = _build_attendance_exceptions_data(year, month, filter_lsys)
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




