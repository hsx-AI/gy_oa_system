# -*- coding: utf-8 -*-
"""
公出登记 API - 写入 gcsqb (公出申请表)
字段映射(汉语拼音首字母简拼):
  wpdw=委派单位, gcdw=公出/填报单位, gzh=工作号, gcsj=公出时间(出发时间)
  lxdh=联系电话, wpsj=委派时间, gcryxm=公出人员姓名, xmmc=项目名称
  yjfhsj=预计返回时间, tzdbh=通知单编号, bcgczrs=本次公出总人数
  gcdd=公出地点, qkje=请款金额, gcrw=公出任务, bld=部领导, szr=室主任
  bldzt=部领导状态, szrzt=室主任状态, gcr=公出人(申请人), sqsj=申请时间
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


@router.post("/apply")
async def apply_business_trip(req: BusinessTripApplyRequest):
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


def _trip_status(bldzt, szrzt) -> tuple:
    """根据 bldzt/szrzt 返回 (状态文案, statusClass)。1=待审批 2=通过 22=驳回"""
    bldzt = bldzt if bldzt is not None else 0
    szrzt = szrzt if szrzt is not None else 0
    if bldzt == 22 or szrzt == 22:
        return "已驳回", "status-rejected"
    if bldzt == 2 and szrzt == 2:
        return "已通过", "status-approved"
    return "审批中", "status-processing"


def _row_to_record(row) -> dict:
    """将 gcsqb 一行转为前端所需记录结构"""
    bldzt = 0 if row.get("bldzt") is None else int(row.get("bldzt"))
    szrzt = 0 if row.get("szrzt") is None else int(row.get("szrzt"))
    status, status_class = _trip_status(bldzt, szrzt)
    current_approver = ""
    if status == "审批中":
        if szrzt == 1:
            current_approver = (row.get("szr") or "").strip()
        elif bldzt == 1:
            current_approver = (row.get("bld") or "").strip()
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
        "expectedStartTime": _fmt_dt(row.get("yjcfsj")),
        "expectedReturnTime": _fmt_dt(row.get("yjfhsj")),
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
        meta["canViewLsys"] = (_jb_match(jb, "主任") or _jb_match(jb, "副主任")) and bool(lsys)
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
            "AND RIGHT(TRIM(y.name), 1) <> '1' "
            "AND RIGHT(TRIM(y.lsys), 1) <> '1')"
        )
        return clause, [], meta
    if not meta["canViewLsys"]:
        raise HTTPException(status_code=403, detail="仅主任、副主任可查看本专业全员公出记录")
    lsys_u = (user.get("lsys") or "").strip()
    clause = (
        "g.gcr IN (SELECT y.name FROM yggl AS y WHERE y.lsys = %s AND COALESCE(y.zaizhi,0)=0 "
        "AND y.name IS NOT NULL AND TRIM(y.name) <> '')"
    )
    return clause, [lsys_u], meta


@router.get("/list")
async def get_business_trip_list(
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


@router.get("/all-records")
async def get_business_trip_all_records(
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
async def set_business_trip_return_time(item_id: str, body: ReturnTimeBody):
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
async def extend_business_trip(item_id: str, req: ExtendTripRequest):
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
        "SELECT id, gcr, bldzt, szrzt, fhdj_status, yjfhsj, gcrw FROM gcsqb WHERE id = %s",
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


@router.get("/extendable-list")
async def get_extendable_business_trips(name: str = Query(..., description="当前用户姓名")):
    """获取当前用户科室内可延长的公出记录（已通过且未返回登记）"""
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

    one_year_ago = datetime.now().replace(year=datetime.now().year - 1).strftime("%Y-%m-%d %H:%M:%S")
    base = f"g.bldzt = 2 AND g.szrzt = 2 AND COALESCE(g.fhdj_status, 0) = 0 AND COALESCE(g.yjcfsj, g.yjfhsj) >= %s"

    if is_admin:
        where = base
        params: tuple = (one_year_ago,)
    else:
        where = (
            f"{base} "
            "AND g.gcr IN (SELECT y.name FROM yggl y WHERE y.lsys = %s AND COALESCE(y.zaizhi,0)=0)"
        )
        params = (one_year_ago, viewer_lsys)

    sql = f"""
        SELECT g.id, g.gcr, g.gcdd, g.yjcfsj, g.yjfhsj, g.gclx, g.xmmc, g.gcrw, g.bld
        FROM gcsqb g WHERE {where}
        ORDER BY g.yjcfsj DESC
    """
    rows = db.execute_query(sql, params) or []
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
    return {"success": True, "list": result}


@router.delete("/{item_id}")
async def delete_business_trip_rejected(item_id: str, name: str):
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
