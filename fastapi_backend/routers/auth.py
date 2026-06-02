# -*- coding: utf-8 -*-
"""
登录认证API路由
"""
import math
import logging
from fastapi import APIRouter, Query
from pydantic import BaseModel
from database import db, db_demo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


def _format_entry_date(value) -> str:
    """入厂时间展示：精确到月份（YYYY-MM）；仅有年份时显示 YYYY。"""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        raw = value.strftime("%Y-%m-%d")
    else:
        raw = str(value).strip()[:10]
    if not raw:
        return ""
    if len(raw) >= 7 and raw[4] == "-":
        return raw[:7]
    if len(raw) >= 4 and raw[:4].isdigit():
        return raw[:4]
    return raw


def _parse_entry_date_for_seniority(value):
    """解析入厂日期用于工龄（精确到日；仅 YYYY-MM 时按当月 1 日）。"""
    from datetime import date as dt_date, datetime as dt_datetime

    if value is None:
        return None
    if isinstance(value, dt_date):
        return value
    if isinstance(value, dt_datetime):
        return value.date()
    if hasattr(value, "year") and hasattr(value, "month"):
        try:
            day = int(getattr(value, "day", 1) or 1)
            return dt_date(int(value.year), int(value.month), day)
        except (TypeError, ValueError):
            return None
    text = str(value).strip()[:10]
    if not text:
        return None
    try:
        if len(text) >= 10 and text[4] == "-":
            return dt_date.fromisoformat(text[:10])
        if len(text) >= 7 and text[4] == "-":
            y, m = int(text[:4]), int(text[5:7])
            return dt_date(y, m, 1)
        if len(text) >= 4 and text[:4].isdigit():
            return dt_date(int(text[:4]), 1, 1)
    except (TypeError, ValueError):
        return None
    return None


def _service_months(entry, today) -> int:
    """入厂至今完整工龄月数（未满月不计入下一月）。"""
    months = (today.year - entry.year) * 12 + (today.month - entry.month)
    if today.day < entry.day:
        months -= 1
    return max(0, months)


def _paid_leave_entitlement_by_months(service_months: int) -> int:
    """工龄对应带薪年休假应得天数：<1年0；1~9年5；10~19年10；20年及以上15。"""
    if service_months < 12:
        return 0
    if service_months < 120:
        return 5
    if service_months < 240:
        return 10
    return 15


class LoginRequest(BaseModel):
    """登录请求模型"""
    admin: str  # 用户名（姓名）
    password: str  # 密码


class LoginResponse(BaseModel):
    """登录响应模型"""
    success: bool
    message: str = ""
    data: dict = {}


class SetLoginStatusRequest(BaseModel):
    """设置登录状态（已读首次登录介绍）"""
    name: str  # 员工姓名


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录接口
    
    验证用户名和密码，返回用户信息
    """
    
    try:
        # 验证参数
        if not request.admin or not request.password:
            return LoginResponse(
                success=False,
                message="请输入用户名和密码"
            )
        
        # 先查是否存在该用户（在职），再校验密码，便于区分「无此用户」与「密码错误」
        check_user_sql = "SELECT name, `pass`, lsys, jb, gh, xbie, denglu_zt, gx_gt FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1"
        try:
            user_rows = db.execute_query(check_user_sql, (request.admin,))
        except Exception:
            check_user_sql = "SELECT name, `pass`, lsys, jb, gh, xbie FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1"
            user_rows = db.execute_query(check_user_sql, (request.admin,))
        if not user_rows or len(user_rows) == 0:
            return LoginResponse(
                success=False,
                message="没有该用户，请检查用户名或联系管理员"
            )
        user_data = user_rows[0]
        db_pass = (user_data.get("pass") or "").strip()
        if db_pass != request.password:
            return LoginResponse(
                success=False,
                message="密码错误，请重新输入"
            )
        # 密码正确，构建返回数据；denglu_zt 为空表示未看过首次登录介绍
        denglu_zt = user_data.get("denglu_zt")
        show_intro = denglu_zt is None or (isinstance(denglu_zt, str) and denglu_zt.strip() == "")

        # 查询未读通知：gx_gt 存最后已读通知 ID，NULL/空/'0' 视为 0
        gx_gt_raw = user_data.get("gx_gt")
        try:
            last_read_id = int(gx_gt_raw) if gx_gt_raw and str(gx_gt_raw).strip() not in ("", "0") else 0
        except (ValueError, TypeError):
            last_read_id = 0

        unread_notifications = []
        try:
            unread_rows = db.execute_query(
                "SELECT id, content, publish_time FROM notifications WHERE id > %s ORDER BY id ASC",
                (last_read_id,),
            )
            for nr in (unread_rows or []):
                unread_notifications.append({
                    "id": nr["id"],
                    "content": (nr.get("content") or "").strip(),
                    "time": str(nr.get("publish_time") or ""),
                })
        except Exception:
            pass

        user_info = {
            "name": (user_data.get("name") or "").strip(),
            "dept": (user_data.get("lsys") or "").strip(),
            "jb": (user_data.get("jb") or "").strip(),
            "gh": (user_data.get("gh") or "").strip(),
            "xbie": (user_data.get("xbie") or "").strip(),
            "showIntro": show_intro,
            "unreadNotifications": unread_notifications,
        }
        return LoginResponse(
            success=True,
            message="登录成功",
            data=user_info
        )
            
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        return LoginResponse(
            success=False,
            message=f"登录失败: {str(e)}"
        )


@router.post("/set-login-status")
async def set_login_status(req: SetLoginStatusRequest):
    """标记用户已看过首次登录介绍，更新 yggl.denglu_zt"""
    name = (req.name or "").strip()
    if not name:
        return {"success": False, "message": "姓名为空"}
    try:
        sql = "UPDATE yggl SET denglu_zt=%s WHERE name=%s AND (COALESCE(zaizhi,0)=0)"
        db.execute_update(sql, ("1", name))
        return {"success": True, "message": "已更新"}
    except Exception as e:
        if "denglu_zt" in str(e).lower() or "unknown column" in str(e).lower():
            return {"success": True, "message": "已更新"}
        logger.error(f"设置登录状态失败: {str(e)}")
        return {"success": False, "message": str(e)}


# ==================== 更新消息推送（多条历史通知） ====================

class PublishNotificationRequest(BaseModel):
    current_user: str
    content: str


class DismissNotificationRequest(BaseModel):
    name: str
    max_id: int


@router.post("/notification/publish")
async def publish_notification(req: PublishNotificationRequest):
    """管理员(admin1)发布更新通知：向 notifications 表插入一条新记录"""
    from routers.db_manager import _get_admin1
    from datetime import datetime
    name = (req.current_user or "").strip()
    admin1 = _get_admin1()
    if not admin1 or name != admin1:
        return {"success": False, "message": "仅系统管理员可发布通知"}
    content = (req.content or "").strip()
    if not content:
        return {"success": False, "message": "通知内容不能为空"}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        db.execute_update(
            "INSERT INTO notifications (content, publish_time, publisher) VALUES (%s, %s, %s)",
            (content, now, name),
        )
        return {"success": True, "message": "通知已发布，未读此通知的员工下次登录将看到弹窗"}
    except Exception as e:
        logger.error(f"发布通知失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/notification/dismiss")
async def dismiss_notification(req: DismissNotificationRequest):
    """用户关闭通知弹窗后，将 gx_gt 更新为已读的最大通知 ID"""
    name = (req.name or "").strip()
    if not name:
        return {"success": False, "message": "姓名为空"}
    try:
        db.execute_update(
            "UPDATE yggl SET gx_gt = %s WHERE name = %s AND COALESCE(zaizhi,0) = 0",
            (str(req.max_id), name),
        )
        return {"success": True}
    except Exception as e:
        logger.error(f"标记通知已读失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/notification/list")
async def list_notifications():
    """获取所有历史通知（供管理页面展示），按时间倒序"""
    try:
        rows = db.execute_query(
            "SELECT id, content, publish_time, publisher FROM notifications ORDER BY id DESC"
        )
        items = []
        for r in (rows or []):
            items.append({
                "id": r["id"],
                "content": (r.get("content") or "").strip(),
                "time": str(r.get("publish_time") or ""),
                "publisher": (r.get("publisher") or "").strip(),
            })
        return {"success": True, "items": items}
    except Exception as e:
        return {"success": True, "items": []}


@router.post("/notification/delete")
async def delete_notification(req: dict):
    """管理员删除一条通知"""
    from routers.db_manager import _get_admin1
    name = (req.get("current_user") or "").strip()
    admin1 = _get_admin1()
    if not admin1 or name != admin1:
        return {"success": False, "message": "仅系统管理员可操作"}
    nid = req.get("id")
    if not nid:
        return {"success": False, "message": "缺少通知ID"}
    try:
        db.execute_update("DELETE FROM notifications WHERE id = %s", (nid,))
        return {"success": True, "message": "已删除"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/profile")
async def get_profile(name: str = Query(..., description="员工姓名")):
    """获取员工信息：用户名、工号、科室、级别、身份证号、入厂时间、换休票总数及明细（按过期日分组）"""
    try:
        from utils.hxp_helper import compute_expire_date, parse_expire_for_sort
        sql = (
            "SELECT name, gh, lsys, jb, sfzh, rcnf FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1"
        )
        try:
            rows = db.execute_query(sql, (name,))
        except Exception:
            # 兼容无 sfzh/rcnf 列：仅查基础字段
            rows = db.execute_query(
                "SELECT name, gh, lsys, jb FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1",
                (name,),
            )
        if not rows:
            return {"success": False, "message": "用户不存在或已离职"}
        r = rows[0]
        # 换休票：从 hxp 表按 sl 加和，排除已过期
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        hxp_rows = db.execute_query(
            "SELECT id, sl, sj FROM hxp WHERE name = %s AND sl > 0", (name,)
        )
        total = 0.0
        expire_groups = {}
        for row in hxp_rows:
            try:
                sl = float(row.get("sl") or 0)
            except (TypeError, ValueError):
                sl = 0.0
            if sl <= 0:
                continue
            exp = compute_expire_date(row.get("sj"))
            if exp and exp < today:
                continue  # 已过期，不计入
            total += sl
            if exp:
                expire_groups[exp] = expire_groups.get(exp, 0.0) + sl
        details = [
            {"expireDate": k, "count": round(v, 3)}
            for k, v in sorted(expire_groups.items(), key=lambda x: parse_expire_for_sort(x[0]))
        ]
        # 换休票预扣减：正在审核中的换休/员工换休票请假所消耗的张数，从「可用」中扣除，避免多单同时审核导致扣成负数
        hxp_pending = 0.0
        try:
            pending_rows = db.execute_query(
                "SELECT COALESCE(SUM(CAST(COALESCE(hxpxh, tian * 2) AS DECIMAL(10,4))), 0) AS s FROM qj WHERE xm = %s AND qjzt IN (0, 1, 3) AND (TRIM(COALESCE(qjfs,'')) = %s OR TRIM(COALESCE(qjfs,'')) = %s)",
                (name, "换休", "员工换休票"),
            )
            if pending_rows and pending_rows[0].get("s") is not None:
                hxp_pending = float(pending_rows[0]["s"])
        except Exception as e:
            logger.debug(f"换休票预扣减查询失败: {e}")
        hxp_available = max(0.0, total - hxp_pending)
        entry_date = _format_entry_date(r.get("rcnf"))
        entry_raw_for_seniority = r.get("rcnf")
        mobile = ""
        sfzh_clean = (r.get("sfzh") or "").strip().replace(" ", "")
        if sfzh_clean:
            try:
                demo_rows = db_demo.execute_query(
                    "SELECT mobile, factory_entry_date FROM employee_info WHERE id_card = %s LIMIT 1",
                    (sfzh_clean,),
                )
                if demo_rows:
                    mobile = str(demo_rows[0].get("mobile") or "").strip()
                    fed = demo_rows[0].get("factory_entry_date")
                    if fed is not None:
                        entry_raw_for_seniority = fed
                        demo_entry = _format_entry_date(fed)
                        if demo_entry:
                            entry_date = demo_entry
            except Exception as e:
                logger.debug("demo 库 employee_info 查询失败: %s", e)
        # 带薪休假：按入厂年月精确计算工龄（月），再对应应得天数
        paid_leave_remaining = None
        paid_leave_detail = None
        try:
            from datetime import date

            entry_dt = _parse_entry_date_for_seniority(entry_raw_for_seniority)
            if entry_dt is not None:
                today = date.today()
                service_months = _service_months(entry_dt, today)
                entitlement = _paid_leave_entitlement_by_months(service_months)
                deducted = 3  # 固定高温假公休
                available = max(0, entitlement - deducted)
                current_year = today.year
                qj_rows = db.execute_query(
                    "SELECT COALESCE(SUM(CAST(tian AS DECIMAL(10,4))), 0) AS total FROM qj WHERE xm = %s AND qjzt = 4 AND YEAR(timefrom) = %s AND (TRIM(COALESCE(qjfs,'')) LIKE %s OR TRIM(COALESCE(qjfs,'')) LIKE %s OR TRIM(COALESCE(qjfs,'')) = %s OR TRIM(COALESCE(qjfs,'')) = %s)",
                    (name, current_year, "%带薪%", "%年休假%", "带薪休假", "年休假"),
                )
                used_raw = float(qj_rows[0]["total"]) if qj_rows and qj_rows[0].get("total") is not None else 0.0
                used_rounded = math.ceil(used_raw / 0.25) * 0.25
                remaining = round(max(0, available - used_rounded) * 4) / 4
                paid_leave_remaining = remaining
                paid_leave_detail = {
                    "entitlement": entitlement,
                    "deducted": deducted,
                    "used": round(used_rounded, 2),
                    "remaining": round(remaining, 2),
                    "serviceMonths": service_months,
                    "serviceYears": round(service_months / 12, 1),
                }
        except Exception as e:
            logger.debug(f"带薪休假计算失败: {e}")
        return {
            "success": True,
            "data": {
                "name": (r.get("name") or "").strip(),
                "workNo": (r.get("gh") or "").strip(),
                "department": (r.get("lsys") or "").strip(),
                "level": (r.get("jb") or "").strip(),
                "idNumber": (r.get("sfzh") or "").strip(),
                "mobile": mobile,
                "entryDate": entry_date,
                "exchangeTickets": round(hxp_available, 3),
                "exchangeTicketsTotal": round(total, 3),
                "exchangeTicketsPending": round(hxp_pending, 3),
                "exchangeTicketDetails": details,
                "paidLeaveRemaining": paid_leave_remaining,
                "paidLeaveDetail": paid_leave_detail,
            }
        }
    except Exception as e:
        logger.error(f"获取员工信息失败: {str(e)}")
        return {"success": False, "message": str(e)}


class ChangePasswordRequest(BaseModel):
    name: str
    oldPassword: str
    newPassword: str


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest):
    """修改密码"""
    try:
        if not req.newPassword or len(req.newPassword) < 4:
            return {"success": False, "message": "新密码至少4位"}
        check = db.execute_query(
            "SELECT 1 FROM yggl WHERE name=%s AND `pass`=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1",
            (req.name, req.oldPassword)
        )
        if not check:
            return {"success": False, "message": "原密码错误"}
        db.execute_update(
            "UPDATE yggl SET `pass`=%s WHERE name=%s",
            (req.newPassword, req.name)
        )
        return {"success": True, "message": "密码修改成功"}
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        return {"success": False, "message": str(e)}


# ==================== 用户配色风格 ====================

def _ensure_skin_style_column():
    """确保 yggl 表有 skin_style 列。"""
    try:
        db.execute_update("ALTER TABLE yggl ADD COLUMN skin_style VARCHAR(20) DEFAULT '' COMMENT '用户配色风格'", ())
    except Exception:
        pass


_ensure_skin_style_column()


@router.get("/user-style")
async def get_user_style(name: str = Query(..., description="用户姓名")):
    """获取用户保存的配色风格。"""
    try:
        rows = db.execute_query(
            "SELECT skin_style FROM yggl WHERE name=%s AND (COALESCE(zaizhi,0)=0) LIMIT 1",
            (name,),
        )
        style = (rows[0].get("skin_style") or "").strip() if rows else ""
        return {"success": True, "skinStyle": style}
    except Exception as e:
        logger.error(f"获取用户风格失败: {e}")
        return {"success": False, "message": str(e)}


class UserStyleRequest(BaseModel):
    name: str
    skinStyle: str


@router.post("/user-style")
async def save_user_style(req: UserStyleRequest):
    """保存用户配色风格到 yggl.skin_style。"""
    try:
        style = (req.skinStyle or "").strip()
        allowed = {"", "default", "dark", "green", "purple", "blue", "warm"}
        if style not in allowed:
            style = ""
        db.execute_update(
            "UPDATE yggl SET skin_style=%s WHERE name=%s AND (COALESCE(zaizhi,0)=0)",
            (style, req.name),
        )
        return {"success": True, "message": "已保存"}
    except Exception as e:
        logger.error(f"保存用户风格失败: {e}")
        return {"success": False, "message": str(e)}
