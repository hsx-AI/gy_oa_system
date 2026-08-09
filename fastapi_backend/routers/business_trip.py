# -*- coding: utf-8 -*-
"""
公出登记 API - 写入 gcsqb (公出申请表)
字段映射(汉语拼音首字母简拼):
  wpdw=委派单位, gcdw=公出/填报单位, gzh=工作号, gcsj=公出时间(出发时间)
  lxdh=联系电话, wpsj=委派时间, gcryxm=公出人员姓名, xmmc=项目名称
  yjfhsj=预计返回时间, tzdbh=通知单编号, bcgczrs=本次公出总人数
  gcdd=公出地点, qkje=请款金额, gcrw=公出任务, bld=部领导, szr=室主任
  bldzt=部领导状态, szrzt=室主任状态, gcr=公出人(申请人)
  lsysjm=隶属于室简称
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from database import db
from routers.approvers import _get_user_info, _jb_match, is_zonghe_tech_director
from routers.db_manager import _get_admin1
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/business-trip", tags=["公出管理"])


class BusinessTripApplyRequest(BaseModel):
    """公出登记请求"""
    tripScope: str = "境内公出"  # gclx 公出类型：市内公出/境内公出/境外公出
    targetUnit: str          # wpdw 委派单位
    assignTime: str = ""     # wpsj 委派时间(可选)
    noticeNo: str            # tzdbh 通知单编号
    department: str          # gcdw 填报单位
    name: str                # gcryxm 公出人员姓名
    totalPeople: int = 1     # bcgczrs 本次公出总人数
    workNo: str = ""         # gzh 工作号
    projectName: str = ""    # xmmc 项目名称
    location: str            # gcdd 公出地点
    startTime: str           # yjcfsj 预计出发时间
    endTime: str             # yjfhsj 预计返回时间
    amount: float = 0        # qkje 请款金额
    phone: str               # lxdh 联系电话
    task: str                # gcrw 公出任务
    deptLeader: str          # bld 部领导
    responsiblePerson: str   # szr 室主任


def _to_dt(s: str) -> Optional[str]:
    """datetime-local 转为 MySQL datetime，兼容各种前端格式"""
    if not s:
        return None
    import re
    s = s.replace("T", " ").strip()
    m = re.match(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?", s)
    if m:
        date_part = m.group(1)
        hh, mm = m.group(2), m.group(3)
        ss = m.group(4) or "00"
        return f"{date_part} {hh}:{mm}:{ss}"
    if len(s) == 10 and re.match(r"\d{4}-\d{2}-\d{2}", s):
        return f"{s} 00:00:00"
    return None


def _next_id() -> str:
    """生成全局唯一的记录 id，避免并发或无序导致重复"""
    return uuid.uuid4().hex


def _parse_dt(s):
    """将字符串或 datetime 解析为 datetime 对象"""
    if s is None:
        return None
    if hasattr(s, "strftime"):
        return s
    s = str(s).strip()[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            pass
    return None


def _check_trip_overlap(gcr: str, start_dt, end_dt, exclude_id: str = None) -> list:
    """
    检查公出人 gcr 的新时间段 [start_dt, end_dt] 是否与已有公出记录重叠。
    排除已驳回(bldzt=22 或 szrzt=22)的记录，以及 gcrw 为「打卡管理员代处理」的记录。
    返回重叠记录列表。
    """
    if not gcr or not start_dt or not end_dt:
        return []
    gcr = gcr.strip()
    new_start = _parse_dt(start_dt)
    new_end = _parse_dt(end_dt)
    if not new_start or not new_end:
        return []

    sql = """
        SELECT id, gcdd, gclx,
               COALESCE(gcsj, yjcfsj) AS trip_start,
               COALESCE(sjfhtime, yjfhsj) AS trip_end,
               COALESCE(fhdj_status, 0) AS fhdj_status
        FROM gcsqb
        WHERE TRIM(gcr) = %s
          AND NOT (COALESCE(bldzt,0) = 22 OR COALESCE(szrzt,0) = 22)
          AND TRIM(COALESCE(gcrw, '')) != '打卡管理员代处理'
    """
    params: list = [gcr]
    if exclude_id:
        sql += " AND id != %s"
        params.append(exclude_id)

    rows = db.execute_query(sql, tuple(params))
    if not rows:
        return []

    conflicts = []
    for row in rows:
        t_start = _parse_dt(row.get("trip_start"))
        t_end = _parse_dt(row.get("trip_end"))
        if not t_start or not t_end:
            continue
        if new_start < t_end and new_end > t_start:
            conflicts.append({
                "id": row.get("id"),
                "location": row.get("gcdd") or "",
                "type": row.get("gclx") or "",
                "start": t_start.strftime("%Y-%m-%d %H:%M"),
                "end": t_end.strftime("%Y-%m-%d %H:%M"),
                "returned": int(row.get("fhdj_status") or 0) == 1,
            })
    return conflicts


def _raise_if_overlap(gcr: str, start_dt, end_dt, exclude_id: str = None):
    """若有时间重叠，抛出 409 异常并列出冲突记录"""
    conflicts = _check_trip_overlap(gcr, start_dt, end_dt, exclude_id)
    if conflicts:
        lines = [f"· {c['start']} ~ {c['end']}（{c['type']}，{c['location']}）" for c in conflicts]
        msg = "公出时间段与以下已有记录重叠，请勿重复填报：\n" + "\n".join(lines)
        if all(c.get("returned") for c in conflicts):
            msg += "\n\n重叠的公出均已返回登记，如需修改已有数据请联系黄圣轩7480"
        else:
            msg += "\n\n重叠的公出中存在未返回登记的记录，请先完成返回登记后再提交"
        raise HTTPException(status_code=409, detail=msg)


@router.post("/apply")
def apply_business_trip(req: BusinessTripApplyRequest):
    """公出登记 - 插入 gcsqb 表"""
    try:
        rid = _next_id()

        yjfhsj = _to_dt(req.endTime)
        yjcfsj = _to_dt(req.startTime) if req.startTime else None
        wpsj = _to_dt(req.assignTime) if req.assignTime else None

        qkje = str(req.amount) if req.amount else "无"
        gzh = req.workNo or "无"
        xmmc = req.projectName or "无"

        # gclx 公出类型；gcsj 不在登记时填写，留待返回登记时填入
        gclx = (req.tripScope or "").strip() or "境内公出"
        if gclx not in ("市内公出", "境内公出", "境外公出"):
            gclx = "境内公出"
        if gclx in ("境内公出", "境外公出") and not (req.noticeNo or "").strip():
            raise HTTPException(status_code=400, detail="境内公出、境外公出须填写通知单编号")

        # 部办用户无室主任，szrzt 直接设为 2（已通过），仅需部领导审批
        is_buban = False
        dept_str = (req.department or "").strip()
        if dept_str == "部办":
            is_buban = True
        else:
            try:
                emp = db.execute_query(
                    "SELECT lsys FROM yggl WHERE name = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
                    ((req.name or "").strip(),),
                )
                if emp and (emp[0].get("lsys") or "").strip() == "部办":
                    is_buban = True
            except Exception:
                pass

        szrzt_init = 2 if is_buban else 1

        _raise_if_overlap(req.name, yjcfsj or req.startTime, yjfhsj or req.endTime)

        sql = """
            INSERT INTO gcsqb (id, gclx, wpdw, gcr, gzh, gcdw, lxdh, wpsj, yjfhsj, yjcfsj, xmmc,
                tzdbh, bcgczrs, gcdd, qkje, gcrw, szr, bld, gcsj, sjfhtime, bldzt, szrzt)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, 1, %s)
        """
        params = (
            rid,
            gclx,
            req.targetUnit or "",
            req.name or "",
            gzh,
            req.department or "",
            req.phone or "",
            wpsj,
            yjfhsj,
            yjcfsj,
            xmmc,
            req.noticeNo or "",
            str(req.totalPeople),
            req.location or "",
            qkje,
            req.task or "",
            req.responsiblePerson or "",
            req.deptLeader or "",
            szrzt_init,
        )
        affected = db.execute_update(sql, params)
        if affected <= 0:
            raise HTTPException(status_code=500, detail="插入公出记录失败")

        return {"success": True, "message": "公出登记已提交", "id": rid}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"公出登记失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"登记失败: {str(e)}")


def _fmt_dt(d) -> str:
    if d is None:
        return ""
    if hasattr(d, "strftime"):
        return d.strftime("%Y-%m-%d %H:%M")
    return str(d)[:16]


def _fmt_dt_sec(d) -> str:
    """保留到秒的格式化，用于需要前端精准回填（如返回登记自动填充实际出发/返回时间）的字段。"""
    if d is None:
        return ""
    if hasattr(d, "strftime"):
        return d.strftime("%Y-%m-%d %H:%M:%S")
    s = str(d)
    # 兼容 "YYYY-MM-DD HH:MM:SS" / "YYYY-MM-DDTHH:MM:SS" / 带微秒
    return s[:19]


def _trip_status(bldzt, szrzt) -> tuple:
    """根据 bldzt/szrzt 返回 (状态文案, statusClass)。1=待审批 2=通过 22=驳回"""
    bldzt = bldzt if bldzt is not None else 0
    szrzt = szrzt if szrzt is not None else 0
    if bldzt == 22 or szrzt == 22:
        return "已驳回", "status-rejected"
    if bldzt == 2 and szrzt == 2:
        return "已通过", "status-approved"
    return "审批中", "status-processing"


def _trip_flow_person(bldzt, szrzt, szr, bld, status: str) -> str:
    """审批中返回当前待审批人；已驳回返回执行驳回的审批人。"""
    bldzt = bldzt if bldzt is not None else 0
    szrzt = szrzt if szrzt is not None else 0
    if status == "审批中":
        if szrzt == 1:
            return (szr or "").strip()
        if bldzt == 1:
            return (bld or "").strip()
    elif status == "已驳回":
        if szrzt == 22:
            return (szr or "").strip()
        if bldzt == 22:
            return (bld or "").strip()
    return ""


def _row_to_record(row) -> dict:
    """将 gcsqb 一行转为前端所需记录结构"""
    bldzt = 0 if row.get("bldzt") is None else int(row.get("bldzt"))
    szrzt = 0 if row.get("szrzt") is None else int(row.get("szrzt"))
    status, status_class = _trip_status(bldzt, szrzt)
    current_approver = _trip_flow_person(
        bldzt, szrzt, row.get("szr"), row.get("bld"), status
    )
    # 列表「出发时间」：已做返回登记用 gcsj，否则用登记时的预计出发 yjcfsj
    start_display = _fmt_dt(row.get("gcsj")) or _fmt_dt(row.get("yjcfsj"))
    # 「实际返回」：仅 sjfhtime；未返回登记时前端可用 expectedReturnTime 显示预计
    actual_ret = _fmt_dt(row.get("sjfhtime"))
    rec = {
        "id": row.get("id"),
        "tripScope": row.get("gclx") or "",
        "targetUnit": row.get("wpdw") or "",
        "person": row.get("gcr") or "",
        "assignTime": _fmt_dt(row.get("wpsj")),
        "projectName": row.get("xmmc") or "",
        "location": row.get("gcdd") or "",
        "startTime": start_display,
        "actualReturnTime": actual_ret,
        "expectedStartTime": _fmt_dt_sec(row.get("yjcfsj")),
        "expectedReturnTime": _fmt_dt_sec(row.get("yjfhsj")),
        "fhdjStatus": int(row.get("fhdj_status") or 0),
        "status": status,
        "statusClass": status_class,
        "currentApprover": current_approver,
        "rejectReason": (row.get("bhyy") or "").strip(),
    }
    rec["roomDirectorApproveTime"] = _fmt_dt(row.get("szrpztime")) if row.get("szrpztime") is not None else ""
    rec["deptLeaderApproveTime"] = _fmt_dt(row.get("bldpztime")) if row.get("bldpztime") is not None else ""
    return rec


def _business_trip_list_gcr_clause(
    viewer_name: str,
    scope: str,
    filter_lsys: Optional[str] = None,
):
    """
    公出 /list：scope=self 仅本人；scope=lsys 同属室（主任/副主任）；
    scope=all：部长/副部长/系统管理员为不限制；综合技术室主任/副主任为 yggl 全员子查询（与请假/台账规则一致）。
    scope=all 且 filter_lsys 非空时，仅筛选该 yggl.lsys（须具备 canViewAll）。
    返回 (sql_fragment, params list, meta)。
    """
    scope = (scope or "self").strip().lower()
    if scope not in ("self", "lsys", "all"):
        raise HTTPException(status_code=400, detail="无效的 scope")
    viewer = (viewer_name or "").strip()
    if not viewer:
        raise HTTPException(status_code=400, detail="姓名不能为空")
    meta = {"canViewLsys": False, "canViewAll": False, "lsysLabel": ""}
    user = _get_user_info(viewer)
    admin1 = (_get_admin1() or "").strip()
    is_admin_user = bool(admin1 and viewer == admin1)
    # 打卡管理员 dakaman 与系统管理员同等权限查看全员
    try:
        _dk_rows = db.execute_query("SELECT dakaman FROM webconfig WHERE id = %s LIMIT 1", ("1",))
        _dakaman = (_dk_rows[0].get("dakaman") or "").strip() if _dk_rows else ""
    except Exception:
        _dakaman = ""
    is_dakaman = bool(_dakaman and viewer == _dakaman)
    jb = ""
    if user:
        jb = (user.get("jb") or "").strip()
        lsys = (user.get("lsys") or "").strip()
        meta["lsysLabel"] = lsys
        meta["canViewLsys"] = (_jb_match(jb, "主任") or _jb_match(jb, "副主任") or _jb_match(jb, "组长") or _jb_match(jb, "副组长")) and bool(lsys)
    is_minister = _jb_match(jb, "部长") or _jb_match(jb, "副部长")
    zonghe_dir = bool(user and is_zonghe_tech_director(user))
    meta["canViewAll"] = is_admin_user or is_minister or zonghe_dir or is_dakaman

    fl = (filter_lsys or "").strip()
    if scope == "all" and fl:
        if not meta["canViewAll"]:
            raise HTTPException(status_code=403, detail="无权限按科室筛选公出记录")
        clause = (
            "g.gcr IN (SELECT y.name FROM yggl AS y WHERE y.lsys = %s AND COALESCE(y.zaizhi,0)=0 "
            "AND y.name IS NOT NULL AND TRIM(y.name) <> '')"
        )
        return clause, [fl], meta

    if scope == "self":
        return "g.gcr = %s", [viewer], meta
    if scope == "all":
        if not meta["canViewAll"]:
            raise HTTPException(
                status_code=403,
                detail="仅部长、副部长、综合技术室主任/副主任或系统管理员可查看全员公出记录",
            )
        if is_admin_user or is_minister or is_dakaman:
            return "1=1", [], meta
        clause = (
            "g.gcr IN (SELECT y.name FROM yggl AS y WHERE COALESCE(y.zaizhi,0)=0 "
            "AND y.name IS NOT NULL AND TRIM(y.name) <> '' "
            "AND TRIM(y.lsys) <> '部办' "
            "AND TRIM(y.lsys) NOT IN ('其他部门员工','其他部门成员') "
            "AND RIGHT(TRIM(y.name), 1) <> '1' "
            "AND RIGHT(TRIM(y.lsys), 1) <> '1')"
        )
        return clause, [], meta
    if not meta["canViewLsys"]:
        raise HTTPException(status_code=403, detail="仅主任、副主任、组长可查看本专业全员公出记录")
    lsys_u = (user.get("lsys") or "").strip()
    clause = (
        "g.gcr IN (SELECT y.name FROM yggl AS y WHERE y.lsys = %s AND COALESCE(y.zaizhi,0)=0 "
        "AND y.name IS NOT NULL AND TRIM(y.name) <> '')"
    )
    return clause, [lsys_u], meta


@router.get("/list")
def get_business_trip_list(
    name: str,
    year: Optional[int] = None,
    month: Optional[int] = Query(None, ge=1, le=12, description="与 year 同时使用时按自然月过滤"),
    all_years: Optional[bool] = Query(False, description="为 true 时不过滤年份，返回全部"),
    scope: str = Query(
        "self",
        description="self=仅本人，lsys=同属室全员（主任/副主任），all=全员（部长/副部长/综合技术室主任/副主任/系统管理员）",
    ),
    filter_lsys: Optional[str] = Query(
        None,
        description="scope=all 时可选，按 yggl.lsys 仅看该科室",
    ),
):
    """获取公出记录列表。部长/副部长或综合技术室主任等可选 all，并可 filter_lsys 指定科室。"""
    try:
        if year is None and not all_years:
            year = datetime.now().year

        gcr_where, gcr_params, meta = _business_trip_list_gcr_clause(name, scope, filter_lsys)
        year_expr = "COALESCE(g.wpsj, g.gcsj, g.yjcfsj, g.yjfhsj)"
        order_by = f" ORDER BY {year_expr} DESC"
        if all_years:
            where_sql = f" WHERE ({gcr_where})"
            params: tuple = tuple(gcr_params)
        else:
            if month is not None:
                where_sql = (
                    f" WHERE ({gcr_where}) AND YEAR({year_expr}) = %s AND MONTH({year_expr}) = %s"
                )
                params = tuple(gcr_params) + (year, month)
            else:
                where_sql = (
                    f" WHERE ({gcr_where}) AND ({year_expr} LIKE %s OR YEAR({year_expr}) = %s)"
                )
                params = tuple(gcr_params) + (f"{year}%", year)

        try:
            query = (
                "SELECT g.id, g.gclx, g.wpdw, g.gcr, g.wpsj, g.yjcfsj, g.yjfhsj, g.xmmc, g.gcdd, g.gcsj, g.sjfhtime, g.fhdj_status, "
                "g.bldzt, g.szrzt, g.szrpztime, g.bldpztime, g.bhyy, g.bld, g.szr FROM gcsqb g" + where_sql + order_by
            )
            rows = db.execute_query(query, params)
        except Exception as e:
            msg = str(e).lower()
            if "unknown column" in msg and (
                "gclx" in msg or "szrpztime" in msg or "bldpztime" in msg or "fhdj_status" in msg or "bhyy" in msg or "bld" in msg or "szr" in msg
            ):
                query = (
                    "SELECT g.id, g.wpdw, g.gcr, g.wpsj, g.yjcfsj, g.yjfhsj, g.xmmc, g.gcdd, g.gcsj, g.sjfhtime, "
                    "g.bldzt, g.szrzt FROM gcsqb g" + where_sql + order_by
                )
                rows = db.execute_query(query, params)
            else:
                raise

        records = [_row_to_record(row) for row in rows]
        return {
            "success": True,
            "data": records,
            "total": len(records),
            "scope": (scope or "self").strip().lower(),
            "meta": meta,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询公出记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


def _fmt_detail_val(v):
    """
    详情弹窗面向用户的时间/字段展示：
    - None -> "—"
    - "YYYY-MM-DD 00:00:00" -> "YYYY-MM-DD"（避免出现 00:00:00 这种信息噪音）
    - 其他 datetime -> 截断到分钟 "YYYY-MM-DD HH:mm"
    """
    if v is None:
        return "—"
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d %H:%M")
    s = str(v).strip()
    if not s:
        return "—"
    if len(s) >= 19 and s[10] == " ":
        const_date = s[:10]
        hh = s[11:13]
        mm = s[14:16]
        ss = s[17:19]
        if hh == "00" and mm == "00" and ss == "00":
            return const_date
        return s[:16]
    if len(s) >= 16:
        return s[:16]
    return s


def _approval_status_text(bldzt, szrzt) -> str:
    """
    面向用户的简化审批状态文案：
    - 已驳回
    - 已通过
    - 审批中
    """
    bldzt = bldzt if bldzt is not None else 0
    szrzt = szrzt if szrzt is not None else 0
    if bldzt == 22 or szrzt == 22:
        return "已驳回"
    if bldzt == 2 and szrzt == 2:
        return "已通过"
    return "审批中"


def _row_to_detail_payload(row: dict) -> dict:
    """将 gcsqb 一行展开为前端详情弹窗所需结构"""
    bldzt = row.get("bldzt")
    szrzt = row.get("szrzt")
    is_rejected = (int(bldzt) if bldzt is not None else 0) == 22 or (int(szrzt) if szrzt is not None else 0) == 22
    status_txt = _approval_status_text(
        int(bldzt) if bldzt is not None else 0,
        int(szrzt) if szrzt is not None else 0,
    )
    fhdj = row.get("fhdj_status")
    fhdj_txt = "已返回登记" if fhdj == 1 else ("未登记" if fhdj == 0 or fhdj is None else str(fhdj))

    # 当前审批人 / 驳回人
    current_approver = _trip_flow_person(
        int(bldzt) if bldzt is not None else 0,
        int(szrzt) if szrzt is not None else 0,
        row.get("szr"),
        row.get("bld"),
        status_txt,
    )

    expected_start = row.get("yjcfsj")
    expected_end = row.get("yjfhsj")
    actual_start = row.get("gcsj")
    actual_end = row.get("sjfhtime")

    expected_range = "—"
    if expected_start and expected_end:
        expected_range = f"{_fmt_detail_val(expected_start)} ~ {_fmt_detail_val(expected_end)}"
    elif expected_start:
        expected_range = f"{_fmt_detail_val(expected_start)} ~ —"
    elif expected_end:
        expected_range = f"— ~ {_fmt_detail_val(expected_end)}"

    actual_range = "—"
    if actual_start and actual_end:
        actual_range = f"{_fmt_detail_val(actual_start)} ~ {_fmt_detail_val(actual_end)}"
    elif actual_start:
        actual_range = f"{_fmt_detail_val(actual_start)} ~ —"
    elif actual_end:
        actual_range = f"— ~ {_fmt_detail_val(actual_end)}"

    amount_val = row.get("qkje")
    amount_txt = "—"
    if amount_val not in (None, ""):
        try:
            amount_txt = f"{float(amount_val):.2f}"
        except Exception:
            amount_txt = _fmt_detail_val(amount_val)

    items = [
        ("公出类型", _fmt_detail_val(row.get("gclx"))),
        ("公出人", _fmt_detail_val(row.get("gcr"))),
        ("委派单位", _fmt_detail_val(row.get("wpdw"))),
        ("委派时间", _fmt_detail_val(row.get("wpsj"))),
        ("通知单编号", _fmt_detail_val(row.get("tzdbh"))),
        ("工作号", _fmt_detail_val(row.get("gzh"))),
        ("公出地点", _fmt_detail_val(row.get("gcdd"))),
        ("项目名称", _fmt_detail_val(row.get("xmmc"))),
        ("公出任务", _fmt_detail_val(row.get("gcrw"))),
        ("联系电话", _fmt_detail_val(row.get("lxdh"))),
        ("请款金额", amount_txt),
        ("本次公出总人数", _fmt_detail_val(row.get("bcgczrs"))),
        ("公出时间（预计）", expected_range),
        ("公出时间（实际）", actual_range),
        ("审批状态", status_txt),
        ("返回登记", fhdj_txt),
        ("室主任", _fmt_detail_val(row.get("szr"))),
        ("室主任审批时间", _fmt_detail_val(row.get("szrpztime"))),
        ("部领导", _fmt_detail_val(row.get("bld"))),
        ("部领导审批时间", _fmt_detail_val(row.get("bldpztime"))),
    ]

    if status_txt == "审批中":
        items.append(("当前审批人", _fmt_detail_val(current_approver) if current_approver else "—"))
    elif is_rejected:
        items.append(("驳回人", _fmt_detail_val(current_approver) if current_approver else "—"))
    if is_rejected and row.get("bhyy"):
        items.append(("驳回原因", _fmt_detail_val(row.get("bhyy"))))

    return {"items": [{"label": k, "value": v} for k, v in items]}


def _all_records_visibility_clause(viewer_name: str) -> tuple:
    """
    与 GET /all-records 一致的「谁能看到哪些 gcr」；
    返回 (sql_fragment, params)，用于 AND (fragment)。
    """
    viewer_name = (viewer_name or "").strip()
    user = _get_user_info(viewer_name)
    if not user:
        return "0=1", tuple()
    admin1 = _get_admin1()
    name_stripped = viewer_name
    try:
        _dk_rows = db.execute_query("SELECT dakaman FROM webconfig WHERE id = %s LIMIT 1", ("1",))
        _dakaman = (_dk_rows[0].get("dakaman") or "").strip() if _dk_rows else ""
    except Exception:
        _dakaman = ""
    is_dk = bool(_dakaman and name_stripped == _dakaman)
    if (admin1 and name_stripped == admin1) or is_dk:
        return "1=1", tuple()
    jb = (user.get("jb") or "").strip()
    lsys = (user.get("lsys") or "").strip()
    is_leader = (
        _jb_match(jb, "部长")
        or _jb_match(jb, "副部长")
        or is_zonghe_tech_director(user)
    )
    if is_leader:
        return "1=1", tuple()
    if not lsys:
        return "0=1", tuple()
    clause = (
        "g.gcr IN (SELECT y.name FROM yggl y WHERE y.lsys = %s AND COALESCE(y.zaizhi,0)=0 "
        "AND y.name IS NOT NULL AND TRIM(y.name) <> '')"
    )
    return clause, (lsys,)


@router.get("/{item_id}/detail")
def get_business_trip_detail(
    item_id: str,
    name: str = Query(..., description="当前用户姓名"),
    scope: str = Query(
        "self",
        description="与 /list 一致：self|lsys|all",
    ),
    filter_lsys: Optional[str] = Query(None),
    list_source: str = Query(
        "list",
        description="list=按列表规则；all_records=与 /all-records 本科室视图一致",
    ),
):
    """单条公出数据库详情（仅当前用户对记录可见时）。"""
    try:
        if list_source.strip().lower() == "all_records":
            vis_sql, vis_params = _all_records_visibility_clause(name)
        else:
            vis_sql, vis_params, _meta = _business_trip_list_gcr_clause(name, scope, filter_lsys)

        detail_select = (
            "SELECT g.id, g.gclx, g.wpdw, g.gcr, g.gzh, g.gcdw, g.lxdh, g.wpsj, g.yjcfsj, g.yjfhsj, g.xmmc, "
            "g.tzdbh, g.bcgczrs, g.gcdd, g.qkje, g.gcrw, g.szr, g.bld, g.gcsj, g.sjfhtime, "
            "g.bldzt, g.szrzt, g.fhdj_status, g.bhyy, g.szrpztime, g.bldpztime FROM gcsqb g "
            f"WHERE g.id = %s AND ({vis_sql})"
        )
        params = (item_id,) + tuple(vis_params)
        try:
            rows = db.execute_query(detail_select, params)
        except Exception as e:
            msg = str(e).lower()
            if "unknown column" in msg:
                detail_select = (
                    "SELECT g.id, g.gclx, g.wpdw, g.gcr, g.gzh, g.gcdw, g.lxdh, g.wpsj, g.yjcfsj, g.yjfhsj, g.xmmc, "
                    "g.gcdd, g.qkje, g.gcrw, g.szr, g.bld, g.gcsj, g.sjfhtime, g.bldzt, g.szrzt FROM gcsqb g "
                    f"WHERE g.id = %s AND ({vis_sql})"
                )
                rows = db.execute_query(detail_select, params)
            else:
                raise

        if not rows:
            raise HTTPException(status_code=404, detail="记录不存在或无权查看")

        payload = _row_to_detail_payload(rows[0])
        return {"success": True, "detail": payload}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询公出详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/all-records")
def get_business_trip_all_records(
    name: str = Query(..., description="当前用户姓名"),
    year: Optional[int] = Query(None, description="按年份筛选，不传则全部"),
    month: Optional[int] = Query(None, ge=1, le=12, description="按月份筛选，须与 year 同时传入"),
):
    """
    全部公出记录（按权限）：
    部长/副部长、综合技术室主任/副主任：按时间顺序查看全员公出记录；
    其余人：仅查看本科室全员公出记录。
    按委派时间/公出时间倒序。
    """
    try:
        user = _get_user_info(name)
        if not user:
            return {"success": True, "data": [], "total": 0, "scope": "none"}
        name_stripped = (name or "").strip()
        admin1 = _get_admin1()
        try:
            _dk_rows = db.execute_query("SELECT dakaman FROM webconfig WHERE id = %s LIMIT 1", ("1",))
            _dakaman = (_dk_rows[0].get("dakaman") or "").strip() if _dk_rows else ""
        except Exception:
            _dakaman = ""
        is_dk = bool(_dakaman and name_stripped == _dakaman)
        if (admin1 and name_stripped == admin1) or is_dk:
            is_leader = True
            lsys = ""
        else:
            jb = (user.get("jb") or "").strip()
            lsys = (user.get("lsys") or "").strip()
            is_leader = (
                _jb_match(jb, "部长")
                or _jb_match(jb, "副部长")
                or is_zonghe_tech_director(user)
            )

        order = "ORDER BY COALESCE(g.wpsj, g.gcsj) DESC, g.wpsj DESC"
        date_where = ""
        date_params: tuple = ()
        if year is not None:
            if month is not None:
                date_where = " AND YEAR(COALESCE(g.wpsj, g.gcsj)) = %s AND MONTH(COALESCE(g.wpsj, g.gcsj)) = %s"
                date_params = (year, month)
            else:
                date_where = " AND YEAR(COALESCE(g.wpsj, g.gcsj)) = %s"
                date_params = (year,)

        if is_leader:
            sql = f"""
                SELECT g.id, g.gclx, g.wpdw, g.gcr, g.wpsj, g.yjcfsj, g.yjfhsj, g.xmmc, g.gcdd, g.gcsj, g.sjfhtime, g.bldzt, g.szrzt,
                    g.szr, g.bld, g.bhyy, g.szrpztime, g.bldpztime, COALESCE(g.fhdj_status, 0) AS fhdj_status
                FROM gcsqb g
                WHERE 1=1{date_where}
                {order}
            """
            params = date_params
        else:
            if not lsys:
                return {"success": True, "data": [], "total": 0, "scope": "dept"}
            sql = f"""
                SELECT g.id, g.gclx, g.wpdw, g.gcr, g.wpsj, g.yjcfsj, g.yjfhsj, g.xmmc, g.gcdd, g.gcsj, g.sjfhtime, g.bldzt, g.szrzt,
                    g.szr, g.bld, g.bhyy, g.szrpztime, g.bldpztime, COALESCE(g.fhdj_status, 0) AS fhdj_status
                FROM gcsqb g
                INNER JOIN yggl y ON g.gcr = y.name AND y.lsys = %s
                WHERE 1=1{date_where}
                {order}
            """
            params = (lsys,) + date_params

        rows = db.execute_query(sql, params)
        records = [_row_to_record(row) for row in rows]
        scope = "all" if is_leader else "dept"
        return {"success": True, "data": records, "total": len(records), "scope": scope}
    except Exception as e:
        logger.error(f"查询全部公出记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


class ReturnTimeBody(BaseModel):
    """公出返回登记请求体：填写实际出发时间和实际返回时间"""
    actualStartTime: str
    actualReturnTime: str


@router.post("/{item_id}/return-time")
def set_business_trip_return_time(item_id: str, body: ReturnTimeBody):
    """公出返回登记：更新 gcsj(实际公出时间)、sjfhtime(实际返回时间) 及 fhdj_status=1"""
    try:
        start_raw = (body.actualStartTime or "").replace("T", " ").strip()[:19]
        end_raw = (body.actualReturnTime or "").replace("T", " ").strip()[:19]
        gcsj = _to_dt(start_raw)
        sjfhtime = _to_dt(end_raw)
        if not gcsj:
            raise HTTPException(status_code=400, detail="实际出发时间不能为空")
        if not sjfhtime:
            raise HTTPException(status_code=400, detail="实际返回时间不能为空")

        rec = db.execute_query("SELECT gcr FROM gcsqb WHERE id = %s", (item_id,))
        if not rec:
            raise HTTPException(status_code=404, detail="记录不存在")
        _raise_if_overlap((rec[0].get("gcr") or ""), gcsj, sjfhtime, exclude_id=item_id)

        sql = "UPDATE gcsqb SET gcsj = %s, sjfhtime = %s, yjcfsj = %s, yjfhsj = %s, fhdj_status = 1 WHERE id = %s"
        n = db.execute_update(sql, (gcsj, sjfhtime, gcsj, sjfhtime, item_id))
        if n <= 0:
            raise HTTPException(status_code=404, detail="记录不存在")
        return {"success": True, "message": "公出返回登记已完成"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新返回时间失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class ExtendTripRequest(BaseModel):
    """公出延长请求"""
    current_user: str
    new_return_time: str
    dept_leader: str
    remark: str = ""


@router.post("/{item_id}/extend")
def extend_business_trip(item_id: str, req: ExtendTripRequest):
    """
    公出延长：班组长/主任/副主任可为本科室已通过且未返回登记的公出修改预计返回时间，
    同时重置审批状态为二级审批（仅需部领导审批），附带备注。
    """
    viewer = (req.current_user or "").strip()
    if not viewer:
        raise HTTPException(status_code=400, detail="当前用户不能为空")
    user = _get_user_info(viewer)
    if not user:
        raise HTTPException(status_code=403, detail="用户信息不存在")
    jb = (user.get("jb") or "").strip()
    viewer_lsys = (user.get("lsys") or "").strip()
    admin1 = (_get_admin1() or "").strip()
    is_admin = bool(admin1 and viewer == admin1)
    can_extend = (
        _jb_match(jb, "组长") or _jb_match(jb, "主任") or _jb_match(jb, "副主任") or is_admin
    )
    if not can_extend:
        raise HTTPException(status_code=403, detail="仅班组长、主任、副主任或系统管理员可操作公出延长")

    rows = db.execute_query(
        "SELECT id, gcr, bldzt, szrzt, fhdj_status, yjfhsj, yjcfsj, gcsj, gcrw FROM gcsqb WHERE id = %s",
        (item_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="公出记录不存在")
    r = rows[0]
    bldzt = int(r.get("bldzt") or 0)
    szrzt = int(r.get("szrzt") or 0)
    fhdj = int(r.get("fhdj_status") or 0)
    if not (bldzt == 2 and szrzt == 2):
        raise HTTPException(status_code=400, detail="仅可延长已通过审批的公出记录")
    if fhdj == 1:
        raise HTTPException(status_code=400, detail="已完成返回登记的公出无法延长，请重新登记")

    gcr = (r.get("gcr") or "").strip()
    if not is_admin:
        emp = _get_user_info(gcr)
        emp_lsys = (emp.get("lsys") or "").strip() if emp else ""
        if emp_lsys != viewer_lsys:
            raise HTTPException(status_code=403, detail="只能延长本科室人员的公出记录")

    new_dt = _to_dt(req.new_return_time)
    if not new_dt:
        raise HTTPException(status_code=400, detail="新的预计返回时间格式不正确")

    existing_start = r.get("gcsj") or r.get("yjcfsj")
    if existing_start:
        _raise_if_overlap(gcr, existing_start, new_dt, exclude_id=item_id)

    dept_leader = (req.dept_leader or "").strip()
    if not dept_leader:
        raise HTTPException(status_code=400, detail="请选择部领导")

    remark = (req.remark or "").strip()
    old_task = (r.get("gcrw") or "").strip()
    extend_note = f"[公出延长 {datetime.now().strftime('%Y-%m-%d %H:%M')} by {viewer}] 原预计返回: {_fmt_dt(r.get('yjfhsj'))}，延长至: {new_dt}"
    if remark:
        extend_note += f"，备注: {remark}"
    new_task = f"{old_task}\n{extend_note}" if old_task else extend_note

    sql = """
        UPDATE gcsqb
        SET yjfhsj = %s, bld = %s, bldzt = 1, szrzt = 2,
            bldpztime = NULL, bhyy = NULL, gcrw = %s
        WHERE id = %s
    """
    n = db.execute_update(sql, (new_dt, dept_leader, new_task, item_id))
    if n <= 0:
        raise HTTPException(status_code=500, detail="更新失败")

    return {"success": True, "message": f"已延长公出并提交部领导({dept_leader})审批"}


def _extendable_scope_where(is_admin: bool, viewer_lsys: str, year: Optional[int]) -> tuple:
    """
    可延长公出：时间/年度条件 + 本科室范围（非管理员）。
    与某公历年度有交集：预计出发～预计返回（缺省字段用 COALESCE 补齐，支持跨年长公出）。
    未指定 year 时：列出近 15 年内有预计时间的记录（替代原先「仅约一年」限制）。
    """
    trip_start = "COALESCE(g.yjcfsj, g.wpsj, g.gcsj, g.yjfhsj)"
    trip_end = "COALESCE(g.yjfhsj, g.yjcfsj, g.wpsj, g.gcsj)"
    parts = [
        "g.bldzt = 2",
        "g.szrzt = 2",
        "COALESCE(g.fhdj_status, 0) = 0",
    ]
    params: list = []
    if year is not None:
        ys = f"{int(year)}-01-01 00:00:00"
        ye = f"{int(year)}-12-31 23:59:59"
        parts.append(f"({trip_start}) <= %s")
        parts.append(f"({trip_end}) >= %s")
        params.extend([ye, ys])
    else:
        min_d = datetime(datetime.now().year - 15, 1, 1).strftime("%Y-%m-%d %H:%M:%S")
        parts.append(f"({trip_start}) >= %s")
        params.append(min_d)

    inner = " AND ".join(parts)
    if is_admin:
        return inner, tuple(params)
    return (
        inner
        + " AND g.gcr IN (SELECT y.name FROM yggl y WHERE y.lsys = %s AND COALESCE(y.zaizhi,0)=0)",
        tuple(params + [viewer_lsys]),
    )


@router.get("/extendable-list")
def get_extendable_business_trips(
    name: str = Query(..., description="当前用户姓名"),
    year: Optional[int] = Query(None, description="公历年度：列出与该年有交集的公出；不传则近15年"),
    person: Optional[str] = Query(None, description="公出人姓名（精确匹配，可选）"),
):
    """获取当前用户科室内可延长的公出记录（已通过且未返回登记）；支持按年度、公出人筛选（含跨年长公出）"""
    viewer = (name or "").strip()
    if not viewer:
        raise HTTPException(status_code=400, detail="姓名不能为空")
    user = _get_user_info(viewer)
    if not user:
        raise HTTPException(status_code=403, detail="用户信息不存在")
    jb = (user.get("jb") or "").strip()
    viewer_lsys = (user.get("lsys") or "").strip()
    admin1 = (_get_admin1() or "").strip()
    is_admin = bool(admin1 and viewer == admin1)
    can_extend = (
        _jb_match(jb, "组长") or _jb_match(jb, "主任") or _jb_match(jb, "副主任") or is_admin
    )
    if not can_extend:
        raise HTTPException(status_code=403, detail="仅班组长、主任、副主任或系统管理员可查看")

    y = int(year) if year is not None else None
    if y is not None and (y < 1990 or y > 2100):
        raise HTTPException(status_code=400, detail="年度参数不合法")

    scope_where, scope_params = _extendable_scope_where(is_admin, viewer_lsys, y)
    person_clean = (person or "").strip()

    # 公出人下拉：与列表相同时间/科室条件，不按 person 再缩窄
    sql_people = f"""
        SELECT DISTINCT TRIM(g.gcr) AS nm FROM gcsqb g
        WHERE {scope_where} AND TRIM(g.gcr) <> ''
        ORDER BY nm
    """
    people_rows = db.execute_query(sql_people, scope_params) or []
    people_list = [(r.get("nm") or "").strip() for r in people_rows if (r.get("nm") or "").strip()]

    list_where = scope_where
    list_params = list(scope_params)
    if person_clean:
        list_where = scope_where + " AND TRIM(g.gcr) = %s"
        list_params.append(person_clean)

    sql = f"""
        SELECT g.id, g.gcr, g.gcdd, g.yjcfsj, g.yjfhsj, g.gclx, g.xmmc, g.gcrw, g.bld
        FROM gcsqb g WHERE {list_where}
        ORDER BY COALESCE(g.yjcfsj, g.wpsj, g.yjfhsj) DESC
    """
    rows = db.execute_query(sql, tuple(list_params)) or []
    result = []
    for row in rows:
        result.append({
            "id": row.get("id"),
            "person": (row.get("gcr") or "").strip(),
            "location": (row.get("gcdd") or "").strip(),
            "tripScope": (row.get("gclx") or "").strip(),
            "projectName": (row.get("xmmc") or "").strip(),
            "expectedStartTime": _fmt_dt(row.get("yjcfsj")),
            "expectedReturnTime": _fmt_dt(row.get("yjfhsj")),
            "deptLeader": (row.get("bld") or "").strip(),
        })
    return {"success": True, "list": result, "people": people_list}


@router.post("/{item_id}/resubmit")
def resubmit_business_trip(item_id: str, req: BusinessTripApplyRequest):
    """修改并重新提交已驳回的公出记录（szrzt/bldzt重置，更新字段）"""
    try:
        rows = db.execute_query("SELECT id, bldzt, szrzt, gcr FROM gcsqb WHERE id = %s", (item_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="记录不存在")
        r = rows[0]
        bldzt = int(r.get("bldzt") or 0)
        szrzt = int(r.get("szrzt") or 0)
        if bldzt != 22 and szrzt != 22:
            raise HTTPException(status_code=400, detail="仅可重新提交已驳回的公出记录")
        if (r.get("gcr") or "").strip() != (req.name or "").strip():
            raise HTTPException(status_code=403, detail="只能重新提交本人的记录")

        yjfhsj = _to_dt(req.endTime)
        yjcfsj = _to_dt(req.startTime) if req.startTime else None
        wpsj = _to_dt(req.assignTime) if req.assignTime else None
        qkje = str(req.amount) if req.amount else "无"
        gclx = (req.tripScope or "").strip() or "境内公出"
        if gclx not in ("市内公出", "境内公出", "境外公出"):
            gclx = "境内公出"
        if gclx in ("境内公出", "境外公出") and not (req.noticeNo or "").strip():
            raise HTTPException(status_code=400, detail="境内公出、境外公出须填写通知单编号")

        is_buban = False
        dept_str = (req.department or "").strip()
        if dept_str == "部办":
            is_buban = True
        else:
            try:
                emp = db.execute_query(
                    "SELECT lsys FROM yggl WHERE name = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
                    ((req.name or "").strip(),),
                )
                if emp and (emp[0].get("lsys") or "").strip() == "部办":
                    is_buban = True
            except Exception:
                pass
        szrzt_init = 2 if is_buban else 1

        _raise_if_overlap(req.name, yjcfsj or req.startTime, yjfhsj or req.endTime, exclude_id=item_id)

        affected = db.execute_update(
            """UPDATE gcsqb SET gclx=%s, wpdw=%s, gzh=%s, gcdw=%s, lxdh=%s, wpsj=%s,
               yjfhsj=%s, yjcfsj=%s, xmmc=%s, tzdbh=%s, bcgczrs=%s, gcdd=%s, qkje=%s,
               gcrw=%s, szr=%s, bld=%s, szrzt=%s, bldzt=1,
               bhyy=NULL, szrpztime=NULL, bldpztime=NULL
               WHERE id=%s AND gcr=%s AND (bldzt=22 OR szrzt=22)""",
            (gclx, req.targetUnit or "", req.workNo or "无", req.department or "",
             req.phone or "", wpsj, yjfhsj, yjcfsj, req.projectName or "无",
             req.noticeNo or "", str(req.totalPeople), req.location or "",
             qkje, req.task or "", req.responsiblePerson or "", req.deptLeader or "",
             szrzt_init,
             item_id, req.name.strip())
        )
        if affected <= 0:
            raise HTTPException(status_code=500, detail="重新提交未生效，请刷新后重试")
        return {"success": True, "message": "已重新提交"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新提交公出失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重新提交失败: {str(e)}")


@router.delete("/{item_id}")
def delete_business_trip_rejected(item_id: str, name: str):
    """删除本人已驳回的公出记录（仅 bldzt=22 或 szrzt=22 可删），数据库物理删除"""
    try:
        rows = db.execute_query("SELECT id, bldzt, szrzt, gcr FROM gcsqb WHERE id = %s", (item_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="记录不存在")
        r = rows[0]
        bldzt = int(r.get("bldzt") or 0)
        szrzt = int(r.get("szrzt") or 0)
        if bldzt != 22 and szrzt != 22:
            raise HTTPException(status_code=400, detail="仅可删除已驳回的公出记录")
        if (r.get("gcr") or "").strip() != (name or "").strip():
            raise HTTPException(status_code=403, detail="只能删除本人的记录")
        n = db.execute_update(
            "DELETE FROM gcsqb WHERE id = %s AND gcr = %s AND (bldzt = 22 OR szrzt = 22)",
            (item_id, name.strip()),
        )
        if n <= 0:
            raise HTTPException(status_code=500, detail="删除未生效")
        return {"success": True, "message": "已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除公出记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除失败")
