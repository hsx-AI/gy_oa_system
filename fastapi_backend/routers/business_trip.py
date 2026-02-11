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
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/business-trip", tags=["公出管理"])


class BusinessTripApplyRequest(BaseModel):
    """公出登记请求"""
    targetUnit: str          # wpdw 委派单位
    assignTime: str = ""     # wpsj 委派时间(可选)
    noticeNo: str            # tzdbh 通知单编号
    department: str          # gcdw 填报单位
    name: str                # gcryxm 公出人员姓名
    totalPeople: int = 1     # bcgczrs 本次公出总人数
    workNo: str = ""         # gzh 工作号
    projectName: str = ""    # xmmc 项目名称
    location: str            # gcdd 公出地点
    startTime: str           # gcsj 出发/公出时间
    endTime: str             # yjfhsj 预计返回时间
    amount: float = 0        # qkje 请款金额
    phone: str               # lxdh 联系电话
    task: str                # gcrw 公出任务
    deptLeader: str          # bld 部领导
    responsiblePerson: str   # szr 室主任


def _to_dt(s: str) -> Optional[str]:
    """datetime-local 转为 MySQL datetime"""
    if not s:
        return None
    s = s.replace("T", " ").strip()
    if len(s) <= 16:
        s = s + ":00"
    return s[:19]


def _next_id() -> str:
    """生成全局唯一的记录 id，避免并发或无序导致重复"""
    return uuid.uuid4().hex


@router.post("/apply")
async def apply_business_trip(req: BusinessTripApplyRequest):
    """公出登记 - 插入 gcsqb 表"""
    try:
        rid = _next_id()

        yjfhsj = _to_dt(req.endTime)
        wpsj = _to_dt(req.assignTime) if req.assignTime else None

        qkje = str(req.amount) if req.amount else "无"
        gzh = req.workNo or "无"
        xmmc = req.projectName or "无"

        # gcsj 不在登记时填写，留待公出返回登记时填入实际公出时间
        # 审批状态：bldzt/szrzt 登记时写入 1,1
        sql = """
            INSERT INTO gcsqb (id, wpdw, gcr, gzh, gcdw, lxdh, wpsj, yjfhsj, xmmc,
                tzdbh, bcgczrs, gcdd, qkje, gcrw, szr, bld, gcsj, sjfhtime, bldzt, szrzt)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, 1, 1)
        """
        params = (
            rid,
            req.targetUnit or "",
            req.name or "",
            gzh,
            req.department or "",
            req.phone or "",
            wpsj,
            yjfhsj,
            xmmc,
            req.noticeNo or "",
            str(req.totalPeople),
            req.location or "",
            qkje,
            req.task or "",
            req.responsiblePerson or "",
            req.deptLeader or "",
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


@router.get("/list")
async def get_business_trip_list(
    name: str,
    year: Optional[int] = None,
    all_years: Optional[bool] = Query(False, description="为 true 时不过滤年份，返回全部"),
):
    """获取本人公出记录列表（按公出人 gcr）。含审批状态 bldzt/szrzt 及批示时间。all_years=true 时返回全部年份。"""
    try:
        if year is None and not all_years:
            year = datetime.now().year

        if all_years:
            base_where = " WHERE gcr = %s ORDER BY wpsj DESC"
            params = (name,)
        else:
            base_where = " WHERE gcr = %s AND (wpsj LIKE %s OR YEAR(wpsj) = %s) ORDER BY wpsj DESC"
            params = (name, f"{year}%", year)
        try:
            # bld=部领导, szr=室主任；审批中时展示当前审批人
            query = (
                "SELECT id, wpdw, gcr, wpsj, xmmc, gcdd, gcsj, sjfhtime, fhdj_status, "
                "bldzt, szrzt, szrpztime, bldpztime, bhyy, bld, szr FROM gcsqb" + base_where
            )
            rows = db.execute_query(query, params)
        except Exception as e:
            msg = str(e).lower()
            if "unknown column" in msg and (
                "szrpztime" in msg or "bldpztime" in msg or "fhdj_status" in msg or "bhyy" in msg or "bld" in msg or "szr" in msg
            ):
                # 兼容老表结构：无 fhdj_status / szrpztime / bldpztime / bhyy / bld / szr 列
                query = (
                    "SELECT id, wpdw, gcr, wpsj, xmmc, gcdd, gcsj, sjfhtime, "
                    "bldzt, szrzt FROM gcsqb" + base_where
                )
                rows = db.execute_query(query, params)
            else:
                raise

        records = []
        for row in rows:
            bldzt = 0 if row.get("bldzt") is None else int(row.get("bldzt"))
            szrzt = 0 if row.get("szrzt") is None else int(row.get("szrzt"))
            status, status_class = _trip_status(bldzt, szrzt)
            # 审批中时：室主任待审批(szrzt==1) 显示室主任，部领导待审批(bldzt==1) 显示部领导
            current_approver = ""
            if status == "审批中":
                if szrzt == 1:
                    current_approver = (row.get("szr") or "").strip()  # 室主任
                elif bldzt == 1:
                    current_approver = (row.get("bld") or "").strip()  # 部领导
            rec = {
                "id": row.get("id"),
                "targetUnit": row.get("wpdw") or "",
                "person": row.get("gcr") or "",
                "assignTime": _fmt_dt(row.get("wpsj")),
                "projectName": row.get("xmmc") or "",
                "location": row.get("gcdd") or "",
                "startTime": _fmt_dt(row.get("gcsj")),
                "actualReturnTime": _fmt_dt(row.get("sjfhtime")),
                "fhdjStatus": int(row.get("fhdj_status") or 0),
                "status": status,
                "statusClass": status_class,
                "currentApprover": current_approver,
                "rejectReason": (row.get("bhyy") or "").strip(),
            }
            rec["roomDirectorApproveTime"] = _fmt_dt(row.get("szrpztime")) if row.get("szrpztime") is not None else ""
            rec["deptLeaderApproveTime"] = _fmt_dt(row.get("bldpztime")) if row.get("bldpztime") is not None else ""
            records.append(rec)

        return {"success": True, "data": records, "total": len(records)}
    except Exception as e:
        logger.error(f"查询公出记录失败: {str(e)}")
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

        sql = "UPDATE gcsqb SET gcsj = %s, sjfhtime = %s, fhdj_status = 1 WHERE id = %s"
        n = db.execute_update(sql, (gcsj, sjfhtime, item_id))
        if n <= 0:
            raise HTTPException(status_code=404, detail="记录不存在")
        return {"success": True, "message": "公出返回登记已完成"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新返回时间失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
