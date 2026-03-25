# -*- coding: utf-8 -*-
"""
公出节假日领换休票 API
- 独立数据库表 holiday_exchange
- 表单：姓名、班组、加班时间(日期范围,天级)、佐证材料(必须)
- 自动计算换休票数量 = 加班天数 / 8
- 二级审批：一级(科室主任) -> 二级(部长/副部长) -> 通过; 驳回=22
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Tuple
from collections import Counter
from pydantic import BaseModel
from datetime import datetime, date, timedelta
from database import db
from utils.holiday_loader import load_holidays_for_year
from config import settings
from pathlib import Path
import uuid
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["公出节假日换休票"])

_BASE = Path(__file__).resolve().parent.parent
UPLOAD_HE_MATERIALS = _BASE / settings.UPLOAD_DIR / "holiday_exchange_materials"

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf",
    ".txt", ".zip", ".rar", ".7z", ".wps", ".et", ".dps",
}
MAX_FILE_SIZE = 20 * 1024 * 1024


def _ensure_upload_dir():
    UPLOAD_HE_MATERIALS.mkdir(parents=True, exist_ok=True)


def _ensure_table():
    sql = """
    CREATE TABLE IF NOT EXISTS holiday_exchange (
        id VARCHAR(36) PRIMARY KEY,
        bz VARCHAR(100) COMMENT '班组',
        xm VARCHAR(50) COMMENT '姓名',
        date_from DATE COMMENT '加班开始日期',
        date_to DATE COMMENT '加班结束日期',
        days INT COMMENT '加班天数',
        hxp_count DECIMAL(10,4) COMMENT '换休票数量',
        material_files TEXT COMMENT '佐证材料文件名JSON',
        spr VARCHAR(50) COMMENT '一级审批人',
        spr2 VARCHAR(50) COMMENT '二级审批人',
        status INT DEFAULT 0 COMMENT '0待一级,1待二级,4通过,22驳回',
        bhyy VARCHAR(500) COMMENT '驳回原因',
        apply_time DATETIME COMMENT '申请时间',
        lsys VARCHAR(100) COMMENT '隶属室'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """
    try:
        db.execute_update(sql)
    except Exception as e:
        logger.warning("创建 holiday_exchange 表失败(可能已存在): %s", e)


_ensure_table()


def _normalize_date_key(s: str) -> str:
    """与 holiday 表、前端统一的 YYYY-MM-DD 键"""
    raw = str(s).strip()[:10]
    parts = raw.split("-")
    if len(parts) != 3:
        return raw
    y, m, d = parts[0], parts[1].zfill(2), parts[2].zfill(2)
    return f"{y}-{m}-{d}"


def _merge_holiday_type_map(years: set) -> dict:
    """多年份 date_str -> type（与统计模块工作日逻辑同源数据）"""
    merged: dict = {}
    for y in years:
        for row in load_holidays_for_year(str(y)):
            d = row.get("date")
            if not d:
                continue
            k = _normalize_date_key(d)
            merged[k] = (row.get("type") or "").strip()
    return merged


def _merge_festival_map(years: set) -> Dict[str, str]:
    """多年份 date_str -> 节日名称（holiday.festival）"""
    merged: Dict[str, str] = {}
    for y in years:
        for row in load_holidays_for_year(str(y)):
            d = row.get("date")
            if not d:
                continue
            k = _normalize_date_key(d)
            fest = (row.get("festival") or "").strip()
            if fest:
                merged[k] = fest
    return merged


_WEEKDAY_CN = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def _describe_each_rest_day(d: date, type_map: dict, festival_map: dict) -> str:
    """单日说明：日期+星期+性质（周末/节日名/类型）"""
    date_str = d.strftime("%Y-%m-%d")
    wd = _WEEKDAY_CN[d.weekday()]
    t = type_map.get(date_str, "") or ""
    is_weekend = d.weekday() >= 5
    if t and "班" in t:
        return f"{date_str}（{wd}）·补班"
    if is_weekend:
        return f"{date_str}（{wd}）·周末"
    fest = festival_map.get(date_str, "")
    if fest:
        return f"{date_str}（{wd}）·{fest}"
    if t:
        return f"{date_str}（{wd}）·{t}"
    return f"{date_str}（{wd}）·周末"


def _summarize_rest_day_lines(lines: List[str]) -> str:
    """审批列表用短摘要：按性质统计天数"""
    if not lines:
        return ""
    kinds = []
    for line in lines:
        if "·" in line:
            kinds.append(line.split("·")[-1].strip())
        else:
            kinds.append("其它")
    cnt = Counter(kinds)
    parts = [f"「{k}」{n}天" for k, n in cnt.most_common()]
    return f"共{len(lines)}天：" + "，".join(parts)


def holiday_exchange_rest_day_info(date_from, date_to) -> Tuple[List[str], str]:
    """
    根据假期表解析区间内每日性质。
    返回 (逐日说明列表, 汇总句)
    """
    try:
        d1 = datetime.strptime(str(date_from)[:10], "%Y-%m-%d").date()
        d2 = datetime.strptime(str(date_to)[:10], "%Y-%m-%d").date()
    except Exception:
        return [], ""
    if d2 < d1:
        return [], ""
    years = set()
    cur = d1
    while cur <= d2:
        years.add(cur.year)
        cur += timedelta(days=1)
    type_map = _merge_holiday_type_map(years)
    festival_map = _merge_festival_map(years)
    lines: List[str] = []
    cur = d1
    while cur <= d2:
        lines.append(_describe_each_rest_day(cur, type_map, festival_map))
        cur += timedelta(days=1)
    return lines, _summarize_rest_day_lines(lines)


def _is_company_rest_day(d: date, holidays: dict) -> bool:
    """
    是否为公司「节假日/休息日」：周六日，或 holiday 表中标记为放假/调休（含「假」「休」），
    且非补班（type 含「班」时与 statistics 一致视为工作日）。
    """
    date_str = d.strftime("%Y-%m-%d")
    weekday = d.weekday()  # 周一=0 … 周日=6
    is_weekend = weekday >= 5
    t = holidays.get(date_str, "") or ""
    if t and "班" in t:
        return False
    if is_weekend:
        return True
    if t and ("假" in t or "休" in t):
        return True
    return False


def _coerce_to_datetime(val) -> Optional[datetime]:
    """将数据库/字符串时间转为 datetime，便于与公出区间比较。"""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime.combine(val, datetime.min.time())
    s = str(val).strip().replace("T", " ")
    if len(s) >= 19:
        s19 = s[:19]
        for fmt in ("%Y-%m-%d %H:%M:%S",):
            try:
                return datetime.strptime(s19, fmt)
            except ValueError:
                pass
    if len(s) >= 16 and s[10] == " ":
        try:
            return datetime.strptime(s[:16], "%Y-%m-%d %H:%M")
        except ValueError:
            pass
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _gcsqb_trip_date_bounds(row: dict) -> Optional[Tuple[date, date]]:
    """
    公出单在日历上的起止日期（含首尾日），与智能建议等一致：
    开始：yjcfsj → gcsj → wpsj；结束：yjfhsj → sjfhtime → 再回退到开始侧字段。
    """
    start_dt = (
        _coerce_to_datetime(row.get("yjcfsj"))
        or _coerce_to_datetime(row.get("gcsj"))
        or _coerce_to_datetime(row.get("wpsj"))
    )
    if start_dt is None:
        return None
    end_dt = (
        _coerce_to_datetime(row.get("yjfhsj"))
        or _coerce_to_datetime(row.get("sjfhtime"))
        or _coerce_to_datetime(row.get("yjcfsj"))
        or _coerce_to_datetime(row.get("gcsj"))
        or _coerce_to_datetime(row.get("wpsj"))
    )
    if end_dt is None or end_dt.date() < start_dt.date():
        end_dt = start_dt
    return start_dt.date(), end_dt.date()


def _validate_gcsqb_covers_range(applicant: str, d_from: date, d_to: date) -> None:
    """
    申请人须存在至少一条已双审通过的 gcsqb，且其 yjcfsj～yjfhsj（按日历日）
    完全覆盖所选的换休票日期区间 [d_from, d_to]。
    """
    name_clean = (applicant or "").strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="姓名不能为空")

    sql = (
        "SELECT yjcfsj, yjfhsj, gcsj, sjfhtime, wpsj FROM gcsqb "
        "WHERE TRIM(gcr) = %s "
        "AND COALESCE(bldzt, 0) = 2 AND COALESCE(szrzt, 0) = 2 "
        "AND COALESCE(bldzt, 0) != 22 AND COALESCE(szrzt, 0) != 22"
    )
    try:
        rows = db.execute_query(sql, (name_clean,)) or []
    except Exception as e:
        err = str(e).lower()
        if "unknown column" in err:
            sql_legacy = (
                "SELECT gcsj, yjfhsj, wpsj, sjfhtime FROM gcsqb "
                "WHERE TRIM(gcr) = %s "
                "AND COALESCE(bldzt, 0) = 2 AND COALESCE(szrzt, 0) = 2 "
                "AND COALESCE(bldzt, 0) != 22 AND COALESCE(szrzt, 0) != 22"
            )
            try:
                rows = db.execute_query(sql_legacy, (name_clean,)) or []
            except Exception as e2:
                logger.warning("校验公出单失败(legacy): %s", e2)
                raise HTTPException(status_code=500, detail="校验公出记录失败，请稍后重试") from e2
        else:
            logger.warning("查询 gcsqb 失败: %s", e)
            raise HTTPException(status_code=500, detail="校验公出记录失败，请稍后重试") from e

    if not rows:
        raise HTTPException(
            status_code=400,
            detail="未找到您已审批通过的公出申请。请先在「公出管理」中申报并完成部领导、室主任审批后，再申请公出节假日换休票。",
        )

    for row in rows:
        bounds = _gcsqb_trip_date_bounds(row)
        if bounds is None:
            continue
        trip_start, trip_end = bounds
        if trip_start <= d_from and trip_end >= d_to:
            return

    raise HTTPException(
        status_code=400,
        detail=(
            f"所选日期 {d_from} 至 {d_to} 未完全落在任一条已审批公出的「预计出发～预计返回」日期范围内。"
            "请核对公出单上的时间与本次填报区间是否一致，或先补办公出申请。"
        ),
    )


def _validate_holiday_exchange_range(d1: date, d2: date) -> None:
    """区间内每一天须为周末或公司节假日，否则 400"""
    if d2 < d1:
        raise HTTPException(status_code=400, detail="截止日期不能早于起始日期")
    years = set()
    cur = d1
    while cur <= d2:
        years.add(cur.year)
        cur += timedelta(days=1)
    holidays = _merge_holiday_type_map(years)
    invalid: List[str] = []
    cur = d1
    while cur <= d2:
        if not _is_company_rest_day(cur, holidays):
            invalid.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    if not invalid:
        return
    sample = invalid[:8]
    msg = (
        "公出节假日换休票仅可选择周末及公司节假日（以假期与调休表为准）。"
        f"以下日期为工作日或非放假安排，请调整区间：{', '.join(sample)}"
    )
    if len(invalid) > 8:
        msg += f" 等共 {len(invalid)} 天"
    raise HTTPException(status_code=400, detail=msg)


def _calc_days(date_from: str, date_to: str) -> int:
    """日期范围天数(含首尾)"""
    try:
        d1 = datetime.strptime(date_from[:10], "%Y-%m-%d").date()
        d2 = datetime.strptime(date_to[:10], "%Y-%m-%d").date()
        return max(1, (d2 - d1).days + 1)
    except Exception:
        return 0


def _add_exchange_tickets(name: str, tickets: float):
    """向 hxp 表增加换休票"""
    if not name or tickets <= 0:
        return
    try:
        tickets = round(float(tickets), 2)
        if tickets <= 0:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            hxp_id = uuid.uuid4().hex
            db.execute_update(
                "INSERT INTO hxp (id, name, sl, sj) VALUES (%s, %s, %s, %s)",
                (hxp_id, name.strip(), tickets, now),
            )
        except Exception:
            db.execute_update(
                "INSERT INTO hxp (name, sl, sj) VALUES (%s, %s, %s)",
                (name.strip(), tickets, now),
            )
    except Exception as e:
        logger.warning("公出节假日换休票入账失败: %s", e)


# ==================== CRUD ====================


@router.post("/holiday-exchange/apply")
async def submit_holiday_exchange(
    name: str = Form(...),
    department: str = Form(""),
    dateFrom: str = Form(...),
    dateTo: str = Form(...),
    approver1: str = Form(...),
    approver2: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """提交公出节假日换休票申请"""
    try:
        if not (name or "").strip():
            raise HTTPException(status_code=400, detail="姓名不能为空")
        if not dateFrom or not dateTo:
            raise HTTPException(status_code=400, detail="请选择加班时间范围")
        if not (approver1 or "").strip():
            raise HTTPException(status_code=400, detail="请选择一级审批人")
        if not (approver2 or "").strip():
            raise HTTPException(status_code=400, detail="请选择二级审批人")
        if not files:
            raise HTTPException(status_code=400, detail="请上传佐证材料")

        try:
            d_from = datetime.strptime(dateFrom[:10], "%Y-%m-%d").date()
            d_to = datetime.strptime(dateTo[:10], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="加班日期格式无效")
        _validate_holiday_exchange_range(d_from, d_to)
        _validate_gcsqb_covers_range((name or "").strip(), d_from, d_to)

        _ensure_upload_dir()
        saved_files = []
        for f in files:
            if not f.filename:
                continue
            ext = Path(f.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")
            content = await f.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"文件 {f.filename} 超过 20MB 限制")
            safe_name = f"he_{uuid.uuid4().hex[:12]}{ext}"
            save_path = UPLOAD_HE_MATERIALS / safe_name
            with open(save_path, "wb") as fp:
                fp.write(content)
            saved_files.append({"name": safe_name, "original": f.filename})

        if not saved_files:
            raise HTTPException(status_code=400, detail="请上传佐证材料")

        days = _calc_days(dateFrom, dateTo)
        if days <= 0:
            raise HTTPException(status_code=400, detail="加班日期范围无效")
        hxp_count = round(days / 8, 4)

        bz = (department or "").strip()
        lsys = ""
        name_clean = name.strip()
        if name_clean:
            rows = db.execute_query(
                "SELECT lsys FROM yggl WHERE name = %s LIMIT 1", (name_clean,)
            )
            if rows:
                lsys = (rows[0].get("lsys") or "").strip()
                if not bz:
                    bz = lsys

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_id = uuid.uuid4().hex

        sql = """
            INSERT INTO holiday_exchange
                (id, bz, xm, date_from, date_to, days, hxp_count,
                 material_files, spr, spr2, status, apply_time, lsys)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s)
        """
        params = (
            new_id, bz, name_clean,
            dateFrom[:10], dateTo[:10], days, hxp_count,
            json.dumps(saved_files, ensure_ascii=False),
            approver1.strip(), approver2.strip(),
            now, lsys,
        )
        db.execute_update(sql, params)

        return {
            "success": True,
            "message": "申请已提交",
            "id": new_id,
            "days": days,
            "hxp_count": hxp_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("公出节假日换休票申请失败: %s", e)
        raise HTTPException(status_code=500, detail=f"提交失败: {e}")


@router.get("/holiday-exchange/list")
async def get_holiday_exchange_list(
    name: str = Query(...),
    year: Optional[int] = None,
    month: Optional[int] = None,
    status: Optional[str] = Query("all"),
    scope: str = Query("self"),
):
    """获取公出节假日换休票记录列表"""
    try:
        conds: list[str] = []
        params: list = []

        if scope == "self":
            conds.append("xm = %s")
            params.append(name.strip())
        elif scope == "lsys":
            rows = db.execute_query(
                "SELECT lsys FROM yggl WHERE name = %s LIMIT 1", (name.strip(),)
            )
            lsys = (rows[0].get("lsys") or "").strip() if rows else ""
            if lsys:
                conds.append("lsys = %s")
                params.append(lsys)
            else:
                conds.append("xm = %s")
                params.append(name.strip())

        if year:
            conds.append("YEAR(apply_time) = %s")
            params.append(year)
        if month:
            conds.append("MONTH(apply_time) = %s")
            params.append(month)

        if status == "processing":
            conds.append("status IN (0, 1)")
        elif status == "approved":
            conds.append("status = 4")
        elif status == "rejected":
            conds.append("status = 22")

        where = " AND ".join(conds) if conds else "1=1"
        sql = f"SELECT * FROM holiday_exchange WHERE {where} ORDER BY apply_time DESC"
        rows = db.execute_query(sql, tuple(params))

        STATUS_TEXT = {0: "待一级审批", 1: "待二级审批", 4: "已通过", 22: "已驳回"}
        STATUS_CLASS = {
            0: "status-processing", 1: "status-processing",
            4: "status-approved", 22: "status-rejected",
        }

        data = []
        for r in rows:
            files = []
            try:
                files = json.loads(r.get("material_files") or "[]")
            except Exception:
                pass

            sv = r.get("status") or 0
            cur = ""
            if sv == 0:
                cur = r.get("spr") or ""
            elif sv == 1:
                cur = r.get("spr2") or ""

            df, dt = r.get("date_from"), r.get("date_to")
            brk, smy = holiday_exchange_rest_day_info(df, dt)
            data.append({
                "id": r.get("id"),
                "department": r.get("bz") or "",
                "applicant": r.get("xm") or "",
                "dateFrom": str(df or ""),
                "dateTo": str(dt or ""),
                "days": r.get("days") or 0,
                "hxpCount": float(r.get("hxp_count") or 0),
                "materialFiles": files,
                "status": STATUS_TEXT.get(sv, "未知"),
                "statusClass": STATUS_CLASS.get(sv, ""),
                "statusCode": sv,
                "currentApprover": cur,
                "rejectReason": r.get("bhyy") or "",
                "applyTime": str(r.get("apply_time") or "")[:19],
                "spr": r.get("spr") or "",
                "spr2": r.get("spr2") or "",
                "restDayBreakdown": brk,
                "restDaySummary": smy,
            })

        return {"success": True, "data": data}
    except Exception as e:
        logger.error("获取公出节假日换休票列表失败: %s", e)
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@router.delete("/holiday-exchange/{item_id}")
async def delete_holiday_exchange(item_id: str, name: str = Query(...)):
    """删除已驳回的记录"""
    try:
        rows = db.execute_query(
            "SELECT id, xm, status FROM holiday_exchange WHERE id = %s", (item_id,)
        )
        if not rows:
            raise HTTPException(status_code=404, detail="记录不存在")
        r = rows[0]
        if r.get("status") != 22:
            raise HTTPException(status_code=400, detail="仅可删除已驳回的记录")
        if (r.get("xm") or "").strip() != name.strip():
            raise HTTPException(status_code=403, detail="只能删除本人的记录")
        db.execute_update("DELETE FROM holiday_exchange WHERE id = %s", (item_id,))
        return {"success": True, "message": "已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("删除记录失败: %s", e)
        raise HTTPException(status_code=500, detail="删除失败")


@router.get("/holiday-exchange/download/{filename}")
async def download_material(filename: str):
    """下载佐证材料"""
    file_path = UPLOAD_HE_MATERIALS / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path=str(file_path), filename=filename)


# ==================== 审批 ====================


@router.get("/approval/pending/holiday-exchange")
async def get_pending_holiday_exchange(approver: str = Query(...)):
    """获取待审批列表"""
    try:
        query = """
            SELECT * FROM holiday_exchange
            WHERE (status = 0 AND spr = %s) OR (status = 1 AND spr2 = %s)
            ORDER BY apply_time DESC
        """
        rows = db.execute_query(query, (approver, approver))

        data = []
        for r in rows:
            files = []
            try:
                files = json.loads(r.get("material_files") or "[]")
            except Exception:
                pass
            sv = r.get("status") or 0
            df, dt = r.get("date_from"), r.get("date_to")
            brk, smy = holiday_exchange_rest_day_info(df, dt)
            data.append({
                "id": r.get("id"),
                "applicant": r.get("xm") or "",
                "department": r.get("bz") or "",
                "dateFrom": str(df or ""),
                "dateTo": str(dt or ""),
                "days": r.get("days") or 0,
                "hxpCount": float(r.get("hxp_count") or 0),
                "materialFiles": files,
                "approvalLevel": "一级审批" if sv == 0 else "二级审批",
                "applyTime": str(r.get("apply_time") or "")[:19],
                "restDayBreakdown": brk,
                "restDaySummary": smy,
            })
        return {"success": True, "data": data}
    except Exception as e:
        logger.error("获取待审批列表失败: %s", e)
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@router.get("/approval/holiday-exchange/{item_id}")
async def get_holiday_exchange_detail(item_id: str):
    """获取详情"""
    rows = db.execute_query(
        "SELECT * FROM holiday_exchange WHERE id = %s", (item_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    r = rows[0]
    files = []
    try:
        files = json.loads(r.get("material_files") or "[]")
    except Exception:
        pass
    df, dt = r.get("date_from"), r.get("date_to")
    brk, smy = holiday_exchange_rest_day_info(df, dt)
    return {
        "success": True,
        "data": {
            "id": r.get("id"),
            "applicant": r.get("xm") or "",
            "department": r.get("bz") or "",
            "dateFrom": str(df or ""),
            "dateTo": str(dt or ""),
            "days": r.get("days") or 0,
            "hxpCount": float(r.get("hxp_count") or 0),
            "materialFiles": files,
            "spr": r.get("spr") or "",
            "spr2": r.get("spr2") or "",
            "status": r.get("status") or 0,
            "rejectReason": r.get("bhyy") or "",
            "applyTime": str(r.get("apply_time") or "")[:19],
            "restDayBreakdown": brk,
            "restDaySummary": smy,
        },
    }


class _ApproveReq(BaseModel):
    action: str
    reason: Optional[str] = ""
    approver: Optional[str] = None


@router.post("/approval/holiday-exchange/{item_id}/action")
async def holiday_exchange_approve(item_id: str, req: _ApproveReq):
    """单条审批"""
    rows = db.execute_query(
        "SELECT id, status, xm, hxp_count FROM holiday_exchange WHERE id = %s",
        (item_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    row = rows[0]
    sv = row.get("status") or 0

    if req.action == "reject":
        reason = (req.reason or "").strip()
        db.execute_update(
            "UPDATE holiday_exchange SET status = 22, bhyy = %s WHERE id = %s",
            (reason[:500] if reason else None, item_id),
        )
        return {"success": True, "message": "已驳回"}

    if req.action != "approve":
        raise HTTPException(status_code=400, detail="无效操作")

    if sv == 0:
        db.execute_update(
            "UPDATE holiday_exchange SET status = 1 WHERE id = %s", (item_id,)
        )
        return {"success": True, "message": "一级审批已通过，等待二级审批"}
    elif sv == 1:
        db.execute_update(
            "UPDATE holiday_exchange SET status = 4 WHERE id = %s", (item_id,)
        )
        xm = (row.get("xm") or "").strip()
        hxp = float(row.get("hxp_count") or 0)
        if xm and hxp > 0:
            _add_exchange_tickets(xm, hxp)
        return {"success": True, "message": "审批已通过"}
    else:
        raise HTTPException(status_code=400, detail="当前状态无法审批")


class _BatchReq(BaseModel):
    ids: List[str]
    action: str
    reason: Optional[str] = ""
    approver: Optional[str] = None


@router.post("/approval/holiday-exchange/batch")
async def holiday_exchange_batch(req: _BatchReq):
    """批量审批"""
    ok, fail = 0, 0
    for iid in req.ids:
        try:
            await holiday_exchange_approve(
                iid,
                _ApproveReq(action=req.action, reason=req.reason, approver=req.approver),
            )
            ok += 1
        except Exception:
            fail += 1
    return {
        "success": True,
        "passed": ok,
        "failed": fail,
        "message": f"成功{ok}条，失败{fail}条",
    }
