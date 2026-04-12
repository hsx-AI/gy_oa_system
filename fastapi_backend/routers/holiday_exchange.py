# -*- coding: utf-8 -*-
"""
公出节假日领换休票 API
- 独立数据库表 holiday_exchange
- 表单：姓名、班组、加班时间(日期范围,天级)、佐证材料(必须)
- 自动计算换休票数量 = 加班天数 / 4
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

# 新增 date_ranges 列（JSON 存多段时间）
try:
    db.execute_update(
        "ALTER TABLE holiday_exchange ADD COLUMN date_ranges TEXT COMMENT '多时间段JSON [{from,to},...]'"
    )
except Exception:
    pass


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


def holiday_exchange_rest_day_info(date_from, date_to, date_ranges_json=None) -> Tuple[List[str], str]:
    """
    根据假期表解析区间内每日性质。支持多时间段（date_ranges_json）。
    返回 (逐日说明列表, 汇总句)
    """
    ranges = []
    if date_ranges_json:
        try:
            parsed = json.loads(date_ranges_json) if isinstance(date_ranges_json, str) else date_ranges_json
            if isinstance(parsed, list):
                for seg in parsed:
                    try:
                        r_from = datetime.strptime(str(seg.get("from", ""))[:10], "%Y-%m-%d").date()
                        r_to = datetime.strptime(str(seg.get("to", ""))[:10], "%Y-%m-%d").date()
                        if r_to >= r_from:
                            ranges.append((r_from, r_to))
                    except Exception:
                        pass
        except Exception:
            pass

    if not ranges:
        try:
            d1 = datetime.strptime(str(date_from)[:10], "%Y-%m-%d").date()
            d2 = datetime.strptime(str(date_to)[:10], "%Y-%m-%d").date()
            if d2 >= d1:
                ranges.append((d1, d2))
        except Exception:
            return [], ""

    if not ranges:
        return [], ""

    years = set()
    for d1, d2 in ranges:
        cur = d1
        while cur <= d2:
            years.add(cur.year)
            cur += timedelta(days=1)
    type_map = _merge_holiday_type_map(years)
    festival_map = _merge_festival_map(years)

    lines: List[str] = []
    for i, (d1, d2) in enumerate(ranges):
        if len(ranges) > 1:
            lines.append(f"--- 第{i + 1}段: {d1} 至 {d2} ---")
        cur = d1
        while cur <= d2:
            lines.append(_describe_each_rest_day(cur, type_map, festival_map))
            cur += timedelta(days=1)
    return lines, _summarize_rest_day_lines([l for l in lines if not l.startswith("---")])


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


def _calc_midpoint_date(date_from, date_to) -> str:
    """取 date_from 与 date_to 的中间日期，返回 YYYY-MM-DD 格式；失败时返回空串。"""
    try:
        d1 = date_from if isinstance(date_from, date) else datetime.strptime(str(date_from)[:10], "%Y-%m-%d").date()
        d2 = date_to if isinstance(date_to, date) else datetime.strptime(str(date_to)[:10], "%Y-%m-%d").date()
        mid = d1 + timedelta(days=(d2 - d1).days // 2)
        return mid.strftime("%Y-%m-%d")
    except Exception:
        return ""


def _add_exchange_tickets(name: str, tickets: float, ly: str = "公出节假日换休", sj: str = ""):
    """向 hxp 表增加换休票。sj 为自定义时间（空则取当前时间）。"""
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
            db.execute_update(
                "INSERT INTO hxp (id, name, sl, sj, ly) VALUES (%s, %s, %s, %s, %s)",
                (hxp_id, name.strip(), tickets, sj_val, ly_val),
            )
        except Exception:
            db.execute_update(
                "INSERT INTO hxp (name, sl, sj, ly) VALUES (%s, %s, %s, %s)",
                (name.strip(), tickets, sj_val, ly_val),
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
    dateRanges: str = Form(""),
):
    """提交公出节假日换休票申请（支持多时间段）"""
    try:
        if not (name or "").strip():
            raise HTTPException(status_code=400, detail="姓名不能为空")
        if not (approver1 or "").strip():
            raise HTTPException(status_code=400, detail="请选择一级审批人")
        if not (approver2 or "").strip():
            raise HTTPException(status_code=400, detail="请选择二级审批人")
        if not files:
            raise HTTPException(status_code=400, detail="请上传佐证材料")

        ranges: List[Tuple[date, date]] = []
        date_ranges_json = (dateRanges or "").strip()
        if date_ranges_json:
            try:
                parsed = json.loads(date_ranges_json)
                if isinstance(parsed, list) and len(parsed) > 0:
                    for seg in parsed:
                        seg_from = str(seg.get("from", ""))[:10]
                        seg_to = str(seg.get("to", ""))[:10]
                        try:
                            r_from = datetime.strptime(seg_from, "%Y-%m-%d").date()
                            r_to = datetime.strptime(seg_to, "%Y-%m-%d").date()
                            if r_to < r_from:
                                raise HTTPException(status_code=400, detail=f"时间段 {seg_from} ~ {seg_to} 截止日期不能早于起始日期")
                            ranges.append((r_from, r_to))
                        except ValueError:
                            raise HTTPException(status_code=400, detail=f"日期格式无效: {seg_from} ~ {seg_to}")
            except json.JSONDecodeError:
                pass

        if not ranges:
            if not dateFrom or not dateTo:
                raise HTTPException(status_code=400, detail="请选择加班时间范围")
            try:
                d_from = datetime.strptime(dateFrom[:10], "%Y-%m-%d").date()
                d_to = datetime.strptime(dateTo[:10], "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="加班日期格式无效")
            ranges.append((d_from, d_to))
            date_ranges_json = ""

        name_clean = name.strip()

        total_days = 0
        for r_from, r_to in ranges:
            _validate_holiday_exchange_range(r_from, r_to)
            _validate_gcsqb_covers_range(name_clean, r_from, r_to)
            total_days += (r_to - r_from).days + 1

        if total_days <= 0:
            raise HTTPException(status_code=400, detail="加班日期范围无效")
        hxp_count = round(total_days / 4, 4)

        overall_from = min(r[0] for r in ranges).strftime("%Y-%m-%d")
        overall_to = max(r[1] for r in ranges).strftime("%Y-%m-%d")

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

        bz = (department or "").strip()
        lsys = ""
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

        stored_ranges = json.dumps(
            [{"from": r[0].strftime("%Y-%m-%d"), "to": r[1].strftime("%Y-%m-%d")} for r in ranges],
            ensure_ascii=False,
        ) if len(ranges) > 1 or date_ranges_json else None

        sql = """
            INSERT INTO holiday_exchange
                (id, bz, xm, date_from, date_to, days, hxp_count,
                 material_files, spr, spr2, status, apply_time, lsys, date_ranges)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s)
        """
        params = (
            new_id, bz, name_clean,
            overall_from, overall_to, total_days, hxp_count,
            json.dumps(saved_files, ensure_ascii=False),
            approver1.strip(), approver2.strip(),
            now, lsys, stored_ranges,
        )
        db.execute_update(sql, params)

        return {
            "success": True,
            "message": "申请已提交",
            "id": new_id,
            "days": total_days,
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
    filter_lsys: Optional[str] = Query(None, description="按科室筛选（scope=all时生效）"),
    filter_name: Optional[str] = Query(None, description="按姓名关键字筛选"),
):
    """获取公出节假日换休票记录列表"""
    try:
        conds: list[str] = []
        params: list = []

        if scope == "self":
            conds.append("xm = %s")
            params.append(name.strip())
        elif scope == "all":
            if filter_lsys:
                conds.append("lsys = %s")
                params.append(filter_lsys.strip())
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

        if filter_name and filter_name.strip():
            conds.append("xm LIKE %s")
            params.append(f"%{filter_name.strip()}%")

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
            dr_raw = r.get("date_ranges")
            brk, smy = holiday_exchange_rest_day_info(df, dt, dr_raw)

            dr_list = None
            if dr_raw:
                try:
                    dr_list = json.loads(dr_raw) if isinstance(dr_raw, str) else dr_raw
                except Exception:
                    pass

            data.append({
                "id": r.get("id"),
                "department": r.get("bz") or "",
                "applicant": r.get("xm") or "",
                "dateFrom": str(df or ""),
                "dateTo": str(dt or ""),
                "dateRanges": dr_list,
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


@router.post("/holiday-exchange/{item_id}/resubmit")
async def resubmit_holiday_exchange(
    item_id: str,
    name: str = Form(...),
    department: str = Form(""),
    dateFrom: str = Form(...),
    dateTo: str = Form(...),
    approver1: str = Form(...),
    approver2: str = Form(...),
    files: List[UploadFile] = File(default=[]),
    dateRanges: str = Form(""),
    keepExistingFiles: str = Form("true"),
):
    """修改并重新提交已驳回的换休票申请（status 22→0，更新字段）"""
    try:
        rows = db.execute_query(
            "SELECT id, xm, status, material_files FROM holiday_exchange WHERE id = %s", (item_id,)
        )
        if not rows:
            raise HTTPException(status_code=404, detail="记录不存在")
        r = rows[0]
        if r.get("status") != 22:
            raise HTTPException(status_code=400, detail="仅可重新提交已驳回的记录")
        if (r.get("xm") or "").strip() != name.strip():
            raise HTTPException(status_code=403, detail="只能重新提交本人的记录")

        if not (approver1 or "").strip():
            raise HTTPException(status_code=400, detail="请选择一级审批人")
        if not (approver2 or "").strip():
            raise HTTPException(status_code=400, detail="请选择二级审批人")

        ranges: List[Tuple[date, date]] = []
        date_ranges_json = (dateRanges or "").strip()
        if date_ranges_json:
            try:
                parsed = json.loads(date_ranges_json)
                if isinstance(parsed, list) and len(parsed) > 0:
                    for seg in parsed:
                        seg_from = str(seg.get("from", ""))[:10]
                        seg_to = str(seg.get("to", ""))[:10]
                        r_from = datetime.strptime(seg_from, "%Y-%m-%d").date()
                        r_to = datetime.strptime(seg_to, "%Y-%m-%d").date()
                        ranges.append((r_from, r_to))
            except (json.JSONDecodeError, ValueError):
                pass
        if not ranges:
            d_from = datetime.strptime(dateFrom[:10], "%Y-%m-%d").date()
            d_to = datetime.strptime(dateTo[:10], "%Y-%m-%d").date()
            ranges.append((d_from, d_to))
            date_ranges_json = ""

        name_clean = name.strip()
        total_days = 0
        for r_from, r_to in ranges:
            _validate_holiday_exchange_range(r_from, r_to)
            _validate_gcsqb_covers_range(name_clean, r_from, r_to)
            total_days += (r_to - r_from).days + 1
        if total_days <= 0:
            raise HTTPException(status_code=400, detail="加班日期范围无效")
        hxp_count = round(total_days / 4, 4)

        overall_from = min(r_item[0] for r_item in ranges).strftime("%Y-%m-%d")
        overall_to = max(r_item[1] for r_item in ranges).strftime("%Y-%m-%d")

        has_new_files = files and any(f.filename for f in files)
        if has_new_files:
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
            material_json = json.dumps(saved_files, ensure_ascii=False)
        else:
            material_json = r.get("material_files") or "[]"

        bz = (department or "").strip()
        lsys = ""
        if name_clean:
            emp_rows = db.execute_query("SELECT lsys FROM yggl WHERE name = %s LIMIT 1", (name_clean,))
            if emp_rows:
                lsys = (emp_rows[0].get("lsys") or "").strip()
                if not bz:
                    bz = lsys

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stored_ranges = json.dumps(
            [{"from": rng[0].strftime("%Y-%m-%d"), "to": rng[1].strftime("%Y-%m-%d")} for rng in ranges],
            ensure_ascii=False,
        ) if len(ranges) > 1 or date_ranges_json else None

        db.execute_update(
            """UPDATE holiday_exchange SET
                bz=%s, date_from=%s, date_to=%s, days=%s, hxp_count=%s,
                material_files=%s, spr=%s, spr2=%s, status=0, apply_time=%s,
                lsys=%s, date_ranges=%s, bhyy=NULL
               WHERE id=%s AND status=22 AND xm=%s""",
            (bz, overall_from, overall_to, total_days, hxp_count,
             material_json, approver1.strip(), approver2.strip(),
             now, lsys, stored_ranges,
             item_id, name_clean)
        )
        return {"success": True, "message": "已重新提交", "days": total_days, "hxp_count": hxp_count}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("重新提交换休票失败: %s", e)
        raise HTTPException(status_code=500, detail=f"重新提交失败: {e}")


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
            dr_raw = r.get("date_ranges")
            brk, smy = holiday_exchange_rest_day_info(df, dt, dr_raw)
            dr_list = None
            if dr_raw:
                try:
                    dr_list = json.loads(dr_raw) if isinstance(dr_raw, str) else dr_raw
                except Exception:
                    pass
            data.append({
                "id": r.get("id"),
                "applicant": r.get("xm") or "",
                "department": r.get("bz") or "",
                "dateFrom": str(df or ""),
                "dateTo": str(dt or ""),
                "dateRanges": dr_list,
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
    dr_raw = r.get("date_ranges")
    brk, smy = holiday_exchange_rest_day_info(df, dt, dr_raw)
    dr_list = None
    if dr_raw:
        try:
            dr_list = json.loads(dr_raw) if isinstance(dr_raw, str) else dr_raw
        except Exception:
            pass
    return {
        "success": True,
        "data": {
            "id": r.get("id"),
            "applicant": r.get("xm") or "",
            "department": r.get("bz") or "",
            "dateFrom": str(df or ""),
            "dateTo": str(dt or ""),
            "dateRanges": dr_list,
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
        "SELECT id, status, xm, hxp_count, date_from, date_to FROM holiday_exchange WHERE id = %s",
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
            mid_sj = _calc_midpoint_date(row.get("date_from"), row.get("date_to"))
            _add_exchange_tickets(xm, hxp, sj=mid_sj)
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


# ==================== 换休票汇总明细（公出 + 值班） ====================

@router.get("/holiday-exchange/summary")
async def get_holiday_exchange_summary(
    name: str = Query(...),
    year: Optional[int] = None,
    month: Optional[int] = Query(None, description="月份筛选 1-12，不传则全年"),
    scope: str = Query("self"),
    filter_lsys: Optional[str] = Query(None),
    source: str = Query("all", description="all|trip|duty|reward"),
):
    """
    换休票获取汇总明细：合并「公出节假日换休票」「加班值班换休票」「系统自动派发/手工调整」三种来源。
    source: all=全部, trip=仅公出, duty=仅值班, reward=仅 hxp 手工/系统派发类（非加班换休、非公出节假日换休）
    """
    try:
        # ── 构建人员筛选 ──
        name_clean = (name or "").strip()
        person_cond_he = "1=1"
        person_cond_jb = "1=1"
        person_cond_hxp = "1=1"
        person_params_he: list = []
        person_params_jb: list = []
        person_params_hxp: list = []

        if scope == "self":
            person_cond_he = "h.xm = %s"
            person_params_he = [name_clean]
            person_cond_jb = "j.xm = %s"
            person_params_jb = [name_clean]
            person_cond_hxp = "p.name = %s"
            person_params_hxp = [name_clean]
        elif scope == "all" and filter_lsys:
            person_cond_he = "h.lsys = %s"
            person_params_he = [filter_lsys.strip()]
            person_cond_jb = "y.lsys = %s"
            person_params_jb = [filter_lsys.strip()]
            person_cond_hxp = "yg.lsys = %s"
            person_params_hxp = [filter_lsys.strip()]
        elif scope == "lsys":
            rows = db.execute_query("SELECT lsys FROM yggl WHERE name = %s LIMIT 1", (name_clean,))
            lsys_val = (rows[0].get("lsys") or "").strip() if rows else ""
            if lsys_val:
                person_cond_he = "h.lsys = %s"
                person_params_he = [lsys_val]
                person_cond_jb = "y.lsys = %s"
                person_params_jb = [lsys_val]
                person_cond_hxp = "yg.lsys = %s"
                person_params_hxp = [lsys_val]
            else:
                person_cond_he = "h.xm = %s"
                person_params_he = [name_clean]
                person_cond_jb = "j.xm = %s"
                person_params_jb = [name_clean]
                person_cond_hxp = "p.name = %s"
                person_params_hxp = [name_clean]

        data = []

        # ── 来源1: 公出节假日换休票（holiday_exchange） ──
        if source in ("all", "trip"):
            he_year_cond = "AND YEAR(h.apply_time) = %s" if year else ""
            he_month_cond = "AND MONTH(h.apply_time) = %s" if month else ""
            he_year_params = ([year] if year else []) + ([month] if month else [])
            he_sql = f"""
                SELECT h.id, h.xm, h.bz, h.lsys, h.date_from, h.date_to, h.date_ranges,
                       h.days, h.hxp_count, h.status, h.spr, h.spr2, h.bhyy, h.apply_time,
                       h.material_files
                FROM holiday_exchange h
                WHERE {person_cond_he} AND h.status = 4 {he_year_cond} {he_month_cond}
                ORDER BY h.apply_time DESC
            """
            he_rows = db.execute_query(he_sql, tuple(person_params_he + he_year_params))

            STATUS_TEXT = {0: "待一级审批", 1: "待二级审批", 4: "已通过", 22: "已驳回"}
            for r in (he_rows or []):
                df, dt = r.get("date_from"), r.get("date_to")
                dr_raw = r.get("date_ranges")
                _, smy = holiday_exchange_rest_day_info(df, dt, dr_raw)
                dr_list = None
                if dr_raw:
                    try:
                        dr_list = json.loads(dr_raw) if isinstance(dr_raw, str) else dr_raw
                    except Exception:
                        pass
                mf_raw = r.get("material_files") or ""
                mf_list = []
                if mf_raw:
                    try:
                        mf_list = json.loads(mf_raw) if isinstance(mf_raw, str) else mf_raw
                    except Exception:
                        pass
                data.append({
                    "id": r.get("id"),
                    "source": "公出节假日",
                    "applicant": r.get("xm") or "",
                    "department": r.get("bz") or r.get("lsys") or "",
                    "dateFrom": str(df or ""),
                    "dateTo": str(dt or ""),
                    "dateRanges": dr_list,
                    "days": r.get("days") or 0,
                    "hxpCount": float(r.get("hxp_count") or 0),
                    "restDaySummary": smy,
                    "applyTime": str(r.get("apply_time") or "")[:19],
                    "status": STATUS_TEXT.get(r.get("status"), "未知"),
                    "materialFiles": mf_list if isinstance(mf_list, list) else [],
                })

        # ── 来源2: 加班值班换休票（jiaban 表 hx='是' 且已通过） ──
        if source in ("all", "duty"):
            jb_year_cond = "AND YEAR(j.timedate) = %s" if year else ""
            jb_month_cond = "AND MONTH(j.timedate) = %s" if month else ""
            jb_year_params = ([year] if year else []) + ([month] if month else [])
            jb_sql = f"""
                SELECT j.id, j.xm, j.bz, j.timedate, j.timefrom, j.timeto,
                       j.tian1, j.hxp, j.jiabanfs, j.content,
                       j.spr, j.spr2, j.jiabanzt
                FROM jiaban j
                LEFT JOIN yggl y ON j.xm = y.name AND COALESCE(y.zaizhi, 0) = 0
                WHERE j.jiabanzt = 4 AND TRIM(COALESCE(j.hx, '')) = '是'
                  AND {person_cond_jb} {jb_year_cond} {jb_month_cond}
                ORDER BY j.timedate DESC
            """
            jb_rows = db.execute_query(jb_sql, tuple(person_params_jb + jb_year_params))

            for r in (jb_rows or []):
                td = r.get("timedate")
                date_str = str(td)[:10] if td else ""
                hxp_val = float(r.get("hxp") or 0)
                if hxp_val <= 0:
                    continue
                tf = r.get("timefrom") or ""
                tt = r.get("timeto") or ""
                time_desc = f"{tf}~{tt}" if tf and tt else ""
                fs = (r.get("jiabanfs") or "").strip()
                data.append({
                    "id": r.get("id"),
                    "source": "值班申请",
                    "applicant": r.get("xm") or "",
                    "department": r.get("bz") or "",
                    "dateFrom": date_str,
                    "dateTo": date_str,
                    "dateRanges": None,
                    "days": None,
                    "hxpCount": hxp_val,
                    "restDaySummary": time_desc,
                    "applyTime": date_str,
                    "status": "已通过",
                })

        # ── 来源3: 系统自动派发/手工调整（hxp 表中非"加班换休""公出节假日换休"的正数记录） ──
        if source in ("all", "reward"):
            hxp_year_cond = "AND YEAR(p.sj) = %s" if year else ""
            hxp_month_cond = "AND MONTH(p.sj) = %s" if month else ""
            hxp_year_params = ([year] if year else []) + ([month] if month else [])
            hxp_sql = f"""
                SELECT p.id, p.name, p.sl, p.sj, p.ly
                FROM hxp p
                LEFT JOIN yggl yg ON p.name = yg.name AND COALESCE(yg.zaizhi, 0) = 0
                WHERE {person_cond_hxp} AND p.sl > 0
                  AND TRIM(COALESCE(p.ly, '')) NOT IN ('加班换休', '公出节假日换休', '')
                  {hxp_year_cond} {hxp_month_cond}
                ORDER BY p.sj DESC
            """
            hxp_rows = db.execute_query(hxp_sql, tuple(person_params_hxp + hxp_year_params))

            for r in (hxp_rows or []):
                sj_raw = r.get("sj")
                sj_str = str(sj_raw or "")[:19] if sj_raw else ""
                date_str = sj_str[:10]
                sl = float(r.get("sl") or 0)
                if sl <= 0:
                    continue
                ly_val = (r.get("ly") or "").strip()
                # 历史用词「集体奖励」与空 ly 统一展示为「系统自动派发」
                src_display = ly_val or "系统自动派发"
                summary_display = ly_val or "系统自动派发"
                if src_display == "集体奖励":
                    src_display = summary_display = "系统自动派发"
                data.append({
                    "id": r.get("id"),
                    "source": src_display,
                    "applicant": r.get("name") or "",
                    "department": "",
                    "dateFrom": date_str,
                    "dateTo": date_str,
                    "dateRanges": None,
                    "days": None,
                    "hxpCount": sl,
                    "restDaySummary": summary_display,
                    "applyTime": sj_str,
                    "status": "已入账",
                    "materialFiles": [],
                })

        data.sort(key=lambda x: x.get("applyTime") or "", reverse=True)
        total_hxp = sum(x.get("hxpCount") or 0 for x in data)

        return {"success": True, "data": data, "totalHxp": round(total_hxp, 4)}
    except Exception as e:
        logger.error("换休票汇总查询失败: %s", e)
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
