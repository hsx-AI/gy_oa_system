# -*- coding: utf-8 -*-
"""
登录认证API路由
"""
import math
import logging
from fastapi import APIRouter, Query
from pydantic import BaseModel
from database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


class LoginRequest(BaseModel):
    """登录请求模型"""
    admin: str  # 用户名（姓名）
    password: str  # 密码


class LoginResponse(BaseModel):
    """登录响应模型"""
    success: bool
    message: str = ""
    data: dict = {}


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
        # 密码正确，构建返回数据
        user_info = {
            "name": (user_data.get("name") or "").strip(),
            "dept": (user_data.get("lsys") or "").strip(),
            "jb": (user_data.get("jb") or "").strip(),
            "gh": (user_data.get("gh") or "").strip(),
            "xbie": (user_data.get("xbie") or "").strip()
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
            {"expireDate": k, "count": round(v, 2)}
            for k, v in sorted(expire_groups.items(), key=lambda x: parse_expire_for_sort(x[0]))
        ]
        # 入厂时间 rcnf：只展示年份，不展示 -01-01
        rcnf_val = r.get("rcnf")
        if hasattr(rcnf_val, "strftime"):
            raw = rcnf_val.strftime("%Y-%m-%d")
        elif rcnf_val is not None and str(rcnf_val).strip():
            raw = str(rcnf_val).strip()[:10]
        else:
            raw = ""
        if raw and len(raw) >= 4 and raw.endswith("-01-01"):
            entry_date = raw[:4]  # 仅年份
        else:
            entry_date = raw
        # 带薪休假剩余：工龄 1~9年5天、10~19年10天、20年以上15天；公司固定扣除3天（高温假）；本年已用从 qj 表统计（仅带薪休假/年休假，已通过，按0.25天进位）
        paid_leave_remaining = None
        paid_leave_detail = None
        try:
            entry_year = int(entry_date[:4]) if entry_date and len(entry_date) >= 4 and entry_date[:4].isdigit() else None
            if entry_year is not None:
                from datetime import date
                current_year = date.today().year
                years = current_year - entry_year
                if years < 1:
                    entitlement = 0
                elif years < 10:
                    entitlement = 5
                elif years < 20:
                    entitlement = 10
                else:
                    entitlement = 15
                deducted = 3  # 固定高温假公休
                available = max(0, entitlement - deducted)
                # 本年已通过的带薪休假/年休假天数（qj 表，最小单位 0.25 天，不够进位）
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
                "entryDate": entry_date,
                "exchangeTickets": round(total, 2),
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
