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
from utils.helpers import format_datetime_plain
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approval", tags=["审批"])


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
    """检查当前用户是否有审批权限（员工无权限；webconfig.dakaman 打卡管理员始终有权限，用于加班最后一环审批）"""
    name_stripped = (name or "").strip()
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


def _add_exchange_tickets(name: str, tickets: float):
    """加班审批通过且「要换休票」时，向 hxp 表增加换休票。tickets 为张数（已按 0.25 取整）。"""
    if not name or tickets <= 0:
        return
    try:
        tickets = round(float(tickets), 2)
        if tickets <= 0:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # hxp 表若 id 为 VARCHAR(36) NOT NULL 则需显式传入；否则按无 id 列插入
        try:
            hxp_id = uuid.uuid4().hex
            n = db.execute_update(
                "INSERT INTO hxp (id, name, sl, sj) VALUES (%s, %s, %s, %s)",
                (hxp_id, name.strip(), tickets, now),
            )
        except Exception:
            n = db.execute_update(
                "INSERT INTO hxp (name, sl, sj) VALUES (%s, %s, %s)",
                (name.strip(), tickets, now),
            )
        if n <= 0:
            logger.warning("加班换休票入账未生效（INSERT 影响行数为0）")
    except Exception as e:
        logger.warning(f"加班换休票入账失败: {e}")


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


@router.post("/leave/batch")
async def leave_batch_approve(req: BatchApproveRequest):
    """请假批量审批"""
    ok, fail = 0, 0
    for iid in req.ids:
        try:
            await leave_approve_action(iid, ApproveRequest(action=req.action, reason=req.reason))
            ok += 1
        except Exception:
            fail += 1
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
            if isinstance(tf, datetime):
                tf = tf.strftime("%H:%M") if tf else ""
            elif tf and " " in str(tf):
                tf = str(tf).split(" ")[-1][:8]
            else:
                tf = str(tf)[:8] if tf else ""
            if isinstance(tt, datetime):
                tt = tt.strftime("%H:%M") if tt else ""
            elif tt and " " in str(tt):
                tt = str(tt).split(" ")[-1][:8]
            else:
                tt = str(tt)[:8] if tt else ""
            hours = r.get("jbf") or r.get("tian1") or 0
            try:
                hours = float(hours)
            except (TypeError, ValueError):
                hours = 0
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
            "hours": r.get("jbf") or r.get("tian1"),
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
        "SELECT id, jiabanzt, spr2, xm, hx, tian1, jbf FROM jiaban WHERE id = %s",
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
        # 打卡管理员通过后流程结束
        db.execute_update("UPDATE jiaban SET jiabanzt = 4 WHERE id = %s", (item_id,))
        final_approved = True
    else:
        raise HTTPException(status_code=400, detail="当前状态无法审批")

    # 加班最终审批通过：hx=是 写 hxp 表并回写 jiaban.hxp、jiaban.jbf=0；hx=否 只写 jiaban.jbf（来自 tian1），jiaban.hxp=0
    if final_approved:
        hx = (row.get("hx") or row.get("HX") or "").strip()
        need_exchange = hx and str(hx) in ("是", "1", "true", "yes")
        try:
            hours = float(row.get("tian1") or row.get("jbf") or 0)
        except (TypeError, ValueError):
            hours = 0
        xm = (row.get("xm") or "").strip()

        if need_exchange and hours > 0 and xm:
            # 1天=8小时=2张，即 1小时=0.25张；向下取整到 0.25 张
            tickets = math.floor(hours) / 4  # 1小时=0.25张，向下取整到整小时后折算
            if tickets > 0:
                _add_exchange_tickets(xm, tickets)
                db.execute_update(
                    "UPDATE jiaban SET hxp = %s, jbf = 0 WHERE id = %s",
                    (tickets, item_id),
                )
        else:
            # hx=否：只记加班费，回写 jbf（以 tian1 为准），hxp 置 0
            db.execute_update(
                "UPDATE jiaban SET jbf = %s, hxp = 0 WHERE id = %s",
                (hours, item_id),
            )

    return {"success": True, "message": "已通过"}


@router.post("/overtime/batch")
async def overtime_batch_approve(req: BatchApproveRequest):
    """加班批量审批"""
    ok, fail = 0, 0
    for iid in req.ids:
        try:
            await overtime_approve_action(iid, ApproveRequest(action=req.action, reason=req.reason))
            ok += 1
        except Exception:
            fail += 1
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
    """两段时间是否有交集（重叠）"""
    if not all([s1, e1, s2, e2]):
        return False
    return s1 < e2 and s2 < e1


def _interval_contained_in(s_start: str, s_end: str, punch_starts: List[str], punch_ends: List[str]) -> bool:
    """加班区间 [s_start, s_end] 是否被某段打卡区间包含"""
    for p_start, p_end in zip(punch_starts, punch_ends):
        if p_start and p_end and p_start <= s_start and s_end <= p_end:
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
    """
    results = []
    items = req.items or []
    if not items:
        return {"success": True, "results": results}

    # 解析每条为 (id, applicant, start_dt_str, end_dt_str)
    parsed = []
    for it in items:
        start_dt = _parse_overtime_datetime(it.date, it.startTime)
        end_dt = _parse_overtime_datetime(it.date, it.endTime)
        if not start_dt or not end_dt or start_dt >= end_dt:
            results.append({"id": it.id, "pass": False, "reason": "时间无效"})
            continue
        parsed.append((it.id, (it.applicant or "").strip(), start_dt, end_dt))

    # 1) 列表内重复：任意两条重叠则都标为「时间段重复」
    duplicate_ids = set()
    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):
            id_i, _, s1, e1 = parsed[i]
            id_j, _, s2, e2 = parsed[j]
            if _intervals_overlap(s1, e1, s2, e2):
                duplicate_ids.add(id_i)
                duplicate_ids.add(id_j)

    for it in items:
        if it.id in duplicate_ids:
            results.append({"id": it.id, "pass": False, "reason": "时间段重复"})
            continue
        # 找到该条解析
        rec = None
        for p in parsed:
            if p[0] == it.id:
                rec = p
                break
        if not rec:
            continue
        _, applicant, start_dt, end_dt = rec

        # 2) 打卡校验：查该人当日打卡，构建 (time_1,time_2),(time_3,time_4)... 区间，看是否包含
        date_ymd = start_dt[:10]
        try:
            att_records = attendance_db.query_by_date_range(date_ymd, date_ymd, name=applicant)
        except Exception:
            att_records = []
        punch_contained = False
        if att_records:
            for row in att_records:
                punch_starts = []
                punch_ends = []
                for i in range(1, 10, 2):
                    t1 = row.get(f"time_{i}")
                    t2 = row.get(f"time_{i+1}")
                    if t1 is None or t2 is None:
                        continue
                    t1 = format_datetime_plain(t1) if t1 else ""
                    t2 = format_datetime_plain(t2) if t2 else ""
                    if isinstance(t1, str) and " " not in t1 and len(t1) <= 8:
                        t1 = f"{date_ymd} {t1}" if len(t1) > 5 else f"{date_ymd} {t1}:00"
                    if isinstance(t2, str) and " " not in t2 and len(t2) <= 8:
                        t2 = f"{date_ymd} {t2}" if len(t2) > 5 else f"{date_ymd} {t2}:00"
                    if t1 and t2 and t1 < t2:
                        punch_starts.append(t1[:19])
                        punch_ends.append(t2[:19])
                if _interval_contained_in(start_dt, end_dt, punch_starts, punch_ends):
                    punch_contained = True
                    break
        if not punch_contained:
            results.append({"id": it.id, "pass": False, "reason": "打卡不实"})
            continue

        # 3) jiaban 表查重：同人、非本条，时间段重叠
        try:
            other_rows = db.execute_query(
                "SELECT id, timefrom, timeto FROM jiaban WHERE xm = %s AND id != %s",
                (applicant, it.id)
            ) or []
        except Exception:
            other_rows = []
        overlap_with_db = False
        for row in other_rows:
            r_start = format_datetime_plain(row.get("timefrom")) or ""
            r_end = format_datetime_plain(row.get("timeto")) or ""
            if "." in r_start:
                r_start = r_start.split(".")[0]
            if "." in r_end:
                r_end = r_end.split(".")[0]
            if r_start and r_end and _intervals_overlap(start_dt, end_dt, r_start[:19], r_end[:19]):
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
        q1 = """
            SELECT id, wpdw, gcdw, gcdd, gcsj, yjfhsj, tzdbh, gcrw, bld, szr, gcr
            FROM gcsqb WHERE bldzt = 1 AND szrzt = 1 AND szr = %s
        """
        # 二级：部领导待审批（bld=当前用户 即登记时选择的部领导）
        q2 = """
            SELECT id, wpdw, gcdw, gcdd, gcsj, yjfhsj, tzdbh, gcrw, bld, szr, gcr
            FROM gcsqb WHERE bldzt = 1 AND szrzt = 2 AND bld = %s
        """
        try:
            rows1 = db.execute_query(q1, (approver,))
            rows2 = db.execute_query(q2, (approver,))
        except Exception as e:
            if "unknown column" in str(e).lower() and ("bldzt" in str(e) or "szrzt" in str(e)):
                return {"success": True, "data": []}
            raise
        items = []
        for r in rows1:
            items.append({
                "id": str(r["id"]) if r.get("id") is not None else "",
                "applicant": (r.get("gcryxm") or r.get("gcr") or "").strip(),
                "targetUnit": r.get("wpdw") or "",
                "department": r.get("gcdw") or "",
                "location": r.get("gcdd") or "",
                "startTime": _fmt_dt(r.get("gcsj")),
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
                "startTime": _fmt_dt(r.get("gcsj")),
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
            "startTime": _fmt_dt(r.get("gcsj")),
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
    """公出批量审批"""
    ok, fail = 0, 0
    for iid in req.ids:
        try:
            await business_trip_approve_action(iid, ApproveRequest(action=req.action, reason=req.reason))
            ok += 1
        except Exception:
            fail += 1
    return {"success": True, "passed": ok, "failed": fail, "message": f"成功{ok}条，失败{fail}条"}
