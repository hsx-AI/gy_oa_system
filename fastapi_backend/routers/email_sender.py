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
from collections import defaultdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from typing import Optional, List
from io import BytesIO
from datetime import datetime

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
                    and entry.get("personal_sent", 0) > 0):
                return True
    except Exception as e:
        logger.warning(f"[AutoReminder] 检查已发送记录失败: {e}")
    return False


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
                await _execute_auto_send(
                    target_year, target_month, f"每月{day_label} {h}:{m:02d} · {month_label}考勤"
                )
        except Exception as e:
            logger.error(f"[AutoReminder] 循环异常: {e}")
            await asyncio.sleep(300)
