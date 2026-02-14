# -*- coding: utf-8 -*-
"""
文件编号 API - 技术文件、技术管理、管理文件
"""
import os
from fastapi import APIRouter, HTTPException, Query, File, UploadFile
from fastapi.responses import FileResponse
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from database import db
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/file-numbering", tags=["文件编号"])

# data 下子文件夹存放上传的 PDF：技术文件、技术管理、管理文件、工艺过程策划表
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
FILE_DIRS = {
    "tech": os.path.join(_DATA_DIR, "tech_files"),
    "jsgl": os.path.join(_DATA_DIR, "jsgl_files"),
    "manage": os.path.join(_DATA_DIR, "manage_files"),
    "gygch": os.path.join(_DATA_DIR, "gygch_files"),
}


def _ensure_file_dirs():
    for d in FILE_DIRS.values():
        os.makedirs(d, exist_ok=True)


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
    # 仅保留安全字符：字母数字、横线、下划线、方括号
    safe = "".join(c for c in str(code).strip() if c.isalnum() or c in "-_[]")
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
        sql = "INSERT INTO gzh (tjr, gzh, gzhname, year1, year0, ssks) VALUES (%s,%s,%s,%s,%s,%s)"
        db.execute_update(sql, (req.tjr, req.gzh, req.xmm, year1, year0, req.ssks))
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
        bhtime = datetime.now().strftime("%Y-%m-%d")
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
        where_sql = (" AND ".join(where)) if where else "1=1"
        cnt = db.execute_query(f"SELECT COUNT(*) as n FROM bianhao WHERE {where_sql}", params)
        total = (cnt[0]["n"] or 0) if cnt else 0
        offset = (page - 1) * page_size
        order = "ORDER BY bhtime DESC, id DESC LIMIT %s OFFSET %s"
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
        bhtime = datetime.now().strftime("%Y-%m-%d")
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
        where_sql = " AND ".join(where) if where else "1=1"
        cnt = db.execute_query(f"SELECT COUNT(*) as n FROM bianhaogljs WHERE {where_sql}", params)
        total = (cnt[0]["n"] or 0) if cnt else 0
        offset = (page - 1) * page_size
        rows = db.execute_query(f"SELECT * FROM bianhaogljs WHERE {where_sql} ORDER BY bhtime DESC, id DESC LIMIT %s OFFSET %s", (*params, page_size, offset))
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
        bhtime = datetime.now().strftime("%Y-%m-%d")
        sql = """INSERT INTO bianhaogl (xm,bz,fenlei,cpname,neirong,bhtime,bhyear,bianhao1,bianhao2,bianhao3,yj,content)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'0',%s)"""
        db.execute_update(sql, (req.xm, req.bz, req.fenlei, req.xmname or "", req.neirong, bhtime, bhyear, req.fenlei, next_num, bianhao3, (req.content or "").strip()))
        code = f"{req.fenlei}{bhyear}{bianhao3}"
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
        "bianhao_code": f"{b1}{by}{b3}" if (b1 and b3) else "-"
    }


@router.get("/bianhaogl/list")
async def get_bianhaogl_list(
    bz: Optional[str] = Query(None, description="所属科室"),
    px: Optional[str] = Query(None),
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
        where_sql = " AND ".join(where) if where else "1=1"
        cnt = db.execute_query(f"SELECT COUNT(*) as n FROM bianhaogl WHERE {where_sql}", params)
        total = (cnt[0]["n"] or 0) if cnt else 0
        offset = (page - 1) * page_size
        rows = db.execute_query(f"SELECT * FROM bianhaogl WHERE {where_sql} ORDER BY bhtime DESC, id DESC LIMIT %s OFFSET %s", (*params, page_size, offset))
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
# 编号规则：年代(4位) + 工艺部室代码(XXCH) + 顺序号(3位)，如 2015SFCH001（水发室2015年第一份）

ROOM_CODES_GYGCH = [
    {"value": "SFCH", "label": "水发室"},
    # 可在此扩展其他工艺部室（组）代码
]


@router.get("/gygch/room-codes")
async def get_gygch_room_codes():
    """工艺过程策划表 - 工艺部室（组）代码选项"""
    return {"success": True, "list": ROOM_CODES_GYGCH}


class BianhaoGygchRequest(BaseModel):
    xm: str
    bz: str
    bhyear: Optional[int] = None  # 年代，不传则当年
    room_code: str  # 如 SFCH
    neirong: str = ""


@router.post("/gygch/add")
async def add_bianhao_gygch(req: BianhaoGygchRequest):
    """工艺过程策划表编号 - 写入 bianhao_gygch"""
    try:
        if (req.room_code or "").strip() not in [r["value"] for r in ROOM_CODES_GYGCH]:
            raise HTTPException(status_code=400, detail="无效的工艺部室代码")
        bhyear = req.bhyear or datetime.now().year
        room_code = (req.room_code or "").strip()
        max_rows = db.execute_query(
            "SELECT seq FROM bianhao_gygch WHERE bhyear=%s AND room_code=%s ORDER BY seq DESC LIMIT 1",
            (bhyear, room_code)
        )
        next_seq = 1 if not max_rows else (max_rows[0].get("seq") or 0) + 1
        bianhao_code = f"{bhyear}{room_code}{str(next_seq).zfill(3)}"
        bhtime = datetime.now().strftime("%Y-%m-%d")
        rid = uuid.uuid4().hex
        sql = """INSERT INTO bianhao_gygch (id, bz, xm, bhyear, room_code, seq, bianhao_code, neirong, bhtime)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        db.execute_update(sql, (rid, req.bz, req.xm, bhyear, room_code, next_seq, bianhao_code, (req.neirong or "").strip(), bhtime))
        return {"success": True, "message": "编号成功", "bianhao": bianhao_code}
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
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100)
):
    """工艺过程策划表编号列表，按编号时间倒序"""
    try:
        where, params = [], ()
        if (bz or "").strip():
            where.append("bz=%s")
            params = (bz.strip(),)
        where_sql = " AND ".join(where) if where else "1=1"
        cnt = db.execute_query(f"SELECT COUNT(*) as n FROM bianhao_gygch WHERE {where_sql}", params)
        total = (cnt[0]["n"] or 0) if cnt else 0
        offset = (page - 1) * page_size
        rows = db.execute_query(
            f"SELECT * FROM bianhao_gygch WHERE {where_sql} ORDER BY bhtime DESC, id DESC LIMIT %s OFFSET %s",
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
