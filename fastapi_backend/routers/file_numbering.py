# -*- coding: utf-8 -*-
"""
文件编号 API - 技术文件、技术管理、管理文件
"""
import os
from fastapi import APIRouter, HTTPException, Query, File, UploadFile
from fastapi.responses import FileResponse, Response
from typing import Optional, List, Tuple
from urllib.parse import quote
from pydantic import BaseModel
from datetime import datetime
from database import db
import logging
import uuid
from io import BytesIO

from routers.department_policy import _can_upload_policy

logger = logging.getLogger(__name__)


def _keyword_sql_clause(keyword: Optional[str], like_lhs_exprs: List[str]) -> Tuple[Optional[str], tuple]:
    """多列 OR LIKE；like_lhs_exprs 为 LIKE 左侧 SQL 表达式（列名或 CAST(...)）。"""
    kw = (keyword or "").strip()
    if not kw:
        return None, ()
    kwp = f"%{kw}%"
    clause = "(" + " OR ".join(f"{e} LIKE %s" for e in like_lhs_exprs) + ")"
    return clause, tuple([kwp] * len(like_lhs_exprs))


_TECH_KW_LHS = ["bz", "xm", "gzh", "cpname", "fenlei", "neirong", "bianhao1", "bianhao3", "CAST(bhyear AS CHAR)"]
_JSGL_KW_LHS = ["bz", "xm", "gzh", "cpname", "neirong", "fenlei", "fenleihao", "bianhao1", "bianhao3", "CAST(bhyear AS CHAR)"]
_GL_KW_LHS = ["bz", "xm", "fenlei", "neirong", "content", "bianhao1", "bianhao3", "CAST(bhyear AS CHAR)"]
_GYGCH_KW_LHS = ["bz", "xm", "neirong", "room_code", "bianhao_code", "CAST(bhyear AS CHAR)"]
_SCSZH_KW_LHS = ["bz", "xm", "fenlei", "neirong", "content", "bianhao1", "CAST(bhyear AS CHAR)"]

router = APIRouter(prefix="/file-numbering", tags=["文件编号"])

# data 下子文件夹存放上传的 PDF：技术文件、技术管理、管理文件、工艺过程策划表
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
FILE_DIRS = {
    "tech": os.path.join(_DATA_DIR, "tech_files"),
    "jsgl": os.path.join(_DATA_DIR, "jsgl_files"),
    "manage": os.path.join(_DATA_DIR, "manage_files"),
    "gygch": os.path.join(_DATA_DIR, "gygch_files"),
    "scszh": os.path.join(_DATA_DIR, "scszh_files"),
}


def _ensure_file_dirs():
    for d in FILE_DIRS.values():
        os.makedirs(d, exist_ok=True)


def _format_bhtime(dt: Optional[datetime] = None) -> str:
    """编号时间存库格式，与历史迁移数据一致：YYYY/M/D（如 2026/3/16），便于与旧数据混排、前端排序解析。"""
    d = dt or datetime.now()
    return f"{d.year}/{d.month}/{d.day}"


def _sql_order_bhtime_desc_id_desc() -> str:
    """
    按编号时间真实日期倒序。bhtime 可能是 VARCHAR / DATE / DATETIME。
    先 CAST 为 CHAR，取日期段，将 - . 统一为 /，再依次尝试两种格式。
    注意：pymysql 用 %s 做参数替换，MySQL 的 %Y 等需要转义为 %%Y。
    """
    bh = "SUBSTRING_INDEX(TRIM(CAST(bhtime AS CHAR(128))), ' ', 1)"
    norm = f"REPLACE(REPLACE({bh}, '-', '/'), '.', '/')"
    parsed = (
        f"COALESCE(STR_TO_DATE({norm}, '%%Y/%%c/%%e'), STR_TO_DATE({norm}, '%%Y/%%m/%%d'))"
    )
    return f"ORDER BY ({parsed} IS NULL) ASC, {parsed} DESC, id DESC"


def _row_id(r) -> Optional[str]:
    """从数据库行取 id，兼容 id / ID 两种列名"""
    if not r:
        return None
    raw = r.get("id") if r.get("id") is not None else r.get("ID")
    if raw is None:
        return None
    return str(raw).strip() or None


def _file_path(ftype: str, row_id: str) -> str:
    if ftype not in FILE_DIRS:
        raise HTTPException(status_code=400, detail="无效类型")
    if not row_id:
        raise HTTPException(status_code=400, detail="无效id")
    safe_id = "".join(c for c in str(row_id) if c.isalnum() or c in "-_")
    if not safe_id:
        raise HTTPException(status_code=400, detail="无效id")
    return os.path.join(FILE_DIRS[ftype], f"{safe_id}.pdf")


def _file_path_by_code(ftype: str, code: str) -> str:
    """用编号代码作为文件名（唯一），如 2617-0768[2025].pdf、艺纪字2025147.pdf"""
    if ftype not in FILE_DIRS:
        raise HTTPException(status_code=400, detail="无效类型")
    if not code or not str(code).strip():
        raise HTTPException(status_code=400, detail="无效编号代码")
    safe = "".join(c for c in str(code).strip() if c.isalnum() or c in "-_[]﹝﹞（）【】")
    if not safe:
        raise HTTPException(status_code=400, detail="无效编号代码")
    return os.path.join(FILE_DIRS[ftype], f"{safe}.pdf")


# ==================== 工作号 gzh ====================

@router.get("/gzh/list")
async def get_gzh_list(ssks: str = Query(..., description="所属科室"), year: Optional[int] = Query(None, description="筛选基准年，不传则当年；返回 year0>=该年 及 NULL")):
    """工作号列表，按科室过滤；筛选今年及之后的工作号（year0 >= 当前年 或 year0 IS NULL）"""
    try:
        y = year or datetime.now().year
        rows = db.execute_query(
            "SELECT id, gzh, gzhname, year0, ssks, tjr FROM gzh WHERE ssks=%s AND (year0 >= %s OR year0 IS NULL) ORDER BY year0 DESC, id DESC",
            (ssks, y)
        )
        return {"success": True, "list": [dict(r) for r in (rows or [])]}
    except Exception as e:
        logger.error(f"获取工作号列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class GzhAddRequest(BaseModel):
    tjr: str
    gzh: str
    xmm: str  # 项目名称 -> gzhname
    jznf: Optional[int] = None  # 基准年份 -> year0
    ssks: str


@router.post("/gzh/add")
async def add_gzh(req: GzhAddRequest):
    """添加工作号"""
    try:
        year0 = req.jznf or datetime.now().year
        year1 = str(datetime.now().year)
        rid = uuid.uuid4().hex
        sql = "INSERT INTO gzh (id, tjr, gzh, gzhname, year1, year0, ssks) VALUES (%s,%s,%s,%s,%s,%s,%s)"
        db.execute_update(sql, (rid, req.tjr, req.gzh, req.xmm, year1, year0, req.ssks))
        return {"success": True, "message": "工作号录入成功"}
    except Exception as e:
        logger.error(f"添加工作号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 技术文件分类 bianhao_fl ====================

@router.get("/bianhao-fl/list")
async def get_bianhao_fl_list(ssks: str = Query(..., description="所属科室")):
    """技术文件分类列表"""
    try:
        rows = db.execute_query(
            "SELECT id, flbianma, flname, ssks, year0 FROM bianhao_fl WHERE ssks=%s ORDER BY id",
            (ssks,)
        )
        return {"success": True, "list": [dict(r) for r in (rows or [])]}
    except Exception as e:
        logger.error(f"获取分类列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BianhaoFlAddRequest(BaseModel):
    tjr: str
    flbianma: str  # 分类编码 如 2217-
    flname: str    # 分类名称 如 工艺卡片
    year0: Optional[int] = None
    ssks: str


@router.post("/bianhao-fl/add")
async def add_bianhao_fl(req: BianhaoFlAddRequest):
    """添加技术文件分类"""
    try:
        year0 = req.year0 or datetime.now().year
        sql = "INSERT INTO bianhao_fl (tjr, flbianma, flname, year0, ssks) VALUES (%s,%s,%s,%s,%s)"
        db.execute_update(sql, (req.tjr, req.flbianma, req.flname, year0, req.ssks))
        return {"success": True, "message": "分类录入成功"}
    except Exception as e:
        logger.error(f"添加分类失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 技术文件编号 bianhao ====================

class BianhaoTechRequest(BaseModel):
    xm: str
    bz: str
    xmname: str   # 项目名称 -> cpname, 用于查 gzh
    fenlei: str   # 分类显示名
    flbianma: str  # 分类编码如 2217-，用于bianhao1
    neirong: str
    content: str = ""


@router.post("/bianhao/tech/add")
async def add_bianhao_tech(req: BianhaoTechRequest):
    """
    技术文件编号 - 写入 bianhao 表
    编号规则: bianhao1=flbianma取5位, bianhao2=同(bianhao1,bz)顺序号, bianhao3=4位
    """
    try:
        if not req.neirong.strip():
            raise HTTPException(status_code=400, detail="编号内容不能为空")
        # 取 gzh
        gzh_rows = db.execute_query("SELECT gzh FROM gzh WHERE gzhname=%s AND ssks=%s LIMIT 1", (req.xmname, req.bz))
        gzh_val = (gzh_rows[0]["gzh"] or "").strip() if gzh_rows else ""
        if not gzh_val:
            raise HTTPException(status_code=400, detail="未找到对应工作号，请先在工作号维护中录入")
        # bianhao1: 分类编码取右5位
        flbianma_s = (req.flbianma or req.fenlei or "").strip()
        bianhao1 = (flbianma_s[-5:] if len(flbianma_s) >= 5 else flbianma_s.zfill(5)) or "00000"
        # 取最大 bianhao2
        max_rows = db.execute_query(
            "SELECT bianhao2 FROM bianhao WHERE bianhao1=%s AND bz=%s ORDER BY bianhao2 DESC LIMIT 1",
            (bianhao1, req.bz)
        )
        next_num = 1 if not max_rows else (max_rows[0].get("bianhao2") or 0) + 1
        bianhao3 = str(next_num).zfill(4)
        bhyear = str(datetime.now().year)
        bhtime = _format_bhtime()
        sql = """INSERT INTO bianhao (bz,xm,fenlei,gzh,cpname,neirong,bhtime,yj,bhyear,bianhao1,bianhao2,bianhao3)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,'0',%s,%s,%s,%s)"""
        db.execute_update(sql, (req.bz, req.xm, req.fenlei, gzh_val, req.xmname, req.neirong, bhtime, bhyear, bianhao1, next_num, bianhao3))
        # 规范化展示格式：XXXX-XXXX[YYYY]，如 2617-0780[2026]
        prefix = (bianhao1[:4] if len(bianhao1) >= 4 else bianhao1.zfill(4))
        code = f"{prefix}-{bianhao3}[{bhyear}]"
        return {"success": True, "message": "编号成功", "bianhao": code}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"技术文件编号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bianhao/tech/list")
async def get_bianhao_tech_list(
    bz: Optional[str] = Query(None),
    px: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None, description="编号/内容/项目等关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100)
):
    """技术文件编号列表，按编制时间倒序，每页30条"""
    try:
        where, params = [], ()
        if bz:
            where.append("bz=%s")
            params = (bz,)
            if px:
                where.append("fenlei=%s")
                params = (bz, px)
        kc, kp = _keyword_sql_clause(keyword, _TECH_KW_COLS)
        if kc:
            where.append(kc)
            params = params + kp
        where_sql = (" AND ".join(where)) if where else "1=1"
        cnt = db.execute_query(f"SELECT COUNT(*) as n FROM bianhao WHERE {where_sql}", params)
        total = (cnt[0]["n"] or 0) if cnt else 0
        offset = (page - 1) * page_size
        order = f"{_sql_order_bhtime_desc_id_desc()} LIMIT %s OFFSET %s"
        rows = db.execute_query(f"SELECT * FROM bianhao WHERE {where_sql} {order}", (*params, page_size, offset))
        def _with_has_pdf(r, ftype):
            d = dict(_fmt_bianhao(r))
            d["id"] = _row_id(r)
            code = d.get("bianhao_code") or ""
            d["has_pdf"] = bool(code) and os.path.isfile(_file_path_by_code(ftype, code))
            return d
        return {"success": True, "list": [_with_has_pdf(r, "tech") for r in (rows or [])], "total": total, "page": page, "pageSize": page_size}
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _fmt_bianhao(r):
    """编号展示格式：XXXX-XXXX[YYYY]，如 2617-0780[2026]"""
    b1, yr, b3 = _str(r.get("bianhao1")), _str(r.get("bhyear")), _str(r.get("bianhao3"))
    prefix = (b1[:4] if len(b1) >= 4 else b1.zfill(4)) if b1 else "0000"
    code = f"{prefix}-{b3}[{yr}]" if (prefix and b3 and yr) else f"{b1}{yr}{b3}"
    return {
        "id": _row_id(r),
        "bz": r.get("bz"),
        "xm": r.get("xm"),
        "fenlei": r.get("fenlei"),
        "gzh": r.get("gzh"),
        "cpname": r.get("cpname"),
        "neirong": r.get("neirong"),
        "bhtime": _str(r.get("bhtime")),
        "bhyear": yr,
        "bianhao1": r.get("bianhao1"),
        "bianhao2": r.get("bianhao2"),
        "bianhao3": r.get("bianhao3"),
        "bianhao_code": code
    }


def _str(v):
    if v is None:
        return ""
    return str(v).strip()


# ==================== 技术管理编号 bianhaogljs ====================
# 固定分类（仅此三种）: 车间技术交底、工艺技术评审、工艺设计问题反馈单

FENLEI_JSGL = [
    {"value": "艺水-JJ-", "label": "车间技术交底"},
    {"value": "艺水-PS-", "label": "工艺技术评审"},
    {"value": "FKD-艺水-", "label": "工艺设计问题反馈单"},
]


class BianhaoJsglRequest(BaseModel):
    xm: str
    bz: str
    xmname: str
    fenlei: str  # 艺水-JJ- / 艺水-PS- / FKD-艺水-
    neirong: str
    content: str = ""


@router.get("/bianhao-jsgl/fenlei")
async def get_jsgl_fenlei():
    """技术管理固定分类选项"""
    return {"success": True, "list": FENLEI_JSGL}


@router.post("/bianhaogljs/add")
async def add_bianhaogljs(req: BianhaoJsglRequest):
    """技术管理编号 - 写入 bianhaogljs"""
    try:
        if not req.neirong.strip():
            raise HTTPException(status_code=400, detail="编号内容不能为空")
        if req.fenlei not in [f["value"] for f in FENLEI_JSGL]:
            raise HTTPException(status_code=400, detail="无效分类")
        gzh_rows = db.execute_query("SELECT gzh FROM gzh WHERE gzhname=%s AND ssks=%s LIMIT 1", (req.xmname, req.bz))
        gzh_val = (gzh_rows[0]["gzh"] or "").strip() if gzh_rows else ""
        bhyear = datetime.now().year
        max_rows = db.execute_query(
            "SELECT bianhao2 FROM bianhaogljs WHERE bianhao1=%s AND bhyear=%s ORDER BY bianhao2 DESC LIMIT 1",
            (req.fenlei, bhyear)
        )
        next_num = 1 if not max_rows else (max_rows[0].get("bianhao2") or 0) + 1
        bianhao3 = str(next_num).zfill(3)
        fenleihao = next((f["label"] for f in FENLEI_JSGL if f["value"] == req.fenlei), "")
        sql = """INSERT INTO bianhaogljs (xm,bz,fenlei,gzh,cpname,neirong,bhtime,bhyear,bianhao1,bianhao2,bianhao3,fenleihao,yj)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'0')"""
        bhtime = _format_bhtime()
        db.execute_update(sql, (req.xm, req.bz, req.fenlei, gzh_val, req.xmname, req.neirong, bhtime, bhyear, req.fenlei, next_num, bianhao3, fenleihao))
        code = f"{req.fenlei}{bhyear}{bianhao3}"
        return {"success": True, "message": "编号成功", "bianhao": code}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"技术管理编号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bianhaogljs/list")
async def get_bianhaogljs_list(
    bz: Optional[str] = Query(None, description="所属科室，不传则不过滤"),
    px: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None, description="关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100)
):
    """技术管理编号列表，按编制时间倒序；可按 bz 筛选所在科室"""
    try:
        fenlei_map = {"1": "FKD-艺水-", "2": "艺水-JJ-", "3": "艺水-PS-"}
        where, params = [], ()
        if (bz or "").strip():
            where.append("bz=%s")
            params = (bz.strip(),)
        if px and px in fenlei_map:
            where.append("fenlei=%s")
            params = params + (fenlei_map[px],) if isinstance(params, tuple) else (fenlei_map[px],)
        kc, kp = _keyword_sql_clause(keyword, _JSGL_KW_LHS)
        if kc:
            where.append(kc)
            params = params + kp
        where_sql = " AND ".join(where) if where else "1=1"
        cnt = db.execute_query(f"SELECT COUNT(*) as n FROM bianhaogljs WHERE {where_sql}", params)
        total = (cnt[0]["n"] or 0) if cnt else 0
        offset = (page - 1) * page_size
        rows = db.execute_query(
            f"SELECT * FROM bianhaogljs WHERE {where_sql} {_sql_order_bhtime_desc_id_desc()} LIMIT %s OFFSET %s",
            (*params, page_size, offset),
        )
        def _with_has_pdf(r, ftype):
            d = dict(_fmt_gl(r))
            d["id"] = _row_id(r)
            code = d.get("bianhao_code") or ""
            d["has_pdf"] = bool(code) and os.path.isfile(_file_path_by_code(ftype, code))
            return d
        return {"success": True, "list": [_with_has_pdf(r, "jsgl") for r in (rows or [])], "total": total, "page": page, "pageSize": page_size}
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _fmt_gl(r):
    b1, by, b3 = r.get("bianhao1"), _str(r.get("bhyear")), r.get("bianhao3")
    return {
        "id": _row_id(r), "xm": r.get("xm"), "bz": r.get("bz"), "fenlei": r.get("fenlei"),
        "fenleihao": _str(r.get("fenleihao")),
        "gzh": r.get("gzh") or "", "cpname": r.get("cpname") or "", "neirong": r.get("neirong"),
        "bhtime": _str(r.get("bhtime")), "bhyear": by, "bianhao1": b1, "bianhao2": r.get("bianhao2"), "bianhao3": b3,
        "bianhao_code": f"{b1}{by}{b3}" if (b1 and b3) else "-"
    }


# ==================== 管理文件编号 bianhaogl ====================
# 固定分类：艺纪字-工艺会议纪要，艺通字-工艺通知文件，艺报字-工艺报告文件

FENLEI_GL = [
    {"value": "艺纪字", "label": "艺纪字-工艺会议纪要"},
    {"value": "艺通字", "label": "艺通字-工艺通知文件"},
    {"value": "艺报字", "label": "艺报字-工艺报告文件"},
]


class BianhaoglRequest(BaseModel):
    xm: str
    bz: str
    xmname: str = ""
    fenlei: str
    neirong: str
    content: str = ""


@router.get("/bianhaogl/fenlei")
async def get_gl_fenlei():
    return {"success": True, "list": FENLEI_GL}


@router.post("/bianhaogl/add")
async def add_bianhaogl(req: BianhaoglRequest):
    """管理文件编号 - 写入 bianhaogl"""
    try:
        if not req.neirong.strip():
            raise HTTPException(status_code=400, detail="编号内容不能为空")
        if req.fenlei not in [f["value"] for f in FENLEI_GL]:
            raise HTTPException(status_code=400, detail="无效分类")
        bhyear = datetime.now().year
        max_rows = db.execute_query(
            "SELECT bianhao2 FROM bianhaogl WHERE bianhao1=%s AND bhyear=%s ORDER BY bianhao2 DESC LIMIT 1",
            (req.fenlei, bhyear)
        )
        next_num = 1 if not max_rows else (max_rows[0].get("bianhao2") or 0) + 1
        bianhao3 = str(next_num).zfill(3)
        bhtime = _format_bhtime()
        sql = """INSERT INTO bianhaogl (xm,bz,fenlei,cpname,neirong,bhtime,bhyear,bianhao1,bianhao2,bianhao3,yj,content)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'0',%s)"""
        db.execute_update(sql, (req.xm, req.bz, req.fenlei, req.xmname or "", req.neirong, bhtime, bhyear, req.fenlei, next_num, bianhao3, (req.content or "").strip()))
        code = f"{req.fenlei}﹝{bhyear}﹞{bianhao3}"
        return {"success": True, "message": "编号成功", "bianhao": code}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"管理文件编号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _fmt_gl_gl(r):
    """管理文件编号列表格式化（无 gzh，cpname 可选）"""
    b1, by, b3 = r.get("bianhao1"), _str(r.get("bhyear")), r.get("bianhao3")
    return {
        "id": _row_id(r), "xm": r.get("xm"), "bz": r.get("bz"), "fenlei": r.get("fenlei"),
        "gzh": r.get("gzh") or "", "cpname": r.get("cpname") or "", "neirong": r.get("neirong"),
        "content": _str(r.get("content")),
        "bhtime": _str(r.get("bhtime")), "bhyear": by, "bianhao1": b1, "bianhao2": r.get("bianhao2"), "bianhao3": b3,
        "bianhao_code": f"{b1}﹝{by}﹞{b3}" if (b1 and b3) else "-"
    }


@router.get("/bianhaogl/list")
async def get_bianhaogl_list(
    bz: Optional[str] = Query(None, description="所属科室"),
    px: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None, description="关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100)
):
    """管理文件编号列表，按编制时间倒序；可按 bz 筛选所在科室"""
    try:
        fenlei_map = {"1": "艺纪字", "2": "艺通字", "3": "艺报字"}
        where, params = [], ()
        if (bz or "").strip():
            where.append("bz=%s")
            params = (bz.strip(),)
        if px and px in fenlei_map:
            where.append("fenlei=%s")
            params = params + (fenlei_map[px],) if isinstance(params, tuple) else (fenlei_map[px],)
        kc, kp = _keyword_sql_clause(keyword, _GL_KW_LHS)
        if kc:
            where.append(kc)
            params = params + kp
        where_sql = " AND ".join(where) if where else "1=1"
        cnt = db.execute_query(f"SELECT COUNT(*) as n FROM bianhaogl WHERE {where_sql}", params)
        total = (cnt[0]["n"] or 0) if cnt else 0
        offset = (page - 1) * page_size
        rows = db.execute_query(
            f"SELECT * FROM bianhaogl WHERE {where_sql} {_sql_order_bhtime_desc_id_desc()} LIMIT %s OFFSET %s",
            (*params, page_size, offset),
        )
        def _with_has_pdf(r, ftype):
            d = dict(_fmt_gl_gl(r))
            d["id"] = _row_id(r)
            code = d.get("bianhao_code") or ""
            d["has_pdf"] = bool(code) and os.path.isfile(_file_path_by_code(ftype, code))
            return d
        return {"success": True, "list": [_with_has_pdf(r, "manage") for r in (rows or [])], "total": total, "page": page, "pageSize": page_size}
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 工艺过程策划表编号 bianhao_gygch ====================
# 编号规则：年代(4位) + 科室代码(前两字拼音首字母+CH) + 顺序号(3位)
# 如 2015SFCH001（水发室2015年第一份）、2026ZHCH002（综合技术室2026年第二份）
# room_code 由用户所在科室(yggl.lsys)自动推导，无需手动选择


def _lsys_to_room_code(lsys: str) -> str:
    """将科室名称转为编号代码：取前两个汉字的拼音首字母大写 + CH。
    如 水发室 -> SFCH, 综合技术室 -> ZHCH"""
    lsys = (lsys or "").strip()
    if not lsys:
        raise HTTPException(status_code=400, detail="科室名称为空，无法生成编号代码")
    try:
        from pypinyin import pinyin, Style
        chars = [c for c in lsys if '\u4e00' <= c <= '\u9fff'][:2]
        if len(chars) < 2:
            raise HTTPException(status_code=400, detail=f"科室「{lsys}」名称过短，需至少两个汉字")
        initials = pinyin(chars, style=Style.FIRST_LETTER)
        code = "".join(i[0].upper() for i in initials) + "CH"
        return code
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"科室名称转编号代码失败: {e}")
        raise HTTPException(status_code=400, detail=f"科室「{lsys}」拼音转换失败: {e}")


class BianhaoGygchRequest(BaseModel):
    xm: str
    bz: str
    bhyear: Optional[int] = None
    neirong: str = ""


@router.post("/gygch/add")
async def add_bianhao_gygch(req: BianhaoGygchRequest):
    """工艺过程策划表编号 - room_code 由 bz(科室) 自动推导"""
    try:
        bz = (req.bz or "").strip()
        if not bz:
            raise HTTPException(status_code=400, detail="科室不能为空")
        room_code = _lsys_to_room_code(bz)
        bhyear = req.bhyear or datetime.now().year
        max_rows = db.execute_query(
            "SELECT seq FROM bianhao_gygch WHERE bhyear=%s AND room_code=%s ORDER BY seq DESC LIMIT 1",
            (bhyear, room_code)
        )
        next_seq = 1 if not max_rows else (max_rows[0].get("seq") or 0) + 1
        bianhao_code = f"{bhyear}{room_code}{str(next_seq).zfill(3)}"
        bhtime = _format_bhtime()
        rid = uuid.uuid4().hex
        sql = """INSERT INTO bianhao_gygch (id, bz, xm, bhyear, room_code, seq, bianhao_code, neirong, bhtime)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        db.execute_update(sql, (rid, bz, req.xm, bhyear, room_code, next_seq, bianhao_code, (req.neirong or "").strip(), bhtime))
        return {"success": True, "message": "编号成功", "bianhao": bianhao_code, "room_code": room_code}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"工艺过程策划表编号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _fmt_gygch(r):
    return {
        "id": _row_id(r),
        "bz": r.get("bz"),
        "xm": r.get("xm"),
        "bhyear": r.get("bhyear"),
        "room_code": r.get("room_code"),
        "seq": r.get("seq"),
        "neirong": _str(r.get("neirong")),
        "bhtime": _str(r.get("bhtime")),
        "bianhao_code": _str(r.get("bianhao_code")) or "-",
    }


@router.get("/gygch/list")
async def get_bianhao_gygch_list(
    bz: Optional[str] = Query(None, description="所属科室"),
    keyword: Optional[str] = Query(None, description="关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100)
):
    """工艺过程策划表编号列表，按编号时间倒序"""
    try:
        where, params = [], ()
        if (bz or "").strip():
            where.append("bz=%s")
            params = (bz.strip(),)
        kc, kp = _keyword_sql_clause(keyword, _GYGCH_KW_LHS)
        if kc:
            where.append(kc)
            params = params + kp
        where_sql = " AND ".join(where) if where else "1=1"
        cnt = db.execute_query(f"SELECT COUNT(*) as n FROM bianhao_gygch WHERE {where_sql}", params)
        total = (cnt[0]["n"] or 0) if cnt else 0
        offset = (page - 1) * page_size
        rows = db.execute_query(
            f"SELECT * FROM bianhao_gygch WHERE {where_sql} {_sql_order_bhtime_desc_id_desc()} LIMIT %s OFFSET %s",
            (*params, page_size, offset)
        )
        def _with_has_pdf(r):
            d = dict(_fmt_gygch(r))
            d["id"] = _row_id(r)
            code = d.get("bianhao_code") or ""
            d["has_pdf"] = bool(code) and os.path.isfile(_file_path_by_code("gygch", code))
            return d
        return {"success": True, "list": [_with_has_pdf(r) for r in (rows or [])], "total": total, "page": page, "pageSize": page_size}
    except Exception as e:
        logger.error(f"查询工艺过程策划表列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PDF 上传与预览/下载 ====================

_ensure_file_dirs()


@router.post("/file/upload")
async def upload_numbering_pdf(
    type: str = Query(..., description="tech|jsgl|manage"),
    code: str = Query(..., description="编号代码，用作文件名，如 2617-0768[2025]、艺纪字2025147"),
    file: UploadFile = File(...),
):
    """上传终版 PDF，仅支持 PDF。文件按编号代码命名（唯一）."""
    if type not in FILE_DIRS:
        raise HTTPException(status_code=400, detail="无效类型")
    fn = (file.filename or "").strip().lower()
    if not fn.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件，请上传终版 PDF")
    ct = (file.content_type or "").lower()
    if "pdf" not in ct and ct:
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")
    try:
        path = _file_path_by_code(type, code)
        _ensure_file_dirs()
        content = await file.read()
        with open(path, "wb") as f:
            f.write(content)
        return {"success": True, "message": "上传成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF 上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 生产数字化编号 bianhao_scszh ====================
# 编号规则：生产数字化（项目缩写）纪字【年份】xx号
# 如 生产数字化（线）纪字【2026】1号
# 项目缩写固定：线(线圈数字化车间)、冲(冲剪数字化车间)、金(金工数字化车间)、焊(焊接数字化车间)

FENLEI_SCSZH = [
    {"value": "线", "label": "线 - 线圈数字化车间"},
    {"value": "冲", "label": "冲 - 冲剪数字化车间"},
    {"value": "金", "label": "金 - 金工数字化车间"},
    {"value": "焊", "label": "焊 - 焊接数字化车间"},
]


def _ensure_scszh_table():
    """确保 bianhao_scszh 表存在"""
    try:
        db.execute_update("""
            CREATE TABLE IF NOT EXISTS bianhao_scszh (
                id INT AUTO_INCREMENT PRIMARY KEY,
                xm VARCHAR(100) DEFAULT NULL,
                bz VARCHAR(200) DEFAULT NULL,
                fenlei VARCHAR(50) NOT NULL COMMENT '项目缩写：线/冲/金/焊',
                neirong TEXT DEFAULT NULL COMMENT '编号内容',
                content VARCHAR(500) DEFAULT NULL COMMENT '备注',
                bhtime VARCHAR(50) DEFAULT NULL,
                bhyear INT DEFAULT NULL,
                bianhao1 VARCHAR(50) DEFAULT NULL COMMENT '项目缩写',
                bianhao2 INT DEFAULT NULL COMMENT '顺序号',
                bianhao3 VARCHAR(10) DEFAULT NULL COMMENT '顺序号字符串',
                yj VARCHAR(10) DEFAULT '0',
                INDEX idx_fenlei_year (bianhao1, bhyear)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """, ())
    except Exception as e:
        logger.warning(f"创建 bianhao_scszh 表: {e}")


_ensure_scszh_table()


@router.get("/scszh/fenlei")
async def get_scszh_fenlei():
    return {"success": True, "list": FENLEI_SCSZH}


class BianhaoScszhRequest(BaseModel):
    xm: str
    bz: str
    fenlei: str
    neirong: str
    content: str = ""


@router.post("/scszh/add")
async def add_bianhao_scszh(req: BianhaoScszhRequest):
    """生产数字化编号 - 写入 bianhao_scszh"""
    try:
        if not req.neirong.strip():
            raise HTTPException(status_code=400, detail="编号内容不能为空")
        valid_values = [f["value"] for f in FENLEI_SCSZH]
        if req.fenlei not in valid_values:
            raise HTTPException(status_code=400, detail=f"无效项目缩写，可选：{valid_values}")
        bhyear = datetime.now().year
        max_rows = db.execute_query(
            "SELECT bianhao2 FROM bianhao_scszh WHERE bianhao1=%s AND bhyear=%s ORDER BY bianhao2 DESC LIMIT 1",
            (req.fenlei, bhyear)
        )
        next_num = 1 if not max_rows else (max_rows[0].get("bianhao2") or 0) + 1
        bhtime = _format_bhtime()
        sql = """INSERT INTO bianhao_scszh (xm,bz,fenlei,neirong,bhtime,bhyear,bianhao1,bianhao2,bianhao3,yj,content)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'0',%s)"""
        db.execute_update(sql, (req.xm, req.bz, req.fenlei, req.neirong.strip(), bhtime, bhyear,
                                req.fenlei, next_num, str(next_num), (req.content or "").strip()))
        code = f"生产数字化（{req.fenlei}）纪字【{bhyear}】{next_num}号"
        return {"success": True, "message": "编号成功", "bianhao": code}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生产数字化编号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _fmt_scszh(r):
    """生产数字化编号列表格式化"""
    fl = r.get("fenlei") or r.get("bianhao1") or ""
    by = _str(r.get("bhyear"))
    seq = r.get("bianhao2") or 0
    return {
        "id": _row_id(r), "xm": r.get("xm"), "bz": r.get("bz"), "fenlei": fl,
        "neirong": r.get("neirong"), "content": _str(r.get("content")),
        "bhtime": _str(r.get("bhtime")), "bhyear": by,
        "bianhao1": fl, "bianhao2": seq, "bianhao3": r.get("bianhao3"),
        "bianhao_code": f"生产数字化（{fl}）纪字【{by}】{seq}号" if (fl and by) else "-"
    }


@router.get("/scszh/list")
async def get_bianhao_scszh_list(
    bz: Optional[str] = Query(None, description="所属科室"),
    px: Optional[str] = Query(None, description="按项目缩写筛选"),
    keyword: Optional[str] = Query(None, description="关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100)
):
    """生产数字化编号列表"""
    try:
        where, params = [], ()
        if (bz or "").strip():
            where.append("bz=%s")
            params = (bz.strip(),)
        if (px or "").strip():
            where.append("fenlei=%s")
            params = params + (px.strip(),)
        kc, kp = _keyword_sql_clause(keyword, _SCSZH_KW_LHS)
        if kc:
            where.append(kc)
            params = params + kp
        where_sql = " AND ".join(where) if where else "1=1"
        cnt = db.execute_query(f"SELECT COUNT(*) as n FROM bianhao_scszh WHERE {where_sql}", params)
        total = (cnt[0]["n"] or 0) if cnt else 0
        offset = (page - 1) * page_size
        rows = db.execute_query(
            f"SELECT * FROM bianhao_scszh WHERE {where_sql} {_sql_order_bhtime_desc_id_desc()} LIMIT %s OFFSET %s",
            (*params, page_size, offset)
        )

        def _with_has_pdf(r):
            d = dict(_fmt_scszh(r))
            code = d.get("bianhao_code") or ""
            d["has_pdf"] = bool(code and code != "-") and os.path.isfile(_file_path_by_code("scszh", code))
            return d

        return {"success": True, "list": [_with_has_pdf(r) for r in (rows or [])], "total": total, "page": page, "pageSize": page_size}
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


_EXPORT_TABLE_LABELS = {
    "tech": "技术文件编号",
    "jsgl": "技术管理文件编号",
    "manage": "管理文件编号",
    "gygch": "工艺过程策划表",
    "scszh": "生产数字化编号",
}


@router.get("/export/excel")
async def export_bianhao_excel(
    table: str = Query(..., description="tech|jsgl|manage|gygch|scszh"),
    name: str = Query(..., description="当前用户姓名"),
):
    """导出各类型编号台账（全量）。仅 yggl 综合技术室且主任/副主任可用，与制度上传权限一致。"""
    if table not in _EXPORT_TABLE_LABELS:
        raise HTTPException(status_code=400, detail="无效表格类型")
    if not _can_upload_policy((name or "").strip()):
        raise HTTPException(status_code=403, detail="仅综合技术室主任/副主任可导出")
    try:
        from openpyxl import Workbook
    except ImportError:
        raise HTTPException(status_code=500, detail="服务端未安装 openpyxl，无法导出")

    order_sql = _sql_order_bhtime_desc_id_desc()
    wb = Workbook()
    ws = wb.active
    label = _EXPORT_TABLE_LABELS[table]
    ws.title = label[:31]

    try:
        if table == "tech":
            rows = db.execute_query(f"SELECT * FROM bianhao WHERE 1=1 {order_sql}", ())
            ws.append(["编号单位", "编制人", "工作号", "项目名称", "编号类别", "编号内容", "编号时间", "编号代码", "已上传PDF"])
            for r in rows or []:
                d = _fmt_bianhao(r)
                code = d.get("bianhao_code") or ""
                hasp = "是" if (code and os.path.isfile(_file_path_by_code("tech", code))) else "否"
                ws.append(
                    [d.get("bz"), d.get("xm"), d.get("gzh"), d.get("cpname"), d.get("fenlei"), d.get("neirong"), d.get("bhtime"), code, hasp]
                )
        elif table == "jsgl":
            rows = db.execute_query(f"SELECT * FROM bianhaogljs WHERE 1=1 {order_sql}", ())
            ws.append(["编号单位", "编制人", "工作号", "项目名称", "编号类别", "编号内容", "编号时间", "编号代码", "已上传PDF"])
            for r in rows or []:
                d = _fmt_gl(r)
                code = d.get("bianhao_code") or ""
                hasp = "是" if (code and os.path.isfile(_file_path_by_code("jsgl", code))) else "否"
                flh = d.get("fenleihao") or d.get("fenlei")
                ws.append([d.get("bz"), d.get("xm"), d.get("gzh"), d.get("cpname"), flh, d.get("neirong"), d.get("bhtime"), code, hasp])
        elif table == "manage":
            rows = db.execute_query(f"SELECT * FROM bianhaogl WHERE 1=1 {order_sql}", ())
            ws.append(["编号单位", "编制人", "编号类别", "编号内容", "编号时间", "编号代码", "备注", "已上传PDF"])
            for r in rows or []:
                d = _fmt_gl_gl(r)
                code = d.get("bianhao_code") or ""
                hasp = "是" if (code and os.path.isfile(_file_path_by_code("manage", code))) else "否"
                ws.append([d.get("bz"), d.get("xm"), d.get("fenlei"), d.get("neirong"), d.get("bhtime"), code, d.get("content"), hasp])
        elif table == "gygch":
            rows = db.execute_query(f"SELECT * FROM bianhao_gygch WHERE 1=1 {order_sql}", ())
            ws.append(["编号单位", "编制人", "年代", "工艺部室", "编号内容", "编号时间", "编号代码", "已上传PDF"])
            for r in rows or []:
                d = _fmt_gygch(r)
                code = d.get("bianhao_code") or ""
                hasp = "是" if (code and os.path.isfile(_file_path_by_code("gygch", code))) else "否"
                ws.append([d.get("bz"), d.get("xm"), d.get("bhyear"), d.get("room_code"), d.get("neirong"), d.get("bhtime"), code, hasp])
        else:  # scszh
            rows = db.execute_query(f"SELECT * FROM bianhao_scszh WHERE 1=1 {order_sql}", ())
            ws.append(["编号单位", "编制人", "项目", "编号内容", "备注", "编号时间", "编号代码", "已上传PDF"])
            for r in rows or []:
                d = _fmt_scszh(r)
                code = d.get("bianhao_code") or ""
                hasp = "是" if (code and code != "-" and os.path.isfile(_file_path_by_code("scszh", code))) else "否"
                ws.append([d.get("bz"), d.get("xm"), d.get("fenlei"), d.get("neirong"), d.get("content"), d.get("bhtime"), code, hasp])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出文件编号 Excel 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    bio = BytesIO()
    wb.save(bio)
    data = bio.getvalue()
    fname = f"文件编号_{label}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fname)}"},
    )


@router.delete("/file")
async def delete_numbering_pdf(
    type: str = Query(..., description="tech|jsgl|manage"),
    code: str = Query(..., description="编号代码"),
):
    """删除已上传的 PDF，删除后可重新上传."""
    path = _file_path_by_code(type, code)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except Exception as e:
            logger.error(f"删除 PDF 失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, "message": "已删除"}


@router.get("/file")
async def get_numbering_pdf(
    type: str = Query(..., description="tech|jsgl|manage"),
    code: str = Query(..., description="编号代码"),
    download: Optional[int] = Query(0, description="1=下载，0=预览"),
):
    """预览或下载已上传的 PDF（按编号代码定位文件）."""
    path = _file_path_by_code(type, code)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="暂无文件")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{code}.pdf",
        content_disposition_type="attachment" if download else "inline",
    )
