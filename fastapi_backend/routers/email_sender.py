# -*- coding: utf-8 -*-
"""
邮件发送 API - 仅系统管理员 (webconfig.admin1) 可使用
基于网易企业邮箱 SMTP SSL 发送
支持：抄送(CC)、附件、考勤异常提醒自动邮件
"""
import smtplib
import logging
import base64
from collections import defaultdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from typing import Optional, List
from io import BytesIO

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


def _build_attendance_reminder_body(month: int, summary_block: str) -> str:
    notice = (
        "请各位同事及时处理考勤异常；班组长、主任、部门管理人员可以看到所属组织异常情况，请提醒和监督。"
    )
    return (
        "各位领导同事您好\n\n"
        "我是工艺部智能办公助手\n\n"
        f"请以下人员登录 http://10.42.60.230 处理{month}月考勤异常。\n\n"
        f"{summary_block}\n\n"
        f"{notice}\n\n"
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


@router.post("/send-attendance-reminder")
async def send_attendance_reminder(req: AttendanceReminderRequest):
    """
    一键发送考勤异常提醒邮件。
    自动获取指定月份异常数据，生成邮件内容和附件，发送给相关人员。
    test_mode=True 时仅发送到 test_recipients（未传或为空时默认 hsx@hec-china.com）。
    """
    _require_admin(req.current_user)

    cfg = _get_email_config()
    sender_addr = cfg["address"]
    password = cfg["auth_code"]
    if not sender_addr or not password:
        raise HTTPException(status_code=400, detail="邮箱未配置，请先配置发件邮箱")

    from routers.suggestions import get_attendance_exception_keys

    exception_keys = get_attendance_exception_keys(req.year, req.month, include_buban=True)
    if not exception_keys:
        return {"success": True, "message": f"{req.year}年{req.month}月无考勤异常，无需发送提醒", "preview": None}

    pair_counts = _pair_counts_from_exception_keys(exception_keys)
    email_map = _get_employee_email_map()
    _rec_info, recipient_emails, no_email_names, person_count = _recipient_rollups_from_pairs(pair_counts, email_map)
    recipient_emails = list(dict.fromkeys(recipient_emails))

    summary_block = _format_exception_summary_by_department(pair_counts)
    body_text = _build_attendance_reminder_body(req.month, summary_block)

    subject = f"请处理{req.month}月考勤异常{ATTENDANCE_REMINDER_SUBJECT_SUFFIX}"

    try:
        excel_bytes = _generate_exception_excel(req.year, req.month)
        excel_b64 = base64.b64encode(excel_bytes).decode("utf-8")
        attachment_filename = f"考勤异常表_{req.year}年{req.month}月.xlsx"
    except Exception as e:
        logger.error(f"生成考勤异常 Excel 附件失败: {e}")
        excel_b64 = None
        attachment_filename = None

    attachments_list = []
    if excel_b64 and attachment_filename:
        attachments_list.append(AttachmentItem(filename=attachment_filename, content_base64=excel_b64))

    cc_list = [addr.strip() for addr in (req.cc or []) if addr.strip()]

    if req.test_mode:
        actual_recipients = _normalize_test_recipients(req.test_recipients)
        test_note = f"\n\n---\n[测试模式] 实际发送到: {', '.join(actual_recipients)}"
        test_note += f"\n原始收件人共 {len(recipient_emails)} 人: {', '.join(recipient_emails[:10])}{'...' if len(recipient_emails) > 10 else ''}"
        if no_email_names:
            test_note += f"\n未找到邮箱的人员: {', '.join(no_email_names)}"
        body_text += test_note
    else:
        actual_recipients = recipient_emails
        if not actual_recipients:
            raise HTTPException(status_code=400, detail="所有异常人员均未配置企业邮箱，无法发送")

    message = _build_email_message(
        sender_addr, actual_recipients, cc_list, subject, body_text, "plain", attachments_list
    )

    all_send_to = list(set(actual_recipients + cc_list))
    _smtp_send(sender_addr, password, all_send_to, message)

    result = {
        "success": True,
        "message": f"考勤异常提醒已发送！共 {person_count} 人异常，发送给 {len(actual_recipients)} 位收件人" +
                   (f"（测试模式：{', '.join(actual_recipients)}）" if req.test_mode else ""),
        "preview": {
            "subject": subject,
            "body": body_text,
            "recipients_count": len(actual_recipients),
            "cc_count": len(cc_list),
            "exception_persons": person_count,
            "total_exception_days": len(exception_keys),
            "has_attachment": bool(attachments_list),
            "no_email_names": no_email_names,
        },
    }
    return result


@router.post("/preview-attendance-reminder")
async def preview_attendance_reminder(req: AttendanceReminderRequest):
    """预览考勤异常提醒邮件内容（不实际发送）"""
    _require_admin(req.current_user)

    from routers.suggestions import get_attendance_exception_keys

    exception_keys = get_attendance_exception_keys(req.year, req.month, include_buban=True)
    if not exception_keys:
        return {
            "success": True,
            "has_exceptions": False,
            "message": f"{req.year}年{req.month}月无考勤异常",
        }

    pair_counts = _pair_counts_from_exception_keys(exception_keys)
    email_map = _get_employee_email_map()
    recipients_info, _recipient_emails, no_email_names, person_count = _recipient_rollups_from_pairs(
        pair_counts, email_map
    )

    summary_block = _format_exception_summary_by_department(pair_counts)
    body_text = _build_attendance_reminder_body(req.month, summary_block)

    subject = f"请处理{req.month}月考勤异常{ATTENDANCE_REMINDER_SUBJECT_SUFFIX}"

    return {
        "success": True,
        "has_exceptions": True,
        "subject": subject,
        "body": body_text,
        "recipients": recipients_info,
        "total_persons": person_count,
        "total_days": len(exception_keys),
        "no_email_names": no_email_names,
        "no_email_count": len(no_email_names),
        "has_email_count": person_count - len(no_email_names),
    }
