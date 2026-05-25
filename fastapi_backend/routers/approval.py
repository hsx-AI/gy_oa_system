# -*- coding: utf-8 -*-
"""
请假/加班/公出逐级审批 API
- 员工无审批权限
- 请假: qjzt=1(室主任spr) -> qjzt=3(部长spr2) -> qjzt=4; 驳回 qjzt=22
- 加班: jiabanzt=0(室主任spr) -> [有spr2时 1->3] -> jiabanzt=5(打卡管理员) -> 4; 驳回 22
- 公出: 两级固定。室主任(szr)先批 szrzt=1->2; 部领导(bld)再批 bldzt=1->2; 驳回 22
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Any
from pydantic import BaseModel
from datetime import datetime
from database import db
from attendance_db import attendance_db
import math
import uuid
from routers.approvers import _get_user_info, _jb_match
from routers.db_manager import _get_admin1
from routers.leave_overtime import _calc_hours, round_overtime_hours_down
from routers.suggestions import collect_valid_times_with_marks, build_intervals_from_marks
from utils.helpers import format_datetime_plain
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approval", tags=["审批"])


def _recalc_overtime_hours(row: dict) -> float:
    """从 timefrom/timeto 重新计算加班时长，避免依赖可能由旧算法写入的 tian1/jbf。"""
    tf = row.get("timefrom")
    tt = row.get("timeto")
    date_val = row.get("timedate")
    if not tf or not tt:
        raw = row.get("tian1")
        if raw is None or raw == "" or raw == 0:
            raw = row.get("jbf") or 0
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0
    try:
        if isinstance(tf, datetime):
            tf_str = tf.strftime("%H:%M:%S")
            date_str = tf.strftime("%Y-%m-%d")
        else:
            tf_str = str(tf).strip()
            if " " in tf_str:
                date_str, tf_str = tf_str.split(" ", 1)
            else:
                date_str = str(date_val or "")[:10]
        if isinstance(tt, datetime):
            tt_str = tt.strftime("%H:%M:%S")
        else:
            tt_str = str(tt).strip()
            if " " in tt_str:
                tt_str = tt_str.split(" ", 1)[1]
        hours = _calc_hours(tf_str, tt_str, date_str)
        return round_overtime_hours_down(hours)
    except Exception as e:
        logger.debug("重算加班时长失败: %s", e)
        raw = row.get("tian1")
        if raw is None or raw == "" or raw == 0:
            raw = row.get("jbf") or 0
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0


def _get_dakaman() -> Optional[str]:
    """从 webconfig 表读取 dakaman 字段（打卡管理员，加班最后一环审批人）。"""
    try:
        rows = db.execute_query("SELECT dakaman FROM webconfig WHERE id = %s LIMIT 1", ("1",))
        if rows and rows[0].get("dakaman") is not None:
            return (rows[0]["dakaman"] or "").strip() or None
    except Exception as e:
        logger.debug(f"读取 webconfig.dakaman 失败: {e}")
    return None


def _fmt_dt(d):
    """格式化为 YYYY-MM-DD HH:MM:SS，无小数秒"""
    return format_datetime_plain(d)


# ==================== 权限检查 ====================

@router.get("/can-approve")
async def can_approve(name: str = Query(...)):
    """检查当前用户是否有审批权限（员工无权限；部长/主任等及 dakaman 有审批权限；admin1 等同部长但不含打卡管理员最终审批）"""
    name_stripped = (name or "").strip()
    admin1 = _get_admin1()
    if admin1 and name_stripped == admin1:
        return {"success": True, "canApprove": True, "jb": "系统管理员", "reason": "系统管理员等同部长权限（不含打卡管理员最终审批加班）"}
    dakaman = _get_dakaman()
    if dakaman and name_stripped == dakaman:
        return {"success": True, "canApprove": True, "jb": "打卡管理员", "reason": "打卡管理员可审批加班最后一环"}

    user = _get_user_info(name)
    if not user:
        return {"success": True, "canApprove": False, "reason": "用户不存在"}
    jb = (user.get("jb") or "").strip()
    if _jb_match(jb, "员工"):
        return {"success": True, "canApprove": False, "jb": jb, "reason": "员工无审批权限"}
    return {"success": True, "canApprove": True, "jb": jb}


# ==================== 请假审批 ====================

@router.get("/pending/leave")
async def get_pending_leave(approver: str = Query(..., description="当前审批人姓名")):
    """获取待当前用户审批的请假列表"""
    try:
        # qjzt=1: spr 审批; qjzt=3: spr2 审批
        query = """
            SELECT id, bz, xm, qjfs, bc, gx, timefrom, timeto, tian, xiaoshi, jy, smcl,
                spr, spr2, qjtime, qjzt, `2j`, content, hxpxh
            FROM qj
            WHERE (qjzt = 1 AND spr = %s) OR (qjzt = 3 AND spr2 = %s)
            ORDER BY qjtime DESC
        """
        rows = db.execute_query(query, (approver, approver))
        items = []
        for r in rows:
            items.append({
                "id": r["id"],
                "applicant": r.get("xm") or "",
                "type": r.get("qjfs") or "",
                "department": r.get("bz") or "",
                "shift": r.get("bc") or "",
                "contactMethod": r.get("gx") or "",
                "startTime": _fmt_dt(r.get("timefrom")),
                "endTime": _fmt_dt(r.get("timeto")),
                "duration": float(r.get("tian") or 0),
                "reason": r.get("jy") or "",
                "material": r.get("smcl") or "",
                "applyTime": _fmt_dt(r.get("qjtime")),
                "spr": r.get("spr"),
                "spr2": r.get("spr2"),
                "qjzt": r.get("qjzt"),
                "needSecondApproval": (r.get("2j") or 0) == 1,
                "content": r.get("content"),
                "hxpxh": r.get("hxpxh"),
            })
        return {"success": True, "data": items}
    except Exception as e:
        logger.error(f"获取待审批请假失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leave/{item_id}")
async def get_leave_detail(item_id: str):
    """请假详情"""
    rows = db.execute_query(
        "SELECT * FROM qj WHERE id = %s",
        (item_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    r = rows[0]
    return {
        "success": True,
        "data": {
            "id": r["id"],
            "applicant": r.get("xm"),
            "type": r.get("qjfs"),
            "department": r.get("bz"),
            "shift": r.get("bc"),
            "contactMethod": r.get("gx"),
            "startTime": _fmt_dt(r.get("timefrom")),
            "endTime": _fmt_dt(r.get("timeto")),
            "duration": r.get("tian"),
            "reason": r.get("jy"),
            "material": r.get("smcl"),
            "materialFile": r.get("smclwj"),
            "applyTime": _fmt_dt(r.get("qjtime")),
            "spr": r.get("spr"),
            "spr2": r.get("spr2"),
            "qjzt": r.get("qjzt"),
            "content": r.get("content"),
            "rejectReason": (r.get("bhyy") or "").strip(),
        }
    }


class ApproveRequest(BaseModel):
    action: str  # "approve" | "reject"
    reason: Optional[str] = ""
    approver: Optional[str] = None  # 当前审批人姓名，用于加班最终环(jiabanzt=5)仅 dakaman 可操作时校验


def _add_exchange_tickets(name: str, tickets: float, ly: str = "", sj: str = ""):
    """向 hxp 表增加换休票。tickets 为张数，ly 为来源说明，sj 为自定义时间（空则取当前时间）。"""
    if not name or tickets <= 0:
        return
    try:
        tickets = round(float(tickets), 2)
        if tickets <= 0:
            return
        sj_val = (sj or "").strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ly_val = (ly or "").strip()
        try:
            hxp_id = uuid.uuid4().hex
            n = db.execute_update(
                "INSERT INTO hxp (id, name, sl, sj, ly) VALUES (%s, %s, %s, %s, %s)",
                (hxp_id, name.strip(), tickets, sj_val, ly_val),
            )
        except Exception:
            n = db.execute_update(
                "INSERT INTO hxp (name, sl, sj, ly) VALUES (%s, %s, %s, %s)",
                (name.strip(), tickets, sj_val, ly_val),
            )
        if n <= 0:
            logger.warning("换休票入账未生效（INSERT 影响行数为0）")
    except Exception as e:
        logger.warning(f"换休票入账失败: {e}")


def _deduct_exchange_tickets(name: str, consume: float):
    """换休审批通过时，从 hxp 表扣减换休票，优先消耗有效期最近的（最先过期的），支持0.5张"""
    if not name or consume <= 0:
        return
    try:
        from datetime import date
        from utils.hxp_helper import compute_expire_date, parse_expire_for_sort
        today = date.today().strftime("%Y-%m-%d")
        rows = db.execute_query(
            "SELECT id, sl, sj FROM hxp WHERE name = %s AND sl > 0 ORDER BY id",
            (name,)
        )
        rows_with_exp = []
        for r in rows:
            exp = compute_expire_date(r.get("sj"))
            if exp and exp < today:
                continue  # 已过期，不参与扣减
            rows_with_exp.append((r, parse_expire_for_sort(exp) if exp else (9999, 12)))
        rows_with_exp.sort(key=lambda x: x[1])
        remain = round(float(consume), 2)
        for row, _ in rows_with_exp:
            if remain <= 0:
                break
            rid = row["id"]
            try:
                sl = float(row.get("sl") or 0)
            except (TypeError, ValueError):
                sl = 0.0
            if sl <= 0:
                continue
            if remain >= sl:
                db.execute_update("DELETE FROM hxp WHERE id = %s", (rid,))
                remain = round(remain - sl, 2)
            else:
                db.execute_update("UPDATE hxp SET sl = sl - %s WHERE id = %s",
                                  (round(remain, 2), rid))
                remain = 0
    except Exception:
        pass


@router.post("/leave/{item_id}/action")
async def leave_approve_action(item_id: str, req: ApproveRequest):
    """请假单条审批"""
    rows = db.execute_query("SELECT id, qjzt, `2j`, spr, spr2, xm, qjfs, hxpxh, tian FROM qj WHERE id = %s", (item_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    row = rows[0]
    qjzt = row.get("qjzt")
    need_2j = (row.get("2j") or 0) == 1

    if req.action == "reject":
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        reason = (req.reason or "").strip()
        try:
            db.execute_update("UPDATE qj SET qjzt = 22, sptime = %s, bhyy = %s WHERE id = %s",
                              (now, reason[:500] if reason else None, item_id))
        except Exception:
            db.execute_update("UPDATE qj SET qjzt = 22, sptime = %s WHERE id = %s", (now, item_id))
        return {"success": True, "message": "已驳回"}

    if req.action != "approve":
        raise HTTPException(status_code=400, detail="无效操作")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_approved = False
    if qjzt == 1:
        if need_2j:
            db.execute_update("UPDATE qj SET qjzt = 3, sptime = %s WHERE id = %s", (now, item_id))
        else:
            db.execute_update("UPDATE qj SET qjzt = 4, sptime = %s, sctime = %s WHERE id = %s",
                              (now, now, item_id))
            final_approved = True
    elif qjzt == 3:
        db.execute_update("UPDATE qj SET qjzt = 4, sp2time = %s, sctime = %s WHERE id = %s",
                          (now, now, item_id))
        final_approved = True
    else:
        raise HTTPException(status_code=400, detail="当前状态无法审批")

    # 换休/员工换休票最终审批通过时，从 hxp 表扣减换休票（优先消耗最先过期的）
    if final_approved:
        qjfs = (row.get("qjfs") or "").strip()
        if qjfs in ("换休", "员工换休票"):
            xm = (row.get("xm") or "").strip()
            hxpxh_val = row.get("hxpxh")
            try:
                consume = float(hxpxh_val) if hxpxh_val is not None else 0
            except (TypeError, ValueError):
                tian = row.get("tian")
                try:
                    dur = float(tian) if tian is not None else 0
                except (TypeError, ValueError):
                    dur = 0
                consume = round(round(dur * 4) / 2, 2)  # 0.5张起
            if consume > 0 and xm:
                _deduct_exchange_tickets(xm, consume)

    return {"success": True, "message": "已通过"}


class BatchApproveRequest(BaseModel):
    ids: List[str]  # 请假 id 支持 UUID 字符串
    action: str
    reason: Optional[str] = ""
    approver: Optional[str] = None  # 加班批量审批时传当前审批人，用于 jiabanzt=5 仅 dakaman 校验


@router.post("/leave/batch")
async def leave_batch_approve(req: BatchApproveRequest):
    """请假批量审批（批量 SQL 优化）"""
    ids = [str(i).strip() for i in req.ids if str(i).strip()]
    if not ids:
        return {"success": True, "passed": 0, "failed": 0, "message": "无有效ID"}

    if req.action == "reject":
        ok, fail = 0, 0
        for iid in ids:
            try:
                await leave_approve_action(iid, ApproveRequest(action="reject", reason=req.reason))
                ok += 1
            except Exception:
                fail += 1
        return {"success": True, "passed": ok, "failed": fail, "message": f"成功{ok}条，失败{fail}条"}

    ph = ",".join(["%s"] * len(ids))
    rows = db.execute_query(
        f"SELECT id, qjzt, `2j`, spr, spr2, xm, qjfs, hxpxh, tian FROM qj WHERE id IN ({ph})",
        tuple(ids),
    ) or []
    row_map = {str(r["id"]): r for r in rows}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ids_to_3 = []
    ids_to_4_from_1 = []
    ids_to_4_from_3 = []
    final_rows = []
    ok, fail = 0, 0

    for iid in ids:
        r = row_map.get(iid)
        if not r:
            fail += 1
            continue
        qjzt = r.get("qjzt")
        need_2j = (r.get("2j") or 0) == 1
        if qjzt == 1:
            if need_2j:
                ids_to_3.append(iid)
            else:
                ids_to_4_from_1.append(iid)
                final_rows.append(r)
            ok += 1
        elif qjzt == 3:
            ids_to_4_from_3.append(iid)
            final_rows.append(r)
            ok += 1
        else:
            fail += 1

    if ids_to_3:
        p = ",".join(["%s"] * len(ids_to_3))
        db.execute_update(f"UPDATE qj SET qjzt = 3, sptime = %s WHERE id IN ({p})", (now,) + tuple(ids_to_3))
    if ids_to_4_from_1:
        p = ",".join(["%s"] * len(ids_to_4_from_1))
        db.execute_update(f"UPDATE qj SET qjzt = 4, sptime = %s, sctime = %s WHERE id IN ({p})", (now, now) + tuple(ids_to_4_from_1))
    if ids_to_4_from_3:
        p = ",".join(["%s"] * len(ids_to_4_from_3))
        db.execute_update(f"UPDATE qj SET qjzt = 4, sp2time = %s, sctime = %s WHERE id IN ({p})", (now, now) + tuple(ids_to_4_from_3))

    for r in final_rows:
        qjfs = (r.get("qjfs") or "").strip()
        if qjfs in ("换休", "员工换休票"):
            xm = (r.get("xm") or "").strip()
            hxpxh_val = r.get("hxpxh")
            try:
                consume = float(hxpxh_val) if hxpxh_val is not None else 0
            except (TypeError, ValueError):
                tian = r.get("tian")
                try:
                    dur = float(tian) if tian is not None else 0
                except (TypeError, ValueError):
                    dur = 0
                consume = round(round(dur * 4) / 2, 2)
            if consume > 0 and xm:
                try:
                    _deduct_exchange_tickets(xm, consume)
                except Exception as e:
                    logger.warning(f"请假批量审批扣减换休票失败 xm={xm}: {e}")

    return {"success": True, "passed": ok, "failed": fail, "message": f"成功{ok}条，失败{fail}条"}


# ==================== 加班审批 ====================

@router.get("/pending/overtime")
async def get_pending_overtime(approver: str = Query(...)):
    """获取待当前用户审批的加班列表（含打卡管理员：jiabanzt=5 时仅 webconfig.dakaman 可见）"""
    try:
        # jiabanzt=0 或 1: spr 审批; jiabanzt=3: spr2 审批; jiabanzt=5: 打卡管理员审批
        query = """
            SELECT id, bz, xm, jb, timedate, timefrom, timeto, jiabantime, tian1, jbf, content, spr, spr2, hx
            FROM jiaban
            WHERE (jiabanzt IN (0, 1) AND spr = %s) OR (jiabanzt = 3 AND spr2 = %s)
            ORDER BY jiabantime DESC
        """
        rows = list(db.execute_query(query, (approver, approver)) or [])
        dakaman = _get_dakaman()
        # jiabanzt=5 仅打卡管理员可见，admin1 不充当 dakaman 最终审批
        if dakaman and (approver or "").strip() == dakaman:
            try:
                rows_dk = db.execute_query(
                    """SELECT id, bz, xm, jb, timedate, timefrom, timeto, jiabantime, tian1, jbf, content, spr, spr2, hx
                       FROM jiaban WHERE jiabanzt = 5 ORDER BY jiabantime DESC"""
                ) or []
                seen = {str(r.get("id") or "") for r in rows}
                for r in rows_dk:
                    rid = str(r.get("id") or "")
                    if rid and rid not in seen:
                        seen.add(rid)
                        rows.append(r)
                rows.sort(key=lambda x: str(x.get("jiabantime") or ""), reverse=True)
            except Exception as e:
                logger.warning("合并打卡管理员待办失败: %s", e)
        items = []
        for r in rows:
            tf = r.get("timefrom") or ""
            tt = r.get("timeto") or ""
            # 统一为 HH:MM:SS，与打卡精确到秒一致，避免智能校验误判「打卡不实」
            if isinstance(tf, datetime):
                tf = tf.strftime("%H:%M:%S") if tf else ""
            elif tf and " " in str(tf):
                tf = str(tf).split(" ")[-1].strip()
                if tf and len(tf) == 5 and ":" in tf:
                    tf = tf + ":00"
                tf = (tf or "")[:8] if tf else ""
            else:
                tf = str(tf).strip() if tf else ""
                if tf and len(tf) == 5 and ":" in tf:
                    tf = tf + ":00"
                tf = (tf or "")[:8] if tf else ""
            if isinstance(tt, datetime):
                tt = tt.strftime("%H:%M:%S") if tt else ""
            elif tt and " " in str(tt):
                tt = str(tt).split(" ")[-1].strip()
                if tt and len(tt) == 5 and ":" in tt:
                    tt = tt + ":00"
                tt = (tt or "")[:8] if tt else ""
            else:
                tt = str(tt).strip() if tt else ""
                if tt and len(tt) == 5 and ":" in tt:
                    tt = tt + ":00"
                tt = (tt or "")[:8] if tt else ""
            hours = _recalc_overtime_hours(r)
            hx_val = (r.get("hx") or "").strip()
            need_exchange_ticket = "是" if hx_val and str(hx_val) in ("是", "1", "true", "yes") else "否"
            items.append({
                "id": str(r.get("id") or ""),
                "applicant": str(r.get("xm") or ""),
                "level": str(r.get("jb") or ""),
                "department": _get_department_from_row(r),
                "date": str(r.get("timedate") or "")[:10],
                "startTime": tf,
                "endTime": tt,
                "hours": hours,
                "needExchangeTicket": need_exchange_ticket,
                "applyTime": _fmt_dt(r.get("jiabantime")) or "",
                "content": str(r.get("content") or ""),
                "spr": str(r.get("spr") or ""),
                "spr2": str(r.get("spr2") or ""),
            })
        return {"success": True, "data": items}
    except Exception as e:
        logger.error(f"获取待审批加班失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_department_from_row(r, xm_key="xm"):
    """从 jiaban 行取部门：优先 bz，为空时用申请人姓名查 yggl.lsys"""
    bz_val = (r.get("bz") or r.get("BZ") or "").strip()
    if bz_val:
        return bz_val
    xm = (r.get(xm_key) or r.get("XM") or "").strip()
    if not xm:
        return "-"
    yggl_rows = db.execute_query("SELECT lsys FROM yggl WHERE name = %s LIMIT 1", (xm,))
    if yggl_rows and (yggl_rows[0].get("lsys") or "").strip():
        return (yggl_rows[0].get("lsys") or "").strip()
    return "-"


@router.get("/overtime/{item_id}")
async def get_overtime_detail(item_id: str):
    """加班详情（item_id 为 jiaban 表 id，支持 UUID 字符串）"""
    item_id = str(item_id).strip()
    rows = db.execute_query("SELECT * FROM jiaban WHERE id = %s", (item_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    r = rows[0]
    department_display = _get_department_from_row(r)
    hx_val = (r.get("hx") or "").strip()
    need_exchange_ticket = "是" if hx_val and str(hx_val) in ("是", "1", "true", "yes") else "否"
    return {
        "success": True,
        "data": {
            "id": r["id"],
            "applicant": r.get("xm") or "",
            "level": r.get("jb") or "",
            "department": department_display,
            "date": str(r.get("timedate") or "")[:10],
            "startTime": _fmt_dt(r.get("timefrom")),
            "endTime": _fmt_dt(r.get("timeto")),
            "hours": _recalc_overtime_hours(r),
            "needExchangeTicket": need_exchange_ticket,
            "applyTime": _fmt_dt(r.get("jiabantime")),
            "content": r.get("content"),
            "spr": r.get("spr"),
            "spr2": r.get("spr2"),
            "rejectReason": (r.get("bhyy") or "").strip(),
        }
    }


@router.post("/overtime/{item_id}/action")
async def overtime_approve_action(item_id: str, req: ApproveRequest):
    """加班单条审批。item_id 为 jiaban 表 id（UUID 字符串）。"""
    item_id = str(item_id).strip()
    rows = db.execute_query(
        "SELECT id, jiabanzt, spr2, xm, hx, tian1, jbf, timedate FROM jiaban WHERE id = %s",
        (item_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    row = rows[0]
    jiabanzt = row.get("jiabanzt") or 0
    has_spr2 = bool(row.get("spr2"))

    if req.action == "reject":
        reason = (req.reason or "").strip()
        try:
            n = db.execute_update("UPDATE jiaban SET jiabanzt = 22, bhyy = %s WHERE id = %s",
                                  (reason[:500] if reason else None, item_id))
        except Exception as e:
            logger.warning("加班驳回写入 bhyy 失败，回退为仅更新状态: %s", e)
            n = db.execute_update("UPDATE jiaban SET jiabanzt = 22 WHERE id = %s", (item_id,))
        if n <= 0:
            logger.error("加班驳回未更新到任何记录: id=%s", item_id)
            raise HTTPException(status_code=500, detail="驳回失败，未找到对应记录")
        return {"success": True, "message": "已驳回"}

    if req.action != "approve":
        raise HTTPException(status_code=400, detail="无效操作")

    final_approved = False
    if jiabanzt in (0, 1):
        if has_spr2:
            db.execute_update("UPDATE jiaban SET jiabanzt = 3 WHERE id = %s", (item_id,))
        else:
            # 无二级审批人时进入打卡管理员审批（最后一环）
            db.execute_update("UPDATE jiaban SET jiabanzt = 5 WHERE id = %s", (item_id,))
    elif jiabanzt == 3:
        # 二级审批通过后进入打卡管理员审批
        db.execute_update("UPDATE jiaban SET jiabanzt = 5 WHERE id = %s", (item_id,))
    elif jiabanzt == 5:
        # 仅 webconfig.dakaman 可做最终审批，admin1 不充当 dakaman
        dakaman = _get_dakaman()
        admin1 = _get_admin1()
        cur_approver = (req.approver or "").strip()
        if not dakaman or cur_approver != dakaman or (admin1 and cur_approver == admin1):
            raise HTTPException(
                status_code=403,
                detail="加班最终审批仅限打卡管理员（webconfig.dakaman），系统管理员无权操作",
            )
        # 打卡管理员通过后流程结束
        db.execute_update("UPDATE jiaban SET jiabanzt = 4 WHERE id = %s", (item_id,))
        final_approved = True
    else:
        raise HTTPException(status_code=400, detail="当前状态无法审批")

    # 加班最终审批通过：重算时长 → hx=是 写 hxp 表；hx=否 写 jbf
    if final_approved:
        hx = (row.get("hx") or row.get("HX") or "").strip()
        need_exchange = hx and str(hx) in ("是", "1", "true", "yes")
        hours = _recalc_overtime_hours(row)
        # 同步修正 tian1（以最新算法为准）
        tian1_new = str(int(hours)) if hours == int(hours) else str(hours)
        try:
            db.execute_update("UPDATE jiaban SET tian1 = %s WHERE id = %s", (tian1_new, item_id))
        except Exception:
            pass
        xm = (row.get("xm") or "").strip()

        if need_exchange and hours > 0 and xm:
            from utils.overtime_exchange import calc_overtime_exchange_tickets

            jb = (row.get("jb") or "").strip()
            tickets = calc_overtime_exchange_tickets(hours, jb)
            overtime_sj = str(row.get("timedate") or "")[:10]
            if tickets > 0:
                _add_exchange_tickets(xm, tickets, ly="加班换休", sj=overtime_sj)
                db.execute_update(
                    "UPDATE jiaban SET hxp = %s, jbf = 0 WHERE id = %s",
                    (tickets, item_id),
                )
        else:
            # hx=否：只记其他绩效激励，回写 jbf（以 tian1 为准），hxp 置 0
            db.execute_update(
                "UPDATE jiaban SET jbf = %s, hxp = 0 WHERE id = %s",
                (hours, item_id),
            )

    return {"success": True, "message": "已通过"}


@router.post("/overtime/batch")
async def overtime_batch_approve(req: BatchApproveRequest):
    """加班批量审批（批量 SQL 优化）"""
    ids = [str(i).strip() for i in req.ids if str(i).strip()]
    if not ids:
        return {"success": True, "passed": 0, "failed": 0, "message": "无有效ID"}

    if req.action == "reject":
        ok, fail = 0, 0
        for iid in ids:
            try:
                await overtime_approve_action(iid, ApproveRequest(action="reject", reason=req.reason, approver=req.approver))
                ok += 1
            except Exception:
                fail += 1
        return {"success": True, "passed": ok, "failed": fail, "message": f"成功{ok}条，失败{fail}条"}

    ph = ",".join(["%s"] * len(ids))
    rows = db.execute_query(
        f"SELECT id, jiabanzt, spr2, xm, hx, tian1, jbf, timedate FROM jiaban WHERE id IN ({ph})",
        tuple(ids),
    ) or []
    row_map = {str(r["id"]): r for r in rows}

    dakaman = _get_dakaman()
    admin1 = _get_admin1()
    cur_approver = (req.approver or "").strip()

    ids_to_3 = []
    ids_to_5_from_01 = []
    ids_to_5_from_3 = []
    ids_to_4 = []
    final_rows = []
    ok, fail = 0, 0

    for iid in ids:
        r = row_map.get(iid)
        if not r:
            fail += 1
            continue
        jiabanzt = r.get("jiabanzt") or 0
        has_spr2 = bool(r.get("spr2"))

        if jiabanzt in (0, 1):
            if has_spr2:
                ids_to_3.append(iid)
            else:
                ids_to_5_from_01.append(iid)
            ok += 1
        elif jiabanzt == 3:
            ids_to_5_from_3.append(iid)
            ok += 1
        elif jiabanzt == 5:
            if not dakaman or cur_approver != dakaman or (admin1 and cur_approver == admin1):
                fail += 1
                continue
            ids_to_4.append(iid)
            final_rows.append(r)
            ok += 1
        else:
            fail += 1

    if ids_to_3:
        p = ",".join(["%s"] * len(ids_to_3))
        db.execute_update(f"UPDATE jiaban SET jiabanzt = 3 WHERE id IN ({p})", tuple(ids_to_3))
    if ids_to_5_from_01:
        p = ",".join(["%s"] * len(ids_to_5_from_01))
        db.execute_update(f"UPDATE jiaban SET jiabanzt = 5 WHERE id IN ({p})", tuple(ids_to_5_from_01))
    if ids_to_5_from_3:
        p = ",".join(["%s"] * len(ids_to_5_from_3))
        db.execute_update(f"UPDATE jiaban SET jiabanzt = 5 WHERE id IN ({p})", tuple(ids_to_5_from_3))
    if ids_to_4:
        p = ",".join(["%s"] * len(ids_to_4))
        db.execute_update(f"UPDATE jiaban SET jiabanzt = 4 WHERE id IN ({p})", tuple(ids_to_4))

    for r in final_rows:
        hx = (r.get("hx") or r.get("HX") or "").strip()
        need_exchange = hx and str(hx) in ("是", "1", "true", "yes")
        hours = _recalc_overtime_hours(r)
        xm = (r.get("xm") or "").strip()
        rid = str(r["id"])
        tian1_new = str(int(hours)) if hours == int(hours) else str(hours)
        try:
            db.execute_update("UPDATE jiaban SET tian1 = %s WHERE id = %s", (tian1_new, rid))
        except Exception:
            pass

        if need_exchange and hours > 0 and xm:
            from utils.overtime_exchange import calc_overtime_exchange_tickets

            jb = (r.get("jb") or "").strip()
            tickets = calc_overtime_exchange_tickets(hours, jb)
            overtime_sj = str(r.get("timedate") or "")[:10]
            if tickets > 0:
                try:
                    _add_exchange_tickets(xm, tickets, ly="加班换休", sj=overtime_sj)
                except Exception as e:
                    logger.warning(f"加班批量审批添加换休票失败 xm={xm}: {e}")
                db.execute_update("UPDATE jiaban SET hxp = %s, jbf = 0 WHERE id = %s", (tickets, rid))
        else:
            db.execute_update("UPDATE jiaban SET jbf = %s, hxp = 0 WHERE id = %s", (hours, rid))

    return {"success": True, "passed": ok, "failed": fail, "message": f"成功{ok}条，失败{fail}条"}


def _parse_overtime_datetime(date_str: str, time_str: str) -> Optional[str]:
    """将加班日期 + 开始/结束时间 转为可比较的 YYYY-MM-DD HH:MM:SS"""
    if not date_str or not time_str:
        return None
    d = str(date_str).strip()[:10]
    t = str(time_str).strip()
    if " " in t:
        t = t.split(" ")[-1]
    if len(t) == 5 and ":" in t:  # HH:MM
        t = t + ":00"
    if len(t) < 8:
        return None
    return f"{d} {t[:8]}"


def _intervals_overlap(s1: str, e1: str, s2: str, e2: str) -> bool:
    """两段时间是否有交集（重叠），闭区间 [s,e] 语义，与历史请假/加班数据一致"""
    if not all([s1, e1, s2, e2]):
        return False
    return s1 <= e2 and s2 <= e1


def _truncate_to_minute(dt_str: str) -> str:
    """将 YYYY-MM-DD HH:MM:SS 截断到分钟，便于与打卡按分钟对齐比较"""
    if not dt_str or len(dt_str) < 19:
        return dt_str or ""
    return dt_str[:17] + "00"


def _overtime_segments_for_noon(date_ymd: str, start_dt: str, end_dt: str) -> List[tuple]:
    """
    若加班区间横跨午休(12:00-13:00)，拆成两段：12点前一段、13点后一段；
    否则返回整段。用于智能校验时分别检查两段是否都被打卡覆盖（午休外出吃饭不判为打卡不实）。
    """
    if not date_ymd or not start_dt or not end_dt or start_dt >= end_dt:
        return [(start_dt, end_dt)] if start_dt and end_dt else []
    noon_start = f"{date_ymd} 12:00:00"
    noon_end = f"{date_ymd} 13:00:00"
    # 横跨午休：开始 < 13:00 且 结束 > 12:00
    if start_dt < noon_end and end_dt > noon_start:
        segs = []
        if start_dt < noon_start:
            segs.append((start_dt, noon_start))
        if end_dt > noon_end:
            segs.append((noon_end, end_dt))
        if segs:
            return segs
    return [(start_dt, end_dt)]


def _interval_contained_in(s_start: str, s_end: str, punch_starts: List[str], punch_ends: List[str]) -> bool:
    """加班区间 [s_start, s_end] 是否被某段打卡区间包含。按分钟对齐比较，避免秒级差异误判「打卡不实」。"""
    s_start_m = _truncate_to_minute(s_start)
    s_end_m = _truncate_to_minute(s_end)
    for p_start, p_end in zip(punch_starts, punch_ends):
        if not p_start or not p_end:
            continue
        p_start_m = _truncate_to_minute(p_start)
        p_end_m = _truncate_to_minute(p_end)
        if p_start_m <= s_start_m and s_end_m <= p_end_m:
            return True
    return False


class OvertimeValidateItem(BaseModel):
    id: str
    applicant: str
    date: str
    startTime: str
    endTime: str


class OvertimeValidateRequest(BaseModel):
    items: List[OvertimeValidateItem]


@router.post("/overtime/validate")
async def overtime_validate(req: OvertimeValidateRequest):
    """
    加班审批智能校验：对当前待审批列表逐条校验。
    1) 列表内时间段重复 -> 不通过，原因「时间段重复」
    2) 与打卡记录对比，加班区间未被某段打卡包含 -> 不通过，原因「打卡不实」
    3) 与 jiaban 表已有记录时间段重叠 -> 不通过，原因「重复申报」

    性能优化：使用批量查询替代逐条查询。
    """
    results = []
    items = req.items or []
    if not items:
        return {"success": True, "results": results}

    parsed = []
    for it in items:
        start_dt = _parse_overtime_datetime(it.date, it.startTime)
        end_dt = _parse_overtime_datetime(it.date, it.endTime)
        if not start_dt or not end_dt or start_dt >= end_dt:
            results.append({"id": it.id, "pass": False, "reason": "时间无效"})
            continue
        parsed.append((it.id, (it.applicant or "").strip(), start_dt, end_dt))

    # 快速索引
    parsed_map = {p[0]: p for p in parsed}

    # 1) 列表内重复
    duplicate_ids = set()
    by_applicant = {}
    for id_, app, s, e in parsed:
        by_applicant.setdefault(app, []).append((id_, s, e))
    for app, group in by_applicant.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if _intervals_overlap(group[i][1], group[i][2], group[j][1], group[j][2]):
                    duplicate_ids.add(group[i][0])
                    duplicate_ids.add(group[j][0])

    # ---------- 批量预取数据 ----------
    applicants = list({p[1] for p in parsed})
    dates = list({p[2][:10] for p in parsed})
    if not applicants or not dates:
        for it in items:
            if it.id not in {r["id"] for r in results}:
                results.append({"id": it.id, "pass": True, "reason": None})
        return {"success": True, "results": results}

    min_date = min(dates)
    max_date = max(dates)

    # 2a) 批量查打卡记录
    att_map = {}
    try:
        ph = ",".join(["%s"] * len(applicants))
        att_rows = db.execute_query(
            f"SELECT * FROM attendance_records "
            f"WHERE employee_name IN ({ph}) AND attendance_date >= %s AND attendance_date <= %s",
            tuple(applicants) + (min_date, max_date),
        )
        for row in att_rows:
            n = (row.get("employee_name") or "").strip()
            d = row.get("attendance_date") or ""
            if hasattr(d, "strftime"):
                d = d.strftime("%Y-%m-%d")
            else:
                d = str(d)[:10]
            att_map.setdefault((n, d), []).append(row)
    except Exception:
        pass

    # 3a) 批量查 jiaban 已有记录
    jiaban_map = {}
    try:
        item_ids = [p[0] for p in parsed]
        ph_names = ",".join(["%s"] * len(applicants))
        jiaban_rows = db.execute_query(
            f"SELECT id, xm, timefrom, timeto FROM jiaban "
            f"WHERE xm IN ({ph_names}) AND (jiabanzt IS NULL OR jiabanzt != 22)",
            tuple(applicants),
        ) or []
        item_id_set = set(item_ids)
        for row in jiaban_rows:
            if row.get("id") in item_id_set:
                continue
            n = (row.get("xm") or "").strip()
            jiaban_map.setdefault(n, []).append(row)
    except Exception:
        pass

    # ---------- 逐条校验（纯内存） ----------
    for it in items:
        if it.id in duplicate_ids:
            results.append({"id": it.id, "pass": False, "reason": "时间段重复"})
            continue
        rec = parsed_map.get(it.id)
        if not rec:
            continue
        _, applicant, start_dt, end_dt = rec

        date_ymd = start_dt[:10]
        if start_dt < f"{date_ymd} 08:00:00":
            results.append({"id": it.id, "pass": False, "reason": "请核实是否存在打卡不实"})
            continue

        # 2b) 打卡校验（基于进/出标记配对，从预取数据中查找）
        punch_contained = False
        for row in att_map.get((applicant, date_ymd), []):
            time_mark_pairs = collect_valid_times_with_marks(row)
            intervals = build_intervals_from_marks(time_mark_pairs)
            punch_starts = []
            punch_ends = []
            for t_in, t_out in intervals:
                s = f"{date_ymd} {t_in.strftime('%H:%M:%S')}" if t_in else ""
                e = f"{date_ymd} {t_out.strftime('%H:%M:%S')}" if t_out else ""
                if s and e and s < e:
                    punch_starts.append(s)
                    punch_ends.append(e)
            segments = _overtime_segments_for_noon(date_ymd, start_dt, end_dt)
            all_contained = all(
                _interval_contained_in(seg_start, seg_end, punch_starts, punch_ends)
                for seg_start, seg_end in segments
            )
            if all_contained:
                punch_contained = True
                break
        if not punch_contained:
            results.append({"id": it.id, "pass": False, "reason": "请核实是否存在打卡不实"})
            continue

        # 3b) jiaban 查重（从预取数据中查找）
        overlap_with_db = False
        for row in jiaban_map.get(applicant, []):
            r_start = format_datetime_plain(row.get("timefrom")) or ""
            r_end = format_datetime_plain(row.get("timeto")) or ""
            if "." in r_start:
                r_start = r_start.split(".")[0]
            if "." in r_end:
                r_end = r_end.split(".")[0]
            if len(r_start) == 16 and r_start[10:11] == " ":
                r_start = r_start + ":00"
            if len(r_end) == 16 and r_end[10:11] == " ":
                r_end = r_end + ":00"
            r_start = r_start[:19]
            r_end = r_end[:19]
            if r_start and r_end and _intervals_overlap(start_dt, end_dt, r_start, r_end):
                overlap_with_db = True
                break
        if overlap_with_db:
            results.append({"id": it.id, "pass": False, "reason": "重复申报"})
            continue

        results.append({"id": it.id, "pass": True, "reason": None})
    return {"success": True, "results": results}


# ==================== 公出审批（按登记时选择的主任/领导流转） ====================
#
# 状态约定：bldzt 部领导批示(1=待审批 2=通过 22=驳回)，szrzt 室主任批示(1=待审批 2=通过 22=驳回)
# 时间字段：szrpztime 室主任批示时间，bldpztime 部领导批示时间
#
# 流转：登记写入 bldzt=1, szrzt=1
#   → 室主任(szr=选定人)审批：通过 szrzt=2, szrpztime=now；驳回 szrzt=22, szrpztime=now
#   → 部领导(bld=选定人)审批：通过 bldzt=2, bldpztime=now；驳回 bldzt=22, bldpztime=now, szrzt=0(重置)
# 待办：室主任看 szrzt=1 AND bldzt=1 AND szr=当前用户；部领导看 szrzt=2 AND bldzt=1 AND bld=当前用户
#

@router.get("/pending/business-trip")
async def get_pending_business_trip(approver: str = Query(...)):
    """
    获取待当前用户审批的公出列表（按登记时选择的 szr/室主任、bld/部领导 匹配当前用户）
    - 室主任待办: bldzt=1, szrzt=1, szr=当前用户
    - 部领导待办: bldzt=1, szrzt=2, bld=当前用户
    """
    try:
        # 一级：室主任待审批（szr=当前用户 即登记时选择的室主任）
        # yjcfsj=预计出发（登记即有）；gcsj=实际出发（返回登记后才有）
        q1 = """
            SELECT id, wpdw, gcdw, gcdd, gcsj, yjcfsj, yjfhsj, tzdbh, gcrw, bld, szr, gcr
            FROM gcsqb WHERE bldzt = 1 AND szrzt = 1 AND szr = %s
        """
        # 二级：部领导待审批（bld=当前用户 即登记时选择的部领导）
        q2 = """
            SELECT id, wpdw, gcdw, gcdd, gcsj, yjcfsj, yjfhsj, tzdbh, gcrw, bld, szr, gcr
            FROM gcsqb WHERE bldzt = 1 AND szrzt = 2 AND bld = %s
        """
        q1_legacy = """
            SELECT id, wpdw, gcdw, gcdd, gcsj, yjfhsj, tzdbh, gcrw, bld, szr, gcr
            FROM gcsqb WHERE bldzt = 1 AND szrzt = 1 AND szr = %s
        """
        q2_legacy = """
            SELECT id, wpdw, gcdw, gcdd, gcsj, yjfhsj, tzdbh, gcrw, bld, szr, gcr
            FROM gcsqb WHERE bldzt = 1 AND szrzt = 2 AND bld = %s
        """
        try:
            rows1 = db.execute_query(q1, (approver,))
            rows2 = db.execute_query(q2, (approver,))
        except Exception as e:
            err = str(e).lower()
            if "unknown column" in err and "yjcfsj" in err:
                rows1 = db.execute_query(q1_legacy, (approver,))
                rows2 = db.execute_query(q2_legacy, (approver,))
            elif "unknown column" in err and ("bldzt" in err or "szrzt" in err):
                return {"success": True, "data": []}
            else:
                raise
        items = []
        for r in rows1:
            items.append({
                "id": str(r["id"]) if r.get("id") is not None else "",
                "applicant": (r.get("gcryxm") or r.get("gcr") or "").strip(),
                "targetUnit": r.get("wpdw") or "",
                "department": r.get("gcdw") or "",
                "location": r.get("gcdd") or "",
                "startTime": _fmt_dt(r.get("gcsj")) or _fmt_dt(r.get("yjcfsj")),
                "endTime": _fmt_dt(r.get("yjfhsj")),
                "applyTime": _fmt_dt(r.get("sqsj")) if r.get("sqsj") else "",
                "noticeNo": r.get("tzdbh") or "",
                "task": r.get("gcrw") or "",
                "deptLeader": r.get("bld") or "",
                "roomDirector": r.get("szr") or "",
                "approvalLevel": "室主任",
            })
        for r in rows2:
            items.append({
                "id": str(r["id"]) if r.get("id") is not None else "",
                "applicant": (r.get("gcryxm") or r.get("gcr") or "").strip(),
                "targetUnit": r.get("wpdw") or "",
                "department": r.get("gcdw") or "",
                "location": r.get("gcdd") or "",
                "startTime": _fmt_dt(r.get("gcsj")) or _fmt_dt(r.get("yjcfsj")),
                "endTime": _fmt_dt(r.get("yjfhsj")),
                "applyTime": _fmt_dt(r.get("sqsj")) if r.get("sqsj") else "",
                "noticeNo": r.get("tzdbh") or "",
                "task": r.get("gcrw") or "",
                "deptLeader": r.get("bld") or "",
                "roomDirector": r.get("szr") or "",
                "approvalLevel": "部领导",
            })
        # 按出发时间倒序（无 sqsj 时用 startTime）
        items.sort(key=lambda x: x["applyTime"] or x.get("startTime") or "", reverse=True)
        return {"success": True, "data": items}
    except Exception as e:
        logger.error(f"获取待审批公出失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/business-trip/{item_id}")
async def get_business_trip_detail(item_id: str):
    """公出详情"""
    rows = db.execute_query("SELECT * FROM gcsqb WHERE id = %s", (item_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    r = rows[0]
    return {
        "success": True,
        "data": {
            "id": str(r["id"]) if r.get("id") is not None else "",
            "applicant": (r.get("gcryxm") or r.get("gcr") or "").strip(),
            "targetUnit": r.get("wpdw"),
            "department": r.get("gcdw"),
            "location": r.get("gcdd"),
            "noticeNo": r.get("tzdbh"),
            "projectName": r.get("xmmc"),
            "startTime": _fmt_dt(r.get("gcsj")) or _fmt_dt(r.get("yjcfsj")),
            "endTime": _fmt_dt(r.get("yjfhsj")),
            "applyTime": _fmt_dt(r.get("sqsj")) if r.get("sqsj") else _fmt_dt(r.get("gcsj")),
            "assignTime": _fmt_dt(r.get("wpsj")),
            "task": r.get("gcrw"),
            "phone": r.get("lxdh"),
            "amount": r.get("qkje"),
            "totalPeople": r.get("bcgczrs"),
            "deptLeader": r.get("bld"),
            "roomDirector": r.get("szr"),
            "rejectReason": (r.get("bhyy") or "").strip(),
        }
    }


@router.post("/business-trip/{item_id}/action")
async def business_trip_approve_action(item_id: str, req: ApproveRequest):
    """
    公出单条审批。使用 bldzt/szrzt 状态与 szrpztime/bldpztime 时间。
    - 室主任通过: szrzt=2, szrpztime=now；驳回: szrzt=22, szrpztime=now
    - 部领导通过: bldzt=2, bldpztime=now；驳回: bldzt=22, szrzt=0, bldpztime=now
    """
    rows = db.execute_query(
        "SELECT id, szrzt, bldzt, szr, bld FROM gcsqb WHERE id = %s",
        (item_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    row = rows[0]
    szrzt = int(row.get("szrzt") or 0)
    bldzt = int(row.get("bldzt") or 0)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if req.action == "reject":
        reason = (req.reason or "").strip()
        reason_val = reason[:500] if reason else None
        if szrzt == 1 and bldzt == 1:
            try:
                db.execute_update(
                    "UPDATE gcsqb SET szrzt = 22, szrpztime = %s, bhyy = %s WHERE id = %s",
                    (now, reason_val, item_id)
                )
            except Exception:
                db.execute_update(
                    "UPDATE gcsqb SET szrzt = 22, szrpztime = %s WHERE id = %s",
                    (now, item_id)
                )
        elif szrzt == 2 and bldzt == 1:
            try:
                db.execute_update(
                    "UPDATE gcsqb SET bldzt = 22, szrzt = 0, bldpztime = %s, bhyy = %s WHERE id = %s",
                    (now, reason_val, item_id)
                )
            except Exception:
                db.execute_update(
                    "UPDATE gcsqb SET bldzt = 22, szrzt = 0, bldpztime = %s WHERE id = %s",
                    (now, item_id)
                )
        else:
            raise HTTPException(status_code=400, detail="当前状态无法驳回")
        return {"success": True, "message": "已驳回"}

    if req.action != "approve":
        raise HTTPException(status_code=400, detail="无效操作")

    if szrzt == 1 and bldzt == 1:
        db.execute_update(
            "UPDATE gcsqb SET szrzt = 2, szrpztime = %s WHERE id = %s",
            (now, item_id)
        )
    elif szrzt == 2 and bldzt == 1:
        db.execute_update(
            "UPDATE gcsqb SET bldzt = 2, bldpztime = %s WHERE id = %s",
            (now, item_id)
        )
    else:
        raise HTTPException(status_code=400, detail="当前状态无法审批")

    return {"success": True, "message": "已通过"}


class BatchBusinessTripRequest(BaseModel):
    ids: List[str]
    action: str
    reason: Optional[str] = ""


@router.post("/business-trip/batch")
async def business_trip_batch_approve(req: BatchBusinessTripRequest):
    """公出批量审批（批量 SQL 优化）"""
    ids = [str(i).strip() for i in req.ids if str(i).strip()]
    if not ids:
        return {"success": True, "passed": 0, "failed": 0, "message": "无有效ID"}

    if req.action == "reject":
        ok, fail = 0, 0
        for iid in ids:
            try:
                await business_trip_approve_action(iid, ApproveRequest(action="reject", reason=req.reason))
                ok += 1
            except Exception:
                fail += 1
        return {"success": True, "passed": ok, "failed": fail, "message": f"成功{ok}条，失败{fail}条"}

    ph = ",".join(["%s"] * len(ids))
    rows = db.execute_query(
        f"SELECT id, szrzt, bldzt FROM gcsqb WHERE id IN ({ph})",
        tuple(ids),
    ) or []
    row_map = {str(r["id"]): r for r in rows}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ids_szr_approve = []
    ids_bld_approve = []
    ok, fail = 0, 0

    for iid in ids:
        r = row_map.get(iid)
        if not r:
            fail += 1
            continue
        szrzt = int(r.get("szrzt") or 0)
        bldzt = int(r.get("bldzt") or 0)
        if szrzt == 1 and bldzt == 1:
            ids_szr_approve.append(iid)
            ok += 1
        elif szrzt == 2 and bldzt == 1:
            ids_bld_approve.append(iid)
            ok += 1
        else:
            fail += 1

    if ids_szr_approve:
        p = ",".join(["%s"] * len(ids_szr_approve))
        db.execute_update(
            f"UPDATE gcsqb SET szrzt = 2, szrpztime = %s WHERE id IN ({p})",
            (now,) + tuple(ids_szr_approve),
        )
    if ids_bld_approve:
        p = ",".join(["%s"] * len(ids_bld_approve))
        db.execute_update(
            f"UPDATE gcsqb SET bldzt = 2, bldpztime = %s WHERE id IN ({p})",
            (now,) + tuple(ids_bld_approve),
        )

    return {"success": True, "passed": ok, "failed": fail, "message": f"成功{ok}条，失败{fail}条"}


# ==================== 换休票未读通知 ====================

def _ensure_hxp_read_column():
    """确保 hxp 表有 is_read 列（0=未读 1=已读），不存在时自动添加。"""
    try:
        cols = db.execute_query("SHOW COLUMNS FROM hxp LIKE 'is_read'")
        if not cols:
            db.execute_update(
                "ALTER TABLE hxp ADD COLUMN is_read TINYINT NOT NULL DEFAULT 0"
            )
    except Exception as e:
        logger.warning(f"检查/添加 hxp.is_read 列失败: {e}")

_ensure_hxp_read_column()


@router.get("/hxp/unread")
async def get_unread_hxp(name: str = Query(..., description="员工姓名")):
    """获取指定员工的未读换休票记录（新增的换休票通知）"""
    rows = db.execute_query(
        "SELECT id, name, sl, sj, ly FROM hxp "
        "WHERE name = %s AND (is_read IS NULL OR is_read = 0) AND sl > 0 "
        "ORDER BY sj DESC",
        (name.strip(),),
    )
    items = []
    for r in (rows or []):
        items.append({
            "id": r.get("id") or "",
            "name": r.get("name") or "",
            "sl": float(r.get("sl") or 0),
            "sj": str(r.get("sj") or ""),
            "ly": (r.get("ly") or "").strip() or "系统自动",
        })
    return {"success": True, "data": items, "total": len(items)}


class HxpMarkReadRequest(BaseModel):
    ids: List[str]


@router.post("/hxp/mark-read")
async def mark_hxp_read(req: HxpMarkReadRequest):
    """将指定换休票记录标记为已读"""
    if not req.ids:
        return {"success": True, "updated": 0}
    ph = ",".join(["%s"] * len(req.ids))
    n = db.execute_update(
        f"UPDATE hxp SET is_read = 1 WHERE id IN ({ph})",
        tuple(req.ids),
    )
    return {"success": True, "updated": n}
