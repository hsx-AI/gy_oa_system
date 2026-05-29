# -*- coding: utf-8 -*-
"""
邮件发送 API - 仅系统管理员 (webconfig.admin1) 可使用
基于网易企业邮箱 SMTP SSL 发送
支持：抄送(CC)、附件、考勤异常提醒自动邮件、定时自动发送
"""
import smtplib
import logging
import base64
import json
import asyncio
import hashlib
from collections import defaultdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from typing import Optional, List, Dict
from io import BytesIO
from datetime import datetime, date, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
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


class AttachmentItem(BaseModel):
    filename: str
    content_base64: str


class SendEmailRequest(BaseModel):
    current_user: str
    to: List[str]
    cc: Optional[List[str]] = None
    subject: str
    content: str
    content_type: str = "plain"
    attachments: Optional[List[AttachmentItem]] = None


@router.get("/config")
async def get_email_config(current_user: str = Query(...)):
    """获取当前邮箱配置（脱敏）及员工通讯录（含企业邮箱）"""
    _require_admin(current_user)
    cfg = _get_email_config()
    masked_addr = cfg["address"] if cfg["address"] else ""
    masked_code = ("*" * (len(cfg["auth_code"]) - 4) + cfg["auth_code"][-4:]) if len(cfg["auth_code"]) > 4 else "未配置"
    employees = []
    try:
        rows = db.execute_query(
            "SELECT name, lsys, enterprise_email FROM yggl WHERE name IS NOT NULL AND TRIM(name) != '' ORDER BY lsys, name",
            (),
        )
        for r in rows:
            employees.append({
                "name": (r.get("name") or "").strip(),
                "dept": (r.get("lsys") or "").strip(),
                "email": (r.get("enterprise_email") or "").strip(),
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


def _build_email_message(sender: str, recipients: List[str], cc_list: List[str],
                         subject: str, content: str, content_type: str,
                         attachments: Optional[List[AttachmentItem]] = None) -> MIMEMultipart:
    """构建支持抄送和附件的邮件消息"""
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = Header(subject, "utf-8")

    body = MIMEText(content, content_type, "utf-8")
    msg.attach(body)

    if attachments:
        for att in attachments:
            try:
                file_data = base64.b64decode(att.content_base64)
                part = MIMEBase("application", "octet-stream")
                part.set_payload(file_data)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=("utf-8", "", att.filename),
                )
                msg.attach(part)
            except Exception as e:
                logger.warning(f"附件 {att.filename} 编码失败: {e}")

    return msg


def _smtp_send(sender: str, password: str, all_recipients: List[str], message: MIMEMultipart):
    """SMTP SSL 发送"""
    smtp_obj = None
    try:
        smtp_obj = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT_SSL, timeout=15)
        smtp_obj.login(sender, password)
        smtp_obj.sendmail(sender, all_recipients, message.as_string())
        logger.info(f"邮件发送成功: {sender} -> {all_recipients}")
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


@router.post("/send")
async def send_email(req: SendEmailRequest):
    """发送邮件（支持抄送和附件）"""
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

    cc_list = [addr.strip() for addr in (req.cc or []) if addr.strip()]

    message = _build_email_message(sender, recipients, cc_list, req.subject, req.content, req.content_type, req.attachments)

    all_recipients = list(set(recipients + cc_list))
    _smtp_send(sender, password, all_recipients, message)

    cc_info = f"，抄送 {len(cc_list)} 人" if cc_list else ""
    att_info = f"，{len(req.attachments or [])} 个附件" if req.attachments else ""
    return {"success": True, "message": f"邮件已发送给 {len(recipients)} 位收件人{cc_info}{att_info}"}


# ==================== 考勤异常提醒邮件 ====================

ATTENDANCE_REMINDER_SUBJECT_SUFFIX = "（系统自动推送无需回复）"


class AttendanceReminderRequest(BaseModel):
    current_user: str
    year: int
    month: int
    cc: Optional[List[str]] = None
    test_mode: bool = True
    test_recipients: Optional[List[str]] = Field(
        None, description="测试模式下的实际收件人邮箱列表；不传或为空则默认 hsx@hec-china.com"
    )


def _get_employee_email_map() -> dict:
    """从 yggl 获取 name -> enterprise_email 映射"""
    mapping = {}
    try:
        rows = db.execute_query(
            "SELECT name, enterprise_email FROM yggl WHERE enterprise_email IS NOT NULL AND TRIM(enterprise_email) != ''",
            (),
        )
        for r in rows:
            name = (r.get("name") or "").strip()
            email = (r.get("enterprise_email") or "").strip()
            if name and email:
                mapping[name] = email
    except Exception as e:
        logger.warning(f"查询企业邮箱映射失败: {e}")
    return mapping


def _pair_counts_from_exception_keys(exception_keys: List[tuple]) -> dict:
    """(姓名, 科室) -> 异常天数；同一人多科室分别计数。"""
    pair_counts = defaultdict(int)
    for name, dept, _date_str in exception_keys:
        n = (name or "").strip()
        if not n:
            continue
        d = (dept or "").strip()
        pair_counts[(n, d)] += 1
    return pair_counts


def _dept_sort_key_for_reminder(d: str) -> tuple:
    """科室排序：部办最前，其余按名称，（未填写科室）最后。"""
    if d == "部办":
        return (0, d)
    if d == "（未填写科室）":
        return (2, d)
    return (1, d)


def _format_exception_summary_by_department(pair_counts: dict) -> str:
    """
    按科室分组（部办段落在最前，未填写科室在最后），科室内按异常天数降序、姓名升序。
    示例：智能制造技术室： 黄圣轩1天、周雨欣2天 考勤异常
    """
    dept_to_people = defaultdict(list)
    for (name, dept), cnt in pair_counts.items():
        label = dept if dept else "（未填写科室）"
        dept_to_people[label].append((name, cnt))
    lines = []
    for d in sorted(dept_to_people.keys(), key=_dept_sort_key_for_reminder):
        items = dept_to_people[d]
        items.sort(key=lambda x: (-x[1], x[0]))
        people_part = "、".join(f"{nm}{cnt}天" for nm, cnt in items)
        lines.append(f"{d}： {people_part} 考勤异常")
    return "\n".join(lines)


def _build_personal_reminder_body(name: str, month: int, days: int) -> str:
    """个人提醒邮件正文"""
    return (
        f"{name}您好\n\n"
        "我是工艺部智能办公助手\n\n"
        f"您在{month}月有 {days} 天考勤异常，请登录 http://10.42.60.230 及时处理。\n\n"
        "祝愿身体健康工作顺利"
    )


def _build_leader_reminder_body(month: int, dept: str, people_summary: str) -> str:
    """科室领导汇总邮件正文"""
    return (
        "您好\n\n"
        "我是工艺部智能办公助手\n\n"
        f"以下同事存在{month}月考勤异常：\n\n"
        f"{dept}： {people_summary}\n\n"
        "邮件已一对一发送提醒至本人，请各位领导做好监督。\n"
        "在系统「考勤异常管理」中可查看未被处理的异常考勤记录。\n\n"
        "http://10.42.60.230\n\n"
        "祝愿身体健康工作顺利"
    )


def _build_attendance_reminder_body(month: int, summary_block: str) -> str:
    """兼容旧逻辑（测试模式合并邮件使用）"""
    return (
        "各位领导同事您好\n\n"
        "我是工艺部智能办公助手\n\n"
        f"请以下人员登录 http://10.42.60.230 处理{month}月考勤异常。\n\n"
        f"{summary_block}\n\n"
        "祝愿身体健康工作顺利"
    )


def _recipient_rollups_from_pairs(pair_counts: dict, email_map: dict):
    """每人汇总总天数与涉及科室，用于收件人列表与发信。"""
    name_totals = defaultdict(int)
    name_depts = defaultdict(set)
    for (name, dept), cnt in pair_counts.items():
        name_totals[name] += cnt
        name_depts[name].add(dept if dept else "（未填写科室）")

    recipients_info = []
    recipient_emails = []
    no_email_names = []
    for name in sorted(name_totals.keys(), key=lambda n: (-name_totals[n], n)):
        depts = sorted(name_depts[name])
        dept_display = "、".join(depts) if depts else ""
        days = name_totals[name]
        email_addr = email_map.get(name)
        recipients_info.append({
            "name": name,
            "dept": dept_display,
            "days": days,
            "email": email_addr or "",
            "has_email": bool(email_addr),
        })
        if email_addr:
            recipient_emails.append(email_addr)
        else:
            no_email_names.append(name)
    return recipients_info, recipient_emails, no_email_names, len(name_totals)


def _get_dept_leader_emails_for_reminder(depts_with_exceptions: List[str], email_map: dict) -> dict:
    """
    查找有异常的每个科室的领导及其邮箱。
    规则：部办→部长/副部长；其他→主任/副主任（若无则组长）。
    返回 { dept: [{"name":..,"jb":..,"email":..}] }
    """
    from routers.approvers import _jb_sql_conditions
    bz_c, bz_p = _jb_sql_conditions("部长")
    fbz_c, fbz_p = _jb_sql_conditions("副部长")
    zr_c, zr_p = _jb_sql_conditions("主任")
    fzr_c, fzr_p = _jb_sql_conditions("副主任")
    zz_c, zz_p = _jb_sql_conditions("组长")
    bz_fbz = f"({bz_c[1:-1]} OR {fbz_c[1:-1]})"
    zr_fzr = f"({zr_c[1:-1]} OR {fzr_c[1:-1]})"

    result: dict = {}
    for dept in depts_with_exceptions:
        if dept in ("部办", "（未填写科室）"):
            rows = db.execute_query(
                f"SELECT name, jb FROM yggl WHERE {bz_fbz} "
                "AND name IS NOT NULL AND TRIM(name) != '' AND (COALESCE(zaizhi,0)=0)",
                bz_p + fbz_p,
            )
        else:
            rows = db.execute_query(
                f"SELECT name, jb FROM yggl WHERE lsys = %s AND {zr_fzr} "
                "AND name IS NOT NULL AND TRIM(name) != '' AND (COALESCE(zaizhi,0)=0)",
                (dept,) + zr_p + fzr_p,
            )
            if not rows:
                rows = db.execute_query(
                    f"SELECT name, jb FROM yggl WHERE lsys = %s AND {zz_c} "
                    "AND name IS NOT NULL AND TRIM(name) != '' AND (COALESCE(zaizhi,0)=0)",
                    (dept,) + zz_p,
                )
        leaders = []
        for r in rows:
            n = (r.get("name") or "").strip()
            if n:
                leaders.append({"name": n, "jb": (r.get("jb") or "").strip(), "email": email_map.get(n, "")})
        result[dept] = leaders
    return result


def _smtp_send_batch(sender: str, password: str, messages: List[tuple]):
    """通过单次 SMTP 连接发送多封邮件。messages: [(all_recipients, MIMEMultipart), ...]"""
    smtp_obj = None
    success_count = 0
    failures = []
    try:
        smtp_obj = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT_SSL, timeout=30)
        smtp_obj.login(sender, password)
        for recipients, msg in messages:
            try:
                smtp_obj.sendmail(sender, recipients, msg.as_string())
                success_count += 1
            except Exception as e:
                failures.append(str(e))
                logger.warning(f"邮件发送失败 -> {recipients}: {e}")
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=401, detail="SMTP 登录失败，请检查邮箱地址和授权码")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP 错误: {e}")
        raise HTTPException(status_code=500, detail=f"SMTP 发送失败: {str(e)}")
    except Exception as e:
        logger.error(f"邮件发送异常: {e}")
        raise HTTPException(status_code=500, detail=f"发送失败: {str(e)}")
    finally:
        if smtp_obj:
            try:
                smtp_obj.quit()
            except Exception:
                pass
    return success_count, failures


def _normalize_test_recipients(test_recipients: Optional[List[str]]) -> List[str]:
    """解析测试收件人列表，去重保序；空则默认 hsx@hec-china.com"""
    seen = set()
    out = []
    for item in test_recipients or []:
        addr = (item or "").strip()
        if addr and addr not in seen:
            seen.add(addr)
            out.append(addr)
    if not out:
        out = ["hsx@hec-china.com"]
    return out


def _generate_exception_excel(year: int, month: int) -> bytes:
    """生成考勤异常 Excel 附件，返回字节内容"""
    from routers.attendance import _build_attendance_exceptions_data
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
    except ImportError:
        raise HTTPException(status_code=500, detail="服务端未安装 openpyxl")

    rows = _build_attendance_exceptions_data(year, month, filter_lsys=None, include_buban=True)
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
            date_str, name, dept,
            t1, t2, t3, t4, t5, t6, t7, t8,
            "是" if is_full else "",
        ])

    col_widths = {"A": 14, "B": 10, "C": 20}
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _prepare_reminder_data(year: int, month: int):
    """
    公共数据准备：获取异常 keys、分组汇总、领导映射等。
    返回 (pair_counts, email_map, recipients_info, no_email_names, person_count,
           dept_people_map, dept_leader_map, exception_keys)
    """
    from routers.suggestions import get_attendance_exception_keys

    exception_keys = get_attendance_exception_keys(year, month, include_buban=True)
    if not exception_keys:
        return None

    pair_counts = _pair_counts_from_exception_keys(exception_keys)
    email_map = _get_employee_email_map()
    recipients_info, _emails, no_email_names, person_count = _recipient_rollups_from_pairs(pair_counts, email_map)

    dept_people_map: dict = defaultdict(list)
    for (name, dept), cnt in pair_counts.items():
        label = dept if dept else "（未填写科室）"
        dept_people_map[label].append((name, cnt))
    for d in dept_people_map:
        dept_people_map[d].sort(key=lambda x: (-x[1], x[0]))

    depts_with_exceptions = sorted(dept_people_map.keys(), key=_dept_sort_key_for_reminder)
    dept_leader_map = _get_dept_leader_emails_for_reminder(depts_with_exceptions, email_map)

    return (pair_counts, email_map, recipients_info, no_email_names, person_count,
            dept_people_map, dept_leader_map, exception_keys)


@router.post("/send-attendance-reminder")
async def send_attendance_reminder(req: AttendanceReminderRequest):
    """
    一键发送考勤异常提醒邮件（新模式）：
    1) 对每位异常人员**单独**发送个人提醒邮件。
    2) 对每个有异常的科室，向该科室领导（室主任/组长/部长）发送汇总邮件。
    test_mode=True 时所有邮件仅发送到 test_recipients。
    """
    _require_admin(req.current_user)

    cfg = _get_email_config()
    sender_addr = cfg["address"]
    password = cfg["auth_code"]
    if not sender_addr or not password:
        raise HTTPException(status_code=400, detail="邮箱未配置，请先配置发件邮箱")

    data = _prepare_reminder_data(req.year, req.month)
    if data is None:
        return {"success": True, "message": f"{req.year}年{req.month}月无考勤异常，无需发送提醒"}

    (pair_counts, email_map, recipients_info, no_email_names, person_count,
     dept_people_map, dept_leader_map, exception_keys) = data

    personal_subject = f"请处理{req.month}月考勤异常{ATTENDANCE_REMINDER_SUBJECT_SUFFIX}"
    cc_list = [addr.strip() for addr in (req.cc or []) if addr.strip()]

    try:
        excel_bytes = _generate_exception_excel(req.year, req.month)
        excel_b64 = base64.b64encode(excel_bytes).decode("utf-8")
        attachment_filename = f"考勤异常表_{req.year}年{req.month}月.xlsx"
        attachment_item = AttachmentItem(filename=attachment_filename, content_base64=excel_b64)
    except Exception as e:
        logger.error(f"生成考勤异常 Excel 附件失败: {e}")
        attachment_item = None

    name_totals: dict = defaultdict(int)
    for (name, _dept), cnt in pair_counts.items():
        name_totals[name] += cnt

    if req.test_mode:
        actual_test = _normalize_test_recipients(req.test_recipients)
        messages = []

        sample_name = next(iter(name_totals), "某某")
        sample_days = name_totals.get(sample_name, 0)
        personal_body = _build_personal_reminder_body(sample_name, req.month, sample_days)
        personal_body += (
            f"\n\n---\n[测试模式] 以上为个人提醒邮件示例\n"
            f"实际将单独发送给 {len([r for r in recipients_info if r['has_email']])} 位异常人员"
        )
        if no_email_names:
            personal_body += f"\n未找到邮箱: {', '.join(no_email_names)}"
        msg1 = _build_email_message(sender_addr, actual_test, cc_list, f"[测试-个人提醒] {personal_subject}", personal_body, "plain")
        messages.append((list(set(actual_test + cc_list)), msg1))

        leader_body_parts = []
        total_leader_email_count = 0
        depts_sorted = sorted(dept_people_map.keys(), key=_dept_sort_key_for_reminder)
        for dept in depts_sorted:
            people = dept_people_map[dept]
            people_str = "、".join(f"{nm}{cnt}天" for nm, cnt in people)
            leaders = dept_leader_map.get(dept, [])
            leader_names = "、".join(f"{l['name']}({l['jb']})" for l in leaders) or "未找到领导"
            leader_emails_for_dept = [l["email"] for l in leaders if l.get("email")]
            total_leader_email_count += len(leader_emails_for_dept)
            leader_body_parts.append(f"【{dept}】→ 发送给: {leader_names}\n  {people_str} 考勤异常")
        combined_leader_body = (
            "以下为各科室领导汇总邮件预览\n\n"
            + "\n\n".join(leader_body_parts)
            + f"\n\n---\n[测试模式] 实际将发送 {len(depts_sorted)} 封领导汇总邮件（共 {total_leader_email_count} 个领导邮箱）"
        )
        leader_subject = f"[测试-领导汇总] {req.month}月考勤异常汇总{ATTENDANCE_REMINDER_SUBJECT_SUFFIX}"
        att_list = [attachment_item] if attachment_item else []
        msg2 = _build_email_message(sender_addr, actual_test, cc_list, leader_subject, combined_leader_body, "plain", att_list)
        messages.append((list(set(actual_test + cc_list)), msg2))

        success_count, failures = _smtp_send_batch(sender_addr, password, messages)
        return {
            "success": True,
            "message": f"测试邮件已发送（{success_count} 封成功）到 {', '.join(actual_test)}",
            "personal_sent": 1 if success_count >= 1 else 0,
            "leader_sent": 1 if success_count >= 2 else 0,
            "failures": failures,
        }

    messages = []
    personal_sent_names = []
    for r in recipients_info:
        if not r["has_email"]:
            continue
        days = r["days"]
        body = _build_personal_reminder_body(r["name"], req.month, days)
        msg = _build_email_message(sender_addr, [r["email"]], cc_list, personal_subject, body, "plain")
        messages.append((list(set([r["email"]] + cc_list)), msg))
        personal_sent_names.append(r["name"])

    leader_sent_depts = []
    depts_sorted = sorted(dept_people_map.keys(), key=_dept_sort_key_for_reminder)
    for dept in depts_sorted:
        leaders = dept_leader_map.get(dept, [])
        leader_emails = [l["email"] for l in leaders if l.get("email")]
        if not leader_emails:
            continue
        people = dept_people_map[dept]
        people_str = "、".join(f"{nm}{cnt}天" for nm, cnt in people)
        body = _build_leader_reminder_body(req.month, dept, people_str)
        subject = f"{dept}{req.month}月考勤异常汇总{ATTENDANCE_REMINDER_SUBJECT_SUFFIX}"
        att_list = [attachment_item] if attachment_item else []
        msg = _build_email_message(sender_addr, leader_emails, cc_list, subject, body, "plain", att_list)
        messages.append((list(set(leader_emails + cc_list)), msg))
        leader_sent_depts.append(dept)

    if not messages:
        raise HTTPException(status_code=400, detail="所有异常人员及领导均未配置企业邮箱，无法发送")

    success_count, failures = _smtp_send_batch(sender_addr, password, messages)
    personal_count = len(personal_sent_names)
    leader_count = len(leader_sent_depts)

    return {
        "success": True,
        "message": (
            f"已发送 {success_count} 封邮件（个人提醒 {personal_count} 封 + 领导汇总 {leader_count} 封）"
            + (f"，{len(failures)} 封失败" if failures else "")
        ),
        "personal_sent": personal_count,
        "leader_sent": leader_count,
        "total_sent": success_count,
        "failures": failures,
        "no_email_names": no_email_names,
    }


@router.post("/preview-attendance-reminder")
async def preview_attendance_reminder(req: AttendanceReminderRequest):
    """预览考勤异常提醒邮件内容（不实际发送）"""
    _require_admin(req.current_user)

    data = _prepare_reminder_data(req.year, req.month)
    if data is None:
        return {"success": True, "has_exceptions": False, "message": f"{req.year}年{req.month}月无考勤异常"}

    (pair_counts, email_map, recipients_info, no_email_names, person_count,
     dept_people_map, dept_leader_map, exception_keys) = data

    personal_subject = f"请处理{req.month}月考勤异常{ATTENDANCE_REMINDER_SUBJECT_SUFFIX}"

    name_totals: dict = defaultdict(int)
    for (name, _dept), cnt in pair_counts.items():
        name_totals[name] += cnt

    sample_name = next(iter(name_totals), "某某")
    sample_days = name_totals.get(sample_name, 0)
    personal_body_sample = _build_personal_reminder_body(sample_name, req.month, sample_days)

    leader_emails_preview = []
    depts_sorted = sorted(dept_people_map.keys(), key=_dept_sort_key_for_reminder)
    for dept in depts_sorted:
        people = dept_people_map[dept]
        people_str = "、".join(f"{nm}{cnt}天" for nm, cnt in people)
        leaders = dept_leader_map.get(dept, [])
        leader_subject = f"{dept}{req.month}月考勤异常汇总{ATTENDANCE_REMINDER_SUBJECT_SUFFIX}"
        leader_body = _build_leader_reminder_body(req.month, dept, people_str)
        leader_emails_preview.append({
            "dept": dept,
            "subject": leader_subject,
            "body": leader_body,
            "leaders": [
                {"name": l["name"], "jb": l["jb"], "email": l.get("email", ""), "has_email": bool(l.get("email"))}
                for l in leaders
            ],
            "people_count": len(people),
            "people_summary": people_str,
        })

    total_personal_sendable = sum(1 for r in recipients_info if r["has_email"])
    total_leader_sendable = sum(
        len([l for l in dept_leader_map.get(d, []) if l.get("email")])
        for d in depts_sorted
    )

    return {
        "success": True,
        "has_exceptions": True,
        "total_persons": person_count,
        "total_days": len(exception_keys),
        "no_email_names": no_email_names,
        "no_email_count": len(no_email_names),
        "has_email_count": person_count - len(no_email_names),
        "personal_subject": personal_subject,
        "personal_body_sample": personal_body_sample,
        "personal_recipients": recipients_info,
        "total_personal_sendable": total_personal_sendable,
        "leader_emails": leader_emails_preview,
        "total_leader_emails": len(leader_emails_preview),
        "total_leader_sendable": total_leader_sendable,
    }


# ==================== 自动发送配置 ====================


def _ensure_auto_reminder_columns():
    """确保 webconfig 表有自动发送相关列"""
    for col, typedef in [
        ("auto_reminder_enabled", "TINYINT DEFAULT 0"),
        ("auto_reminder_schedules", "TEXT"),
        ("auto_reminder_log", "MEDIUMTEXT"),
    ]:
        try:
            db.execute_update(f"ALTER TABLE webconfig ADD COLUMN {col} {typedef}", ())
        except Exception:
            pass


def _get_auto_reminder_config() -> dict:
    _ensure_auto_reminder_columns()
    try:
        rows = db.execute_query(
            "SELECT auto_reminder_enabled, auto_reminder_schedules, auto_reminder_log FROM webconfig WHERE id = %s LIMIT 1",
            ("1",),
        )
        if not rows:
            return {"enabled": False, "schedules": [], "log": []}
        r = rows[0]
        enabled = bool(r.get("auto_reminder_enabled"))
        schedules_raw = r.get("auto_reminder_schedules") or "[]"
        log_raw = r.get("auto_reminder_log") or "[]"
        try:
            schedules = json.loads(schedules_raw)
        except Exception:
            schedules = []
        try:
            log_list = json.loads(log_raw)
        except Exception:
            log_list = []
        return {"enabled": enabled, "schedules": schedules, "log": log_list}
    except Exception as e:
        logger.warning(f"读取自动发送配置失败: {e}")
        return {"enabled": False, "schedules": [], "log": []}


def _save_auto_reminder_config(enabled: bool, schedules: list):
    _ensure_auto_reminder_columns()
    db.execute_update(
        "UPDATE webconfig SET auto_reminder_enabled = %s, auto_reminder_schedules = %s WHERE id = %s",
        (1 if enabled else 0, json.dumps(schedules, ensure_ascii=False), "1"),
    )


def _append_auto_reminder_log(entry: dict):
    _ensure_auto_reminder_columns()
    try:
        rows = db.execute_query(
            "SELECT auto_reminder_log FROM webconfig WHERE id = %s LIMIT 1", ("1",)
        )
        raw = (rows[0].get("auto_reminder_log") if rows else None) or "[]"
        try:
            log_list = json.loads(raw)
        except Exception:
            log_list = []
        log_list.insert(0, entry)
        log_list = log_list[:50]
        db.execute_update(
            "UPDATE webconfig SET auto_reminder_log = %s WHERE id = %s",
            (json.dumps(log_list, ensure_ascii=False), "1"),
        )
    except Exception as e:
        logger.error(f"写入自动发送日志失败: {e}")


class AutoReminderConfigRequest(BaseModel):
    current_user: str
    enabled: bool
    schedules: list = Field(
        default_factory=list,
        description='[{"day":5,"hour":9,"minute":0,"monthScope":"last"}, ...] monthScope: last=上月考勤, current=本月考勤',
    )


class AutoReminderNoticeReadRequest(BaseModel):
    current_user: str
    id: int


def _ensure_auto_reminder_notice_table():
    try:
        db.execute_update(
            """
            CREATE TABLE IF NOT EXISTS auto_reminder_result_notifications (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                recipient_name VARCHAR(100) NOT NULL,
                title VARCHAR(120) NOT NULL,
                description TEXT NOT NULL,
                target_year INT NOT NULL,
                target_month INT NOT NULL,
                trigger_label VARCHAR(120) NOT NULL,
                source_time VARCHAR(30) NOT NULL,
                source_key VARCHAR(64) NOT NULL,
                is_read TINYINT NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                read_at DATETIME NULL,
                UNIQUE KEY uk_auto_reminder_notice (recipient_name, source_key),
                INDEX idx_auto_reminder_notice_recipient (recipient_name, is_read, created_at)
            )
            """,
            (),
        )
    except Exception as e:
        logger.warning(f"确保自动发送结果通知表失败: {e}")
    try:
        cols = db.execute_query("SHOW COLUMNS FROM auto_reminder_result_notifications LIKE 'source_key'", ())
        if not cols:
            db.execute_update(
                "ALTER TABLE auto_reminder_result_notifications ADD COLUMN source_key VARCHAR(64) NOT NULL DEFAULT '' AFTER source_time",
                (),
            )
    except Exception as e:
        logger.warning(f"确保自动发送结果通知 source_key 字段失败: {e}")
    try:
        idx_rows = db.execute_query(
            """
            SELECT INDEX_NAME
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'auto_reminder_result_notifications'
              AND INDEX_NAME = 'uk_auto_reminder_notice_source'
            LIMIT 1
            """,
            (),
        )
        if not idx_rows:
            db.execute_update(
                "ALTER TABLE auto_reminder_result_notifications ADD UNIQUE KEY uk_auto_reminder_notice_source (recipient_name, source_key)",
                (),
            )
    except Exception as e:
        logger.warning(f"确保自动发送结果通知 source_key 唯一索引失败: {e}")


def _get_auto_reminder_notice_recipients() -> List[str]:
    names = set()
    try:
        rows = db.execute_query(
            """
            SELECT name
            FROM yggl
            WHERE name IS NOT NULL AND TRIM(name) != ''
              AND COALESCE(zaizhi, 0) = 0
              AND (
                TRIM(COALESCE(jb, '')) = %s
                OR TRIM(COALESCE(jb, '')) LIKE %s
                OR TRIM(COALESCE(jb, '')) = %s
                OR TRIM(COALESCE(jb, '')) LIKE %s
              )
            """,
            ("经理", "经理%", "副经理", "副经理%"),
        )
        for r in rows or []:
            n = (r.get("name") or "").strip()
            if n:
                names.add(n)
    except Exception as e:
        logger.warning(f"查询自动发送结果通知经理/副经理失败: {e}")

    try:
        rows = db.execute_query("SELECT dakaman, admin1 FROM webconfig WHERE id = %s LIMIT 1", ("1",))
        if rows:
            for col in ("dakaman", "admin1"):
                n = (rows[0].get(col) or "").strip()
                if n:
                    names.add(n)
    except Exception as e:
        logger.warning(f"查询自动发送结果通知管理员失败: {e}")

    return sorted(names)


def _create_auto_reminder_result_notifications(log_entry: dict):
    if log_entry.get("status") != "ok":
        return
    _ensure_auto_reminder_notice_table()
    recipients = _get_auto_reminder_notice_recipients()
    if not recipients:
        return

    year = int(log_entry.get("year") or 0)
    month = int(log_entry.get("month") or 0)
    trigger = (log_entry.get("trigger") or "").strip()
    source_time = (log_entry.get("time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")).strip()
    message = (log_entry.get("message") or "").strip()
    source_key = hashlib.sha256(f"{year}|{month}|{trigger}|{source_time}".encode("utf-8")).hexdigest()
    title = "考勤异常邮件提醒发送结果"
    description = f"{year}年{month}月考勤异常邮件提醒已完成：{message}。触发计划：{trigger}。"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for name in recipients:
        try:
            db.execute_update(
                """
                INSERT IGNORE INTO auto_reminder_result_notifications
                (recipient_name, title, description, target_year, target_month, trigger_label, source_time, source_key, is_read, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, %s)
                """,
                (name, title, description, year, month, trigger, source_time, source_key, now),
            )
        except Exception as e:
            logger.warning(f"写入自动发送结果通知失败 recipient={name}: {e}")


@router.get("/auto-reminder-config")
async def get_auto_reminder_config_api(current_user: str = Query(...)):
    _require_admin(current_user)
    cfg = _get_auto_reminder_config()
    return {"success": True, **cfg}


@router.post("/auto-reminder-config")
async def save_auto_reminder_config_api(req: AutoReminderConfigRequest):
    _require_admin(req.current_user)
    valid = []
    for s in req.schedules:
        d = int(s.get("day", 0))
        h = int(s.get("hour", 9))
        m = int(s.get("minute", 0))
        scope = str(s.get("monthScope") or "last").strip().lower()
        if scope not in ("last", "current"):
            scope = "last"
        if (1 <= d <= 31 or d == -1) and 0 <= h <= 23 and 0 <= m <= 59:
            valid.append({"day": d, "hour": h, "minute": m, "monthScope": scope})
    _save_auto_reminder_config(req.enabled, valid)
    return {"success": True, "message": f"已保存（{'启用' if req.enabled else '停用'}，{len(valid)} 条计划）"}


@router.get("/auto-reminder-log")
async def get_auto_reminder_log_api(current_user: str = Query(...)):
    _require_admin(current_user)
    cfg = _get_auto_reminder_config()
    return {"success": True, "log": cfg.get("log", [])}


@router.get("/auto-reminder-notices")
async def get_auto_reminder_notices(name: str = Query(...)):
    current_user = (name or "").strip()
    if not current_user:
        return {"success": True, "data": []}
    _ensure_auto_reminder_notice_table()
    rows = db.execute_query(
        """
        SELECT id, title, description, target_year, target_month, trigger_label, source_time, created_at
        FROM auto_reminder_result_notifications
        WHERE recipient_name = %s AND is_read = 0
        ORDER BY created_at DESC, id DESC
        LIMIT 20
        """,
        (current_user,),
    )
    data = []
    for r in rows or []:
        data.append({
            "id": r.get("id"),
            "title": (r.get("title") or "").strip(),
            "description": (r.get("description") or "").strip(),
            "year": r.get("target_year"),
            "month": r.get("target_month"),
            "trigger": (r.get("trigger_label") or "").strip(),
            "sourceTime": (r.get("source_time") or "").strip(),
            "createdAt": str(r.get("created_at") or ""),
        })
    return {"success": True, "data": data}


@router.post("/auto-reminder-notices/read")
async def mark_auto_reminder_notice_read(req: AutoReminderNoticeReadRequest):
    current_user = (req.current_user or "").strip()
    if not current_user or not req.id:
        return {"success": False, "message": "参数不完整"}
    _ensure_auto_reminder_notice_table()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute_update(
        """
        UPDATE auto_reminder_result_notifications
        SET is_read = 1, read_at = %s
        WHERE id = %s AND recipient_name = %s
        """,
        (now, req.id, current_user),
    )
    return {"success": True, "message": "已阅"}


@router.post("/run-todo-reminder")
async def run_todo_reminder_api(current_user: str = Query(...)):
    """手动触发一次管理人员待办邮件提醒（调试用，仅 admin1 可用）。"""
    _require_admin(current_user)
    recipients = _get_todo_reminder_recipients()
    result = await run_todo_email_reminder_once()
    result["_debug_recipients_sample"] = [r["name"] for r in recipients[:5]]
    return {"success": True, "result": result}


async def _execute_auto_send(year: int, month: int, trigger_label: str):
    """执行一次自动发送（与手动 send_attendance_reminder 正式模式相同逻辑）"""
    log_entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trigger": trigger_label,
        "year": year,
        "month": month,
        "status": "error",
        "message": "",
    }
    try:
        cfg = _get_email_config()
        sender_addr = cfg["address"]
        password = cfg["auth_code"]
        if not sender_addr or not password:
            log_entry["message"] = "邮箱未配置"
            _append_auto_reminder_log(log_entry)
            return

        data = _prepare_reminder_data(year, month)
        if data is None:
            log_entry["status"] = "ok"
            log_entry["message"] = f"{year}年{month}月无考勤异常"
            _append_auto_reminder_log(log_entry)
            return

        (pair_counts, email_map, recipients_info, no_email_names, person_count,
         dept_people_map, dept_leader_map, exception_keys) = data

        personal_subject = f"请处理{month}月考勤异常{ATTENDANCE_REMINDER_SUBJECT_SUFFIX}"

        try:
            excel_bytes = _generate_exception_excel(year, month)
            excel_b64 = base64.b64encode(excel_bytes).decode("utf-8")
            attachment_item = AttachmentItem(
                filename=f"考勤异常表_{year}年{month}月.xlsx",
                content_base64=excel_b64,
            )
        except Exception:
            attachment_item = None

        name_totals: dict = defaultdict(int)
        for (name, _dept), cnt in pair_counts.items():
            name_totals[name] += cnt

        messages = []
        for r in recipients_info:
            if not r["has_email"]:
                continue
            body = _build_personal_reminder_body(r["name"], month, r["days"])
            msg = _build_email_message(sender_addr, [r["email"]], [], personal_subject, body, "plain")
            messages.append(([r["email"]], msg))

        depts_sorted = sorted(dept_people_map.keys(), key=_dept_sort_key_for_reminder)
        leader_count = 0
        for dept in depts_sorted:
            leaders = dept_leader_map.get(dept, [])
            leader_emails = [l["email"] for l in leaders if l.get("email")]
            if not leader_emails:
                continue
            people = dept_people_map[dept]
            people_str = "、".join(f"{nm}{cnt}天" for nm, cnt in people)
            body = _build_leader_reminder_body(month, dept, people_str)
            subject = f"{dept}{month}月考勤异常汇总{ATTENDANCE_REMINDER_SUBJECT_SUFFIX}"
            att_list = [attachment_item] if attachment_item else []
            msg = _build_email_message(sender_addr, leader_emails, [], subject, body, "plain", att_list)
            messages.append((leader_emails, msg))
            leader_count += 1

        if messages:
            success_count, failures = _smtp_send_batch(sender_addr, password, messages)
        else:
            success_count, failures = 0, []

        personal_sent = sum(1 for r in recipients_info if r["has_email"])
        log_entry["status"] = "ok"
        log_entry["message"] = f"发送 {success_count} 封（个人 {personal_sent} + 领导 {leader_count}）"
        if failures:
            log_entry["message"] += f"，{len(failures)} 封失败"
        log_entry["personal_sent"] = personal_sent
        log_entry["leader_sent"] = leader_count
        _create_auto_reminder_result_notifications(log_entry)

    except Exception as e:
        log_entry["message"] = str(e)[:200]
        logger.error(f"自动发送考勤提醒失败: {e}")

    _append_auto_reminder_log(log_entry)


def _has_already_sent_for_month(target_year: int, target_month: int) -> bool:
    """检查数据库日志中是否已经成功发送过该目标月份的提醒"""
    try:
        rows = db.execute_query(
            "SELECT auto_reminder_log FROM webconfig WHERE id = %s LIMIT 1", ("1",)
        )
        raw = (rows[0].get("auto_reminder_log") if rows else None) or "[]"
        log_list = json.loads(raw) if raw else []
        for entry in log_list:
            if (entry.get("status") == "ok"
                    and entry.get("year") == target_year
                    and entry.get("month") == target_month
                    and (entry.get("personal_sent", 0) > 0 or entry.get("leader_sent", 0) > 0)):
                return True
    except Exception as e:
        logger.warning(f"[AutoReminder] 检查已发送记录失败: {e}")
    return False


def _try_acquire_mysql_lock(lock_name: str, owner_label: str):
    conn = None
    try:
        conn = db.get_connection()
        if not conn:
            logger.warning("[%s] 获取数据库连接失败，无法获取发送锁", owner_label)
            return None
        with conn.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK(%s, 0) AS acquired", (lock_name,))
            row = cursor.fetchone() or {}
        if int(row.get("acquired") or 0) == 1:
            return conn
        logger.info("[%s] 跳过：已有其他进程持有发送锁 %s", owner_label, lock_name)
    except Exception as e:
        logger.warning("[%s] 获取发送锁失败 %s: %s", owner_label, lock_name, e)
    if conn:
        conn.close()
    return None


def _release_mysql_lock(conn, lock_name: str, owner_label: str):
    if not conn:
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
    except Exception as e:
        logger.warning("[%s] 释放发送锁失败 %s: %s", owner_label, lock_name, e)
    finally:
        conn.close()


async def _execute_auto_send_with_month_lock(year: int, month: int, trigger_label: str, now: datetime):
    """
    用 MySQL advisory lock 保护自动发送，避免多个后端进程同时命中同一计划时重复发信。
    """
    lock_name = f"oa_auto_reminder_{year}_{month}"
    conn = _try_acquire_mysql_lock(lock_name, "AutoReminder")
    if not conn:
        _append_auto_reminder_log({
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "trigger": trigger_label,
            "year": year,
            "month": month,
            "status": "skipped",
            "message": f"已跳过：{year}年{month}月提醒正在由其他进程发送",
        })
        return
    try:
        if _has_already_sent_for_month(year, month):
            _append_auto_reminder_log({
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "trigger": trigger_label,
                "year": year,
                "month": month,
                "status": "skipped",
                "message": f"已跳过：{year}年{month}月提醒已由之前的计划发送",
            })
            return

        await _execute_auto_send(year, month, trigger_label)
    except Exception as e:
        logger.error(f"[AutoReminder] 自动发送互斥执行失败: {e}")
    finally:
        _release_mysql_lock(conn, lock_name, "AutoReminder")


async def auto_reminder_background_loop():
    """后台循环：每 60 秒检查是否需要自动发送"""
    logger.info("[AutoReminder] 后台定时检查已启动")
    print("[System] 考勤异常提醒自动发送后台任务已启动")
    last_triggered: dict = {}
    while True:
        try:
            await asyncio.sleep(60)
            cfg = _get_auto_reminder_config()
            if not cfg["enabled"] or not cfg["schedules"]:
                continue

            now = datetime.now()
            import calendar as _cal
            _, last_day_of_month = _cal.monthrange(now.year, now.month)
            for sch in cfg["schedules"]:
                d, h, m = int(sch.get("day", 0)), int(sch.get("hour", 9)), int(sch.get("minute", 0))
                scope = str(sch.get("monthScope") or "last").strip().lower()
                if scope not in ("last", "current"):
                    scope = "last"
                match_day = (now.day == d) or (d == -1 and now.day == last_day_of_month)
                if not match_day or now.hour != h or abs(now.minute - m) > 1:
                    continue

                if scope == "current":
                    target_year, target_month = now.year, now.month
                elif now.month == 1:
                    target_year, target_month = now.year - 1, 12
                else:
                    target_year, target_month = now.year, now.month - 1

                sch_run_key = f"{now.strftime('%Y-%m-%d')}_{d}_{h}:{m:02d}"
                if sch_run_key in last_triggered:
                    continue
                last_triggered[sch_run_key] = True

                target_key = f"sent_{target_year}_{target_month}"
                if target_key in last_triggered:
                    day_label = "最后一天" if d == -1 else f"{d}号"
                    logger.info(
                        f"[AutoReminder] 跳过: {target_year}年{target_month}月已由其他计划发送过 "
                        f"(计划: 每月{day_label} {h}:{m:02d})"
                    )
                    continue

                if _has_already_sent_for_month(target_year, target_month):
                    last_triggered[target_key] = True
                    day_label = "最后一天" if d == -1 else f"{d}号"
                    logger.info(
                        f"[AutoReminder] 跳过: {target_year}年{target_month}月已发送过（数据库记录） "
                        f"(计划: 每月{day_label} {h}:{m:02d})"
                    )
                    _append_auto_reminder_log({
                        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "trigger": f"每月{day_label} {h}:{m:02d}",
                        "year": target_year,
                        "month": target_month,
                        "status": "skipped",
                        "message": f"已跳过：{target_year}年{target_month}月提醒已由之前的计划发送",
                    })
                    continue

                if len(last_triggered) > 200:
                    keys = sorted(last_triggered.keys())
                    for k in keys[:100]:
                        del last_triggered[k]

                last_triggered[target_key] = True

                day_label = "最后一天" if d == -1 else f"{d}号"
                month_label = "本月" if scope == "current" else "上月"
                logger.info(
                    f"[AutoReminder] 触发自动发送: {target_year}年{target_month}月 ({month_label}) "
                    f"(计划: 每月{day_label} {h}:{m:02d})"
                )
                print(f"[AutoReminder] 触发: {target_year}年{target_month}月 ({month_label})")
                await _execute_auto_send_with_month_lock(
                    target_year,
                    target_month,
                    f"每月{day_label} {h}:{m:02d} · {month_label}考勤",
                    now,
                )
        except Exception as e:
            logger.error(f"[AutoReminder] 循环异常: {e}")
            await asyncio.sleep(300)


# ==================== 周排班自动邮件 ====================

SHIFT_SCHEDULE_SEND_HOUR = 17
SHIFT_SCHEDULE_SEND_CHECK_SECONDS = 60


def _ensure_shift_schedule_email_log_table():
    db.execute_update("""
        CREATE TABLE IF NOT EXISTS shift_schedule_email_log (
          id INT AUTO_INCREMENT PRIMARY KEY,
          department VARCHAR(100) NOT NULL,
          week_start DATE NOT NULL,
          week_end DATE NOT NULL,
          trigger_label VARCHAR(100) NULL,
          recipient_count INT NOT NULL DEFAULT 0,
          status VARCHAR(20) NOT NULL DEFAULT 'ok',
          message VARCHAR(500) NULL,
          sent_at DATETIME NOT NULL,
          INDEX idx_shift_mail_week (department, week_start, status),
          INDEX idx_shift_mail_sent_at (sent_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    try:
        db.execute_update("ALTER TABLE shift_schedule_email_log DROP INDEX uk_shift_mail_week", ())
    except Exception:
        pass
    try:
        db.execute_update(
            "ALTER TABLE shift_schedule_email_log ADD INDEX idx_shift_mail_week (department, week_start, status)",
            (),
        )
    except Exception:
        pass


def _shift_schedule_email_sent(department: str, week_start: date) -> bool:
    _ensure_shift_schedule_email_log_table()
    rows = db.execute_query(
        "SELECT id FROM shift_schedule_email_log "
        "WHERE department = %s AND week_start = %s AND status = 'ok' LIMIT 1",
        (department, week_start.strftime("%Y-%m-%d")),
    )
    return bool(rows)


def _record_shift_schedule_email_log(
    department: str,
    week_start: date,
    week_end: date,
    trigger_label: str,
    recipient_count: int,
    status: str,
    message: str,
):
    _ensure_shift_schedule_email_log_table()
    db.execute_update(
        "INSERT INTO shift_schedule_email_log "
        "(department, week_start, week_end, trigger_label, recipient_count, status, message, sent_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            department,
            week_start.strftime("%Y-%m-%d"),
            week_end.strftime("%Y-%m-%d"),
            trigger_label,
            recipient_count,
            status,
            (message or "")[:500],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )


def _shift_schedule_target_week(department: str, now: Optional[datetime] = None) -> date:
    """按科室配置的发送日，返回当日 17:00 邮件对应的排班周起始日。"""
    from routers.shift_schedule import _shift_schedule_target_week_start
    return _shift_schedule_target_week_start(department, now)


def _get_shift_config_recipients(department: str) -> List[dict]:
    from routers.shift_schedule import _parse_shift_email_recipients
    try:
        rows = db.execute_query(
            "SELECT email_recipients FROM shift_config WHERE department = %s LIMIT 1",
            (department,),
        )
        if rows:
            return _parse_shift_email_recipients(rows[0].get("email_recipients"))
    except Exception as e:
        logger.warning("[ShiftScheduleEmail] 读取排班收件人失败 %s: %s", department, e)
    return []


def _get_shift_dept_leader_recipients(department: str) -> List[dict]:
    from routers.approvers import _jb_match
    rows = db.execute_query(
        "SELECT name, jb, enterprise_email FROM yggl "
        "WHERE lsys = %s AND name IS NOT NULL AND TRIM(name) != '' "
        "AND COALESCE(zaizhi,0) = 0",
        (department,),
    )
    leaders = []
    for r in rows or []:
        jb = (r.get("jb") or "").strip()
        if not (_jb_match(jb, "主任") or _jb_match(jb, "副主任") or _jb_match(jb, "组长")):
            continue
        email = (r.get("enterprise_email") or "").strip()
        if not email:
            continue
        leaders.append({"name": (r.get("name") or "").strip(), "email": email, "jb": jb})
    return leaders


def _resolve_shift_schedule_email_scope(current_user: str, requested_department: Optional[str]) -> Optional[str]:
    """管理员可发全部/指定科室；科室主任、副主任、班组长只能发本科室。"""
    user = (current_user or "").strip()
    if not user:
        raise HTTPException(status_code=403, detail="请先登录")

    admin1 = _get_admin1()
    req_dept = (requested_department or "").strip()
    if admin1 and user == admin1:
        return req_dept or None

    from routers.approvers import _jb_match
    rows = db.execute_query(
        "SELECT lsys, jb FROM yggl WHERE name = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
        (user,),
    )
    if not rows:
        raise HTTPException(status_code=403, detail="未找到当前用户信息，无法发送排班邮件")
    my_dept = (rows[0].get("lsys") or "").strip()
    jb = (rows[0].get("jb") or "").strip()
    is_shift_manager = _jb_match(jb, "主任") or _jb_match(jb, "副主任") or _jb_match(jb, "组长")
    if not is_shift_manager or not my_dept:
        raise HTTPException(status_code=403, detail="仅本科室主任、副主任、班组长可手动发送排班邮件")
    if req_dept and req_dept != my_dept:
        raise HTTPException(status_code=403, detail="仅可发送本人所在科室的排班邮件")
    return my_dept


def _merge_shift_email_recipients(*groups: List[dict]) -> List[dict]:
    merged = []
    seen = set()
    for group in groups:
        for item in group or []:
            email = (item.get("email") or "").strip()
            if not email:
                continue
            key = email.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append({"name": (item.get("name") or "").strip(), "email": email})
    return merged


def _normalize_shift_recipient_unit(unit: str) -> str:
    from routers.shift_schedule import SHIFT_EMAIL_RECIPIENT_UNITS

    u = (unit or "").strip() or "其他"
    return u if u in SHIFT_EMAIL_RECIPIENT_UNITS else "其他"


def _shift_recipient_units(config_recipients: List[dict], leaders: List[dict]) -> set:
    """科室参与合并发送的单位集合；无配置收件人仅有管理人员时归入「其他」。"""
    units = set()
    for item in config_recipients or []:
        email = (item.get("email") or "").strip()
        if not email:
            continue
        units.add(_normalize_shift_recipient_unit(item.get("unit")))
    if not units and leaders:
        units.add("其他")
    return units


def _build_shift_schedule_email_body(report: dict) -> str:
    week_start = report["week_start"]
    week_end = report["week_end"]
    return (
        "<p>各位领导同事您好：</p>"
        f"<p>以下为{report['department']} {week_start.month}月{week_start.day}日"
        f"至{week_end.month}月{week_end.day}日排班计划，附件为周排班表。</p>"
        f"{report['html_table']}"
    )


def _build_merged_shift_schedule_subject(reports: List[dict], unit: str) -> str:
    if not reports:
        return "排班计划（自动发送）"
    ws = min(r["week_start"] for r in reports)
    dept_names = "、".join(r["department"] for r in reports)
    if len(reports) == 1:
        return f"{ws.month}月{ws.day}日排班智能制造工艺部{dept_names}排班计划（自动发送）"
    return f"{ws.month}月{ws.day}日排班智能制造工艺部{dept_names}等单位周排班计划（{unit}·自动发送）"


def _build_merged_shift_schedule_body(reports: List[dict], unit: str) -> str:
    dept_names = "、".join(r["department"] for r in reports)
    parts = [
        "<p>各位领导同事您好：</p>",
        f"<p>以下为向<strong>{unit}</strong>发送的周排班计划，包含<strong>{dept_names}</strong>，"
        f"共 {len(reports)} 个科室排班表（见附件）。</p>",
    ]
    for report in reports:
        week_start = report["week_start"]
        week_end = report["week_end"]
        parts.append(
            f"<p><strong>{report['department']}</strong> "
            f"{week_start.month}月{week_start.day}日至{week_end.month}月{week_end.day}日：</p>"
            f"{report['html_table']}"
        )
    return "".join(parts)


def _collect_shift_email_send_buckets(jobs: List[dict]) -> dict:
    """
    按发送星期 + 收件人单位合并。
    jobs 元素需含 department, send_weekday, report, config_recipients, leaders。
    """
    buckets = {}
    for job in jobs:
        dept = job["department"]
        send_wd = job["send_weekday"]
        report = job["report"]
        config = job["config_recipients"]
        leaders = job["leaders"]
        units = _shift_recipient_units(config, leaders)
        if not units:
            continue
        for unit in units:
            key = (send_wd, unit)
            bucket = buckets.setdefault(
                key,
                {
                    "send_weekday": send_wd,
                    "unit": unit,
                    "reports": [],
                    "to_emails": set(),
                    "cc_emails": set(),
                    "departments": [],
                },
            )
            if dept not in bucket["departments"]:
                bucket["departments"].append(dept)
                bucket["reports"].append(report)
            for item in config or []:
                if _normalize_shift_recipient_unit(item.get("unit")) != unit:
                    continue
                email = (item.get("email") or "").strip()
                if email:
                    bucket["to_emails"].add(email)
            for item in leaders or []:
                email = (item.get("email") or "").strip()
                if email:
                    bucket["cc_emails"].add(email)
    for bucket in buckets.values():
        bucket["cc_emails"] -= bucket["to_emails"]
    return buckets


async def run_shift_schedule_email_once(
    trigger_label: str = "周五17:00自动发送",
    target_week_start: Optional[date] = None,
    department_filter: Optional[str] = None,
    only_departments: Optional[List[str]] = None,
    force: bool = False,
) -> dict:
    """发送周排班邮件：按发送时间与收件人单位合并，同单位同时间只发一封（多附件）。"""
    lock_scope = department_filter or ",".join(only_departments or []) or "all"
    lock_week = target_week_start.strftime("%Y-%m-%d") if target_week_start else datetime.now().strftime("%Y-%m-%d")
    lock_name = f"oa_shift_schedule_email_{lock_week}_{hashlib.sha256(lock_scope.encode('utf-8')).hexdigest()[:16]}"
    lock_conn = _try_acquire_mysql_lock(lock_name, "ShiftScheduleEmail")
    if not lock_conn:
        return {"success": True, "message": "已有其他进程正在发送周排班邮件，本进程已跳过", "sent": 0, "skipped": 0, "errors": 0}
    try:
        return await _run_shift_schedule_email_once_locked(
            trigger_label=trigger_label,
            target_week_start=target_week_start,
            department_filter=department_filter,
            only_departments=only_departments,
            force=force,
        )
    finally:
        _release_mysql_lock(lock_conn, lock_name, "ShiftScheduleEmail")


async def _run_shift_schedule_email_once_locked(
    trigger_label: str = "周五17:00自动发送",
    target_week_start: Optional[date] = None,
    department_filter: Optional[str] = None,
    only_departments: Optional[List[str]] = None,
    force: bool = False,
) -> dict:
    from routers.shift_schedule import (
        _get_shift_departments,
        _get_shift_email_send_weekday,
        _load_shift_email_feature_config,
        build_week_schedule_report,
    )

    cfg = _get_email_config()
    sender_addr = cfg["address"]
    password = cfg["auth_code"]
    if not sender_addr or not password:
        return {"success": False, "message": "邮箱未配置，无法发送周排班邮件", "sent": 0, "skipped": 0, "errors": 0}

    if department_filter:
        departments = [department_filter]
    elif only_departments:
        departments = [d for d in only_departments if d]
    else:
        departments = _get_shift_departments()
    enabled_departments, _configured = _load_shift_email_feature_config(_get_shift_departments())
    sent = 0
    skipped = 0
    errors = 0
    details = []
    mail_sent = 0
    now_dt = datetime.now()
    jobs = []

    for dept in [d for d in departments if d]:
        week_start = target_week_start or _shift_schedule_target_week(dept, now_dt)
        if dept not in enabled_departments:
            skipped += 1
            details.append({"department": dept, "status": "skipped", "message": "本科室未启用排班邮件功能"})
            continue
        if not force and _shift_schedule_email_sent(dept, week_start):
            skipped += 1
            details.append({"department": dept, "status": "skipped", "message": "本周已发送"})
            continue

        config = _get_shift_config_recipients(dept)
        leaders = _get_shift_dept_leader_recipients(dept)
        if not _shift_recipient_units(config, leaders):
            skipped += 1
            details.append({"department": dept, "status": "skipped", "message": "未配置有效收件人或领导邮箱"})
            continue

        try:
            report = build_week_schedule_report(dept, week_start)
            jobs.append({
                "department": dept,
                "send_weekday": _get_shift_email_send_weekday(dept),
                "report": report,
                "config_recipients": config,
                "leaders": leaders,
            })
        except Exception as e:
            errors += 1
            logger.error("[ShiftScheduleEmail] %s 生成排班报表失败: %s", dept, e)
            details.append({"department": dept, "status": "error", "message": str(e)[:200]})

    buckets = _collect_shift_email_send_buckets(jobs)
    if not buckets and jobs:
        for job in jobs:
            skipped += 1
            details.append({"department": job["department"], "status": "skipped", "message": "无法归入发送批次"})

    for bucket in buckets.values():
        to_emails = sorted(bucket["to_emails"])
        cc_emails = sorted(bucket["cc_emails"])
        reports = bucket["reports"]
        unit = bucket["unit"]
        if not reports:
            continue
        if not to_emails:
            for dept in bucket["departments"]:
                skipped += 1
                details.append({
                    "department": dept,
                    "status": "skipped",
                    "message": "该单位未配置排班表收件人（管理人员仅抄送，不能单独作为收件人）",
                })
            continue

        subject = _build_merged_shift_schedule_subject(reports, unit)
        attachments = [
            AttachmentItem(
                filename=report["filename"],
                content_base64=base64.b64encode(report["excel_bytes"]).decode("utf-8"),
            )
            for report in reports
        ]
        body = (
            _build_shift_schedule_email_body(reports[0])
            if len(reports) == 1
            else _build_merged_shift_schedule_body(reports, unit)
        )
        msg = _build_email_message(sender_addr, to_emails, cc_emails, subject, body, "html", attachments)
        all_recipients = list(set(to_emails + cc_emails))
        try:
            success_count, failures = _smtp_send_batch(sender_addr, password, [(all_recipients, msg)])
            if success_count:
                mail_sent += 1
                log_msg = (
                    f"已向{unit}发送 {len(reports)} 个科室排班表，"
                    f"收件人 {len(to_emails)} 人，抄送 {len(cc_emails)} 人"
                )
                recipient_total = len(all_recipients)
                for report in reports:
                    sent += 1
                    _record_shift_schedule_email_log(
                        report["department"],
                        report["week_start"],
                        report["week_end"],
                        trigger_label,
                        recipient_total,
                        "ok",
                        log_msg,
                    )
                    details.append({
                        "department": report["department"],
                        "status": "ok",
                        "recipientCount": len(to_emails),
                        "ccCount": len(cc_emails),
                        "unit": unit,
                        "merged": len(reports) > 1,
                    })
            else:
                errors += len(reports)
                msg_text = "；".join(failures) if failures else "SMTP 未返回成功"
                for report in reports:
                    _record_shift_schedule_email_log(
                        report["department"],
                        report["week_start"],
                        report["week_end"],
                        trigger_label,
                        len(all_recipients),
                        "error",
                        msg_text,
                    )
                    details.append({
                        "department": report["department"],
                        "status": "error",
                        "message": msg_text[:200],
                        "unit": unit,
                    })
        except Exception as e:
            errors += len(reports)
            logger.error("[ShiftScheduleEmail] 合并发送失败 unit=%s: %s", unit, e)
            for report in reports:
                details.append({
                    "department": report["department"],
                    "status": "error",
                    "message": str(e)[:200],
                    "unit": unit,
                })

    return {
        "success": errors == 0,
        "message": (
            f"周排班邮件发送完成：成功 {sent} 个科室（{mail_sent} 封合并邮件），"
            f"跳过 {skipped} 个科室，失败 {errors} 个科室"
        ),
        "sent": sent,
        "skipped": skipped,
        "errors": errors,
        "mailCount": mail_sent,
        "details": details,
    }


@router.post("/run-shift-schedule-email")
async def run_shift_schedule_email_api(
    current_user: str = Query(...),
    week_date: Optional[str] = Query(None, description="指定日期所属的周六-周五排班周"),
    department: Optional[str] = Query(None, description="只发送指定科室，留空则全部科室"),
    force: bool = Query(False, description="是否忽略已发送记录强制发送"),
):
    scoped_department = _resolve_shift_schedule_email_scope(current_user, department)
    target_week_start = None
    if week_date:
        from routers.shift_schedule import _parse_iso_date, _week_range_for_send_day, _get_shift_email_send_weekday
        anchor = _parse_iso_date(week_date)
        if not anchor:
            raise HTTPException(status_code=400, detail="week_date 格式应为 YYYY-MM-DD")
        send_wd = _get_shift_email_send_weekday(scoped_department or department or "")
        target_week_start, _ = _week_range_for_send_day(anchor, send_wd)
    result = await run_shift_schedule_email_once(
        "手动触发周排班邮件",
        target_week_start=target_week_start,
        department_filter=scoped_department,
        force=force,
    )
    return result


@router.get("/shift-schedule-email-sent-weeks")
async def get_shift_schedule_email_sent_weeks_api(
    current_user: str = Query(...),
    department: str = Query(...),
    start_date: str = Query(..., description="修改日期范围起始 YYYY-MM-DD"),
    end_date: str = Query(..., description="修改日期范围结束 YYYY-MM-DD"),
):
    scoped_department = _resolve_shift_schedule_email_scope(current_user, department)
    if not scoped_department:
        raise HTTPException(status_code=400, detail="请指定科室")
    from routers.shift_schedule import _parse_iso_date, _week_saturday_range
    start = _parse_iso_date(start_date)
    end = _parse_iso_date(end_date)
    if not start or not end:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")
    if start > end:
        start, end = end, start
    _ensure_shift_schedule_email_log_table()
    rows = db.execute_query(
        "SELECT week_start, week_end, MAX(sent_at) AS sent_at "
        "FROM shift_schedule_email_log "
        "WHERE department = %s AND status = 'ok' AND week_end >= %s AND week_start <= %s "
        "GROUP BY week_start, week_end ORDER BY week_start",
        (scoped_department, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")),
    )
    weeks = []
    for r in rows or []:
        ws = r.get("week_start")
        we = r.get("week_end")
        ws_date = ws if isinstance(ws, date) else _parse_iso_date(str(ws)[:10])
        we_date = we if isinstance(we, date) else _parse_iso_date(str(we)[:10])
        if not ws_date or not we_date:
            continue
        weeks.append({
            "weekStart": ws_date.strftime("%Y-%m-%d"),
            "weekEnd": we_date.strftime("%Y-%m-%d"),
            "sentAt": str(r.get("sent_at") or ""),
        })
    return {
        "success": True,
        "department": scoped_department,
        "hasSent": bool(weeks),
        "weeks": weeks,
    }


async def shift_schedule_email_background_loop():
    """按各科室配置的星期几 17:00 自动发送对应周期的排班邮件。"""
    from routers.shift_schedule import _get_shift_departments, _get_shift_email_send_weekday, _load_shift_email_feature_config

    logger.info("[ShiftScheduleEmail] 周排班自动邮件后台任务已启动")
    print("[System] 周排班自动邮件后台任务已启动")
    last_triggered = set()
    weekday_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    while True:
        try:
            await asyncio.sleep(SHIFT_SCHEDULE_SEND_CHECK_SECONDS)
            now = datetime.now()
            if now.hour != SHIFT_SCHEDULE_SEND_HOUR or now.minute > 1:
                continue
            enabled_departments, _configured = _load_shift_email_feature_config(_get_shift_departments())
            due_departments = [
                dept for dept in enabled_departments
                if _get_shift_email_send_weekday(dept) == now.weekday()
            ]
            if not due_departments:
                continue
            run_key = f"{now.strftime('%Y-%m-%d')}|shift-email-batch"
            if run_key in last_triggered:
                continue
            last_triggered.add(run_key)
            if len(last_triggered) > 200:
                last_triggered = set(sorted(last_triggered)[-100:])
            send_wd = now.weekday()
            label = weekday_labels[send_wd] if 0 <= send_wd <= 6 else "周"
            await run_shift_schedule_email_once(
                f"{label}17:00自动发送",
                only_departments=due_departments,
            )
        except Exception as e:
            logger.error("[ShiftScheduleEmail] 循环异常: %s", e)
            await asyncio.sleep(300)


# ==================== 管理人员待办邮件提醒 ====================

TODO_REMINDER_THRESHOLD = 10
TODO_REMINDER_INTERVAL_DAYS = 3
TODO_REMINDER_CHECK_SECONDS = TODO_REMINDER_INTERVAL_DAYS * 24 * 3600


def _is_todo_reminder_role(jb: str) -> bool:
    """需要待办提醒的管理角色：经理/副经理/主任/主任责/副主任/班组长/组长。"""
    try:
        from routers.approvers import _jb_match
        return (
            _jb_match(jb, "部长")
            or _jb_match(jb, "副部长")
            or _jb_match(jb, "主任")
            or _jb_match(jb, "副主任")
            or _jb_match(jb, "组长")
        )
    except Exception:
        j = (jb or "").strip()
        return any(k in j for k in ("经理", "主任", "主任责", "副主任", "班组长", "组长"))


def _ensure_todo_reminder_table():
    try:
        db.execute_update(
            """
            CREATE TABLE IF NOT EXISTS todo_email_reminder_log (
                recipient_name VARCHAR(50) PRIMARY KEY,
                last_sent_at DATETIME NULL,
                last_todo_count INT DEFAULT 0,
                last_error VARCHAR(500) DEFAULT '',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='待办事项邮件提醒发送记录'
            """,
            (),
        )
    except Exception as e:
        logger.warning("[TodoReminder] 建表失败: %s", e)


def _fmt_todo_dt(v) -> str:
    if not v:
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v)[:19]


def _append_todo(items: List[Dict], type_: str, applicant: str, description: str, apply_time=None):
    items.append({
        "type": type_,
        "applicant": (applicant or "").strip() or "-",
        "description": (description or "").strip(),
        "applyTime": _fmt_todo_dt(apply_time),
    })


def _query_manager_todos(name: str) -> List[Dict]:
    """直接汇总首页中管理人员需要处理的 OA 待办明细。"""
    n = (name or "").strip()
    if not n:
        return []
    items: List[Dict] = []

    # 请假审批
    rows = db.execute_query(
        """
        SELECT xm, qjfs, timefrom, timeto, qjtime, qjzt
        FROM qj
        WHERE (qjzt = 1 AND spr = %s) OR (qjzt = 3 AND spr2 = %s)
        ORDER BY qjtime DESC
        """,
        (n, n),
    ) or []
    for r in rows:
        level = "一级审批" if int(r.get("qjzt") or 0) == 1 else "二级审批"
        _append_todo(
            items,
            "请假审批",
            r.get("xm"),
            f"{r.get('qjfs') or '请假'}，{_fmt_todo_dt(r.get('timefrom'))} 至 {_fmt_todo_dt(r.get('timeto'))}，{level}",
            r.get("qjtime"),
        )

    # 加班审批
    rows = list(db.execute_query(
        """
        SELECT xm, jb, timedate, timefrom, timeto, jiabantime, jiabanzt, hx
        FROM jiaban
        WHERE (jiabanzt IN (0, 1) AND spr = %s) OR (jiabanzt = 3 AND spr2 = %s)
        ORDER BY jiabantime DESC
        """,
        (n, n),
    ) or [])
    try:
        dakaman = _get_dakaman_for_todo()
        if dakaman and dakaman == n:
            rows.extend(db.execute_query(
                """
                SELECT xm, jb, timedate, timefrom, timeto, jiabantime, jiabanzt, hx
                FROM jiaban
                WHERE jiabanzt = 5
                ORDER BY jiabantime DESC
                """,
                (),
            ) or [])
    except Exception:
        pass
    for r in rows:
        zt = int(r.get("jiabanzt") or 0)
        level = "打卡管理员审批" if zt == 5 else ("二级审批" if zt == 3 else "一级审批")
        _append_todo(
            items,
            "加班审批",
            r.get("xm"),
            f"{r.get('jb') or '加班'}，{str(r.get('timedate') or '')[:10]} {_fmt_todo_dt(r.get('timefrom'))[-8:]} 至 {_fmt_todo_dt(r.get('timeto'))[-8:]}，换休票：{r.get('hx') or '否'}，{level}",
            r.get("jiabantime"),
        )

    # 公出审批
    rows = db.execute_query(
        """
        SELECT gcr, gclx, gcdd, yjcfsj, yjfhsj, szrzt, bldzt, sqsj
        FROM gcsqb
        WHERE (szrzt = 1 AND szr = %s) OR (szrzt = 2 AND bldzt = 1 AND bld = %s)
        ORDER BY sqsj DESC
        """,
        (n, n),
    ) or []
    for r in rows:
        level = "室主任审批" if int(r.get("szrzt") or 0) == 1 else "部领导审批"
        _append_todo(
            items,
            "公出审批",
            r.get("gcr"),
            f"{r.get('gclx') or '公出'}，{r.get('gcdd') or ''}，{_fmt_todo_dt(r.get('yjcfsj'))} 至 {_fmt_todo_dt(r.get('yjfhsj'))}，{level}",
            r.get("sqsj"),
        )

    # 公出节假日换休票审批
    rows = db.execute_query(
        """
        SELECT xm, date_from, date_to, days, hxp_count, status, apply_time
        FROM holiday_exchange
        WHERE (status = 0 AND spr = %s) OR (status = 1 AND spr2 = %s)
        ORDER BY apply_time DESC
        """,
        (n, n),
    ) or []
    for r in rows:
        level = "一级审批" if int(r.get("status") or 0) == 0 else "二级审批"
        _append_todo(
            items,
            "节假日换休票审批",
            r.get("xm"),
            f"{r.get('date_from') or ''} 至 {r.get('date_to') or ''}，{r.get('days') or 0}天，{r.get('hxp_count') or 0}张，{level}",
            r.get("apply_time"),
        )

    # 换休票管理审批
    rows = db.execute_query(
        """
        SELECT applicant, action, amount, ly, names_json, apply_time
        FROM hxp_approval
        WHERE approver = %s AND status = 0
        ORDER BY apply_time DESC
        """,
        (n,),
    ) or []
    for r in rows:
        try:
            names = json.loads(r.get("names_json") or "[]")
        except Exception:
            names = []
        action_text = "增加" if (r.get("action") or "") == "add" else "减少"
        target_text = "、".join(names[:5]) + ("等" if len(names) > 5 else "")
        _append_todo(
            items,
            "换休票管理审批",
            r.get("applicant"),
            f"为{len(names)}人{action_text}{r.get('amount') or 0}张换休票（{target_text or '未列明人员'}），原因：{r.get('ly') or ''}",
            r.get("apply_time"),
        )

    # 用印审批
    rows = db.execute_query(
        """
        SELECT applicant, seal_type, reason, apply_time
        FROM seal_apply
        WHERE approver = %s AND status = 0
        ORDER BY apply_time DESC
        """,
        (n,),
    ) or []
    for r in rows:
        _append_todo(
            items,
            "用印审批",
            r.get("applicant"),
            f"{r.get('seal_type') or '用印'}，事由：{r.get('reason') or ''}",
            r.get("apply_time"),
        )

    # 匿名意见待查看（status=0 视为未读；打开信箱后会标记已读）
    rows = db.execute_query(
        """
        SELECT content, created_at
        FROM feedback_leader_inbox
        WHERE target_leader = %s AND COALESCE(status, 0) = 0
        ORDER BY created_at DESC
        """,
        (n,),
    ) or []
    for r in rows:
        desc = (r.get("content") or "").strip()
        _append_todo(items, "匿名意见待查看", "意见与建议", desc[:120], r.get("created_at"))

    # 换休票入账（未读）
    rows = db.execute_query(
        """
        SELECT id, sl, sj, ly
        FROM hxp
        WHERE name = %s AND (is_read IS NULL OR is_read = 0) AND sl > 0
        ORDER BY sj DESC
        """,
        (n,),
    ) or []
    for r in rows:
        _append_todo(
            items,
            "换休票入账",
            "本人",
            f"获得 {r.get('sl') or 0} 张换休票（来源：{(r.get('ly') or '').strip() or '系统自动'}）",
            r.get("sj"),
        )

    # 待用印（已通过审批但尚未标记已用印）
    rows = db.execute_query(
        """
        SELECT seal_type, reason, apply_time, approve_time
        FROM seal_apply
        WHERE applicant = %s AND status = 1 AND COALESCE(used_stamp, 0) = 0
        ORDER BY approve_time DESC, apply_time DESC
        """,
        (n,),
    ) or []
    for r in rows:
        _append_todo(
            items,
            "待用印",
            "本人",
            f"用印申请已通过（{r.get('seal_type') or '部门公章'}），请完成盖章后标记「已用印」",
            r.get("approve_time") or r.get("apply_time"),
        )

    # 吐槽问题处理（被指派且尚未解决）
    rows = db.execute_query(
        """
        SELECT content, assigned_by, assigned_at, created_at
        FROM feedback_wall
        WHERE status = 1 AND assignee = %s AND COALESCE(resolved, 0) <> 3
        ORDER BY assigned_at DESC, created_at DESC
        """,
        (n,),
    ) or []
    for r in rows:
        content = (r.get("content") or "").strip()
        assigner = (r.get("assigned_by") or "").strip()
        _append_todo(
            items,
            "吐槽问题处理",
            f"指派人：{assigner}" if assigner else "吐槽墙",
            f"请处理：{content[:120]}",
            r.get("assigned_at") or r.get("created_at"),
        )

    # 吐槽墙待审核 & 系统建议待回复（仅 admin1）
    try:
        admin1 = _get_admin1()
        if admin1 and n == admin1:
            wall_pending_rows = db.execute_query(
                "SELECT id, content, created_at FROM feedback_wall WHERE status = 0 ORDER BY created_at DESC"
            ) or []
            if wall_pending_rows:
                _append_todo(
                    items,
                    "吐槽墙待审核",
                    "意见与建议",
                    f"您有 {len(wall_pending_rows)} 条吐槽待审核上墙",
                    wall_pending_rows[0].get("created_at") if len(wall_pending_rows) == 1 else None,
                )

            sys_pending_rows = db.execute_query(
                "SELECT id, content, created_at FROM feedback_system WHERE status != 1 ORDER BY created_at DESC"
            ) or []
            if sys_pending_rows:
                _append_todo(
                    items,
                    "系统建议待回复",
                    "意见与建议",
                    f"您有 {len(sys_pending_rows)} 条系统功能建议待回复",
                    sys_pending_rows[0].get("created_at") if len(sys_pending_rows) == 1 else None,
                )
    except Exception:
        pass

    return sorted(items, key=lambda x: x.get("applyTime") or "", reverse=True)


def _get_dakaman_for_todo() -> str:
    try:
        rows = db.execute_query("SELECT dakaman FROM webconfig WHERE id = %s LIMIT 1", ("1",))
        return (rows[0].get("dakaman") or "").strip() if rows else ""
    except Exception:
        return ""


def _build_todo_reminder_body(name: str, count: int, todos: List[Dict]) -> str:
    lines = [
        f"{name}您好",
        "",
        "我是工艺部智能办公助手。",
        "",
        f"系统检测到您当前有 {count} 条待办事项未处理，已超过 {TODO_REMINDER_THRESHOLD} 条，请登录 OA 系统及时处理。",
        "",
        "待办明细：",
    ]
    for idx, item in enumerate(todos, 1):
        time_part = f"；申请时间：{item['applyTime']}" if item.get("applyTime") else ""
        lines.append(
            f"{idx}. 【{item.get('type') or '待办'}】{item.get('applicant') or '-'}：{item.get('description') or ''}{time_part}"
        )
    lines.extend([
        "",
        "系统地址：http://10.42.60.230",
        "",
        f"本提醒每 {TODO_REMINDER_INTERVAL_DAYS} 天检查一次；如待办数仍超过 {TODO_REMINDER_THRESHOLD} 条，将继续提醒。",
        "此邮件由系统自动发送，请勿直接回复。",
    ])
    return "\n".join(lines)


def _parse_last_sent_at(v) -> Optional[datetime]:
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.strptime(str(v)[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _should_send_todo_reminder(name: str, now: datetime) -> bool:
    _ensure_todo_reminder_table()
    rows = db.execute_query(
        "SELECT last_sent_at FROM todo_email_reminder_log WHERE recipient_name = %s LIMIT 1",
        ((name or "").strip(),),
    ) or []
    if not rows:
        return True
    last = _parse_last_sent_at(rows[0].get("last_sent_at"))
    if not last:
        return True
    return now - last >= timedelta(days=TODO_REMINDER_INTERVAL_DAYS)


def _record_todo_reminder_result(name: str, sent_at: Optional[datetime], count: int, error: str = ""):
    _ensure_todo_reminder_table()
    db.execute_update(
        """
        INSERT INTO todo_email_reminder_log (recipient_name, last_sent_at, last_todo_count, last_error, updated_at)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          last_sent_at = COALESCE(VALUES(last_sent_at), last_sent_at),
          last_todo_count = VALUES(last_todo_count),
          last_error = VALUES(last_error),
          updated_at = VALUES(updated_at)
        """,
        (
            (name or "").strip(),
            sent_at.strftime("%Y-%m-%d %H:%M:%S") if sent_at else None,
            int(count or 0),
            (error or "")[:500],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )


def _smtp_send_todo_messages(sender: str, password: str, messages: List[Dict]):
    """单次 SMTP 连接发送待办提醒，返回成功的用户与失败信息。"""
    smtp_obj = None
    sent = []
    failures = []
    try:
        smtp_obj = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT_SSL, timeout=30)
        smtp_obj.login(sender, password)
        for item in messages:
            try:
                smtp_obj.sendmail(sender, item["recipients"], item["message"].as_string())
                sent.append({"name": item["name"], "count": item["count"]})
            except Exception as e:
                failures.append({"name": item["name"], "error": str(e)[:200]})
                logger.warning("[TodoReminder] 邮件发送失败 -> %s: %s", item["name"], e)
    finally:
        if smtp_obj:
            try:
                smtp_obj.quit()
            except Exception:
                pass
    return sent, failures


def _get_todo_reminder_recipients() -> List[Dict]:
    rows = db.execute_query(
        """
        SELECT name, lsys, jb, enterprise_email
        FROM yggl
        WHERE COALESCE(zaizhi,0)=0
          AND name IS NOT NULL AND TRIM(name) != ''
          AND enterprise_email IS NOT NULL AND TRIM(enterprise_email) != ''
        ORDER BY lsys, jb, name
        """,
        (),
    ) or []
    result = []
    for r in rows:
        jb = (r.get("jb") or "").strip()
        if _is_todo_reminder_role(jb):
            result.append({
                "name": (r.get("name") or "").strip(),
                "dept": (r.get("lsys") or "").strip(),
                "jb": jb,
                "email": (r.get("enterprise_email") or "").strip(),
            })
    return result


async def run_todo_email_reminder_once() -> dict:
    """扫描管理人员待办，超过阈值且距离上次提醒已满 3 天则发送邮件。"""
    lock_name = "oa_todo_email_reminder_run"
    lock_conn = _try_acquire_mysql_lock(lock_name, "TodoReminder")
    if not lock_conn:
        return {"checked": 0, "sent": 0, "message": "已有其他进程正在发送待办提醒，本进程已跳过"}
    try:
        return await _run_todo_email_reminder_once_locked()
    finally:
        _release_mysql_lock(lock_conn, lock_name, "TodoReminder")


async def _run_todo_email_reminder_once_locked() -> dict:
    cfg = _get_email_config()
    sender_addr = cfg["address"]
    password = cfg["auth_code"]
    email_configured = bool(sender_addr and password)

    now = datetime.now()
    recipients = _get_todo_reminder_recipients()
    checked = 0
    messages = []
    skipped_over_threshold = 0
    # 调试模式：仅展示扫描结果，不发邮件
    debug_over_threshold = []

    for user in recipients:
        name = user["name"]
        if not name:
            continue
        checked += 1
        todos = _query_manager_todos(name)
        count = len(todos)
        if count <= TODO_REMINDER_THRESHOLD:
            continue
        if not _should_send_todo_reminder(name, now):
            skipped_over_threshold += 1
            continue
        if email_configured:
            subject = f"您有 {count} 条 OA 待办事项待处理（系统自动提醒）"
            body = _build_todo_reminder_body(name, count, todos)
            msg = _build_email_message(sender_addr, [user["email"]], [], subject, body, "plain")
            messages.append({
                "name": name,
                "count": count,
                "recipients": [user["email"]],
                "message": msg,
            })
        else:
            debug_over_threshold.append({"name": name, "count": count, "email": user.get("email", "")})

    if not messages:
        return {
            "checked": checked,
            "sent": 0,
            "skippedOverThreshold": skipped_over_threshold,
            "message": "邮箱未配置（仅展示扫描结果）" if not email_configured else "无需要发送的待办提醒",
            "_debugOverThreshold": debug_over_threshold,
        }

    try:
        sent, failures = _smtp_send_todo_messages(sender_addr, password, messages)
        sent_at = datetime.now()
        for item in sent:
            _record_todo_reminder_result(item["name"], sent_at, item["count"])
        for item in failures:
            _record_todo_reminder_result(item["name"], None, 0, item["error"])
        if failures:
            logger.warning("[TodoReminder] 部分待办提醒发送失败: %s", failures[:3])
        logger.info("[TodoReminder] 已发送 %s 封待办提醒，检查 %s 人", len(sent), checked)
        return {
            "checked": checked,
            "sent": len(sent),
            "failures": failures,
            "message": f"已发送 {len(sent)} 封待办提醒",
        }
    except Exception as e:
        logger.error("[TodoReminder] 发送待办提醒失败: %s", e)
        for item in messages:
            _record_todo_reminder_result(item["name"], None, item["count"], str(e))
        return {"checked": checked, "sent": 0, "error": str(e)}


async def todo_reminder_background_loop():
    """后台循环：每 3 天检查一次，单人 3 天内最多提醒一次。"""
    logger.info("[TodoReminder] 管理人员待办邮件提醒后台任务已启动")
    print("[System] 管理人员待办邮件提醒后台任务已启动")
    await asyncio.sleep(300)
    while True:
        try:
            await run_todo_email_reminder_once()
        except Exception as e:
            logger.error("[TodoReminder] 循环异常: %s", e)
        await asyncio.sleep(TODO_REMINDER_CHECK_SECONDS)
