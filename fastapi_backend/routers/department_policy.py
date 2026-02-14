# -*- coding: utf-8 -*-
"""
部门制度查询 API - 制度上传、制度查询、关键词搜索、预览与下载
支持 PDF、Word(.doc/.docx)、Excel(.xls/.xlsx)
预览时通过 LibreOffice 将 Word/Excel 转为 PDF
"""
import os
import uuid
import subprocess
import shutil
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, File, UploadFile
from fastapi.responses import FileResponse
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from database import db
from config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/department-policy", tags=["部门制度查询"])

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
POLICY_DIR = os.path.join(_DATA_DIR, "policy_files")
PDF_CACHE_DIR = os.path.join(POLICY_DIR, "pdf_cache")


def _get_libreoffice_cmd():
    if getattr(settings, "LIBREOFFICE_CMD", "") and str(settings.LIBREOFFICE_CMD).strip():
        return str(settings.LIBREOFFICE_CMD).strip()
    return shutil.which("libreoffice") or shutil.which("soffice") or "libreoffice"

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx"}
CONVERTIBLE_TYPES = {"doc", "docx", "xls", "xlsx"}
MIME_MAP = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _ensure_policy_dir():
    os.makedirs(POLICY_DIR, exist_ok=True)
    os.makedirs(PDF_CACHE_DIR, exist_ok=True)


def _convert_to_pdf_sync(source_path: str) -> Optional[str]:
    """使用 LibreOffice 将 Word/Excel 转为 PDF，返回 PDF 路径"""
    if not os.path.isfile(source_path):
        return None
    base_name = Path(source_path).stem
    pdf_name = f"{base_name}.pdf"
    pdf_path = os.path.join(PDF_CACHE_DIR, pdf_name)
    if os.path.isfile(pdf_path) and os.path.getmtime(pdf_path) >= os.path.getmtime(source_path):
        return pdf_path
    out_dir = PDF_CACHE_DIR
    cmd = _get_libreoffice_cmd()
    try:
        result = subprocess.run(
            [cmd, "--headless", "--convert-to", "pdf", "--outdir", out_dir, source_path],
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.error(f"LibreOffice 转换失败: {result.stderr.decode('utf-8', errors='ignore')}")
            return None
        if os.path.isfile(pdf_path):
            return pdf_path
    except FileNotFoundError:
        logger.warning("未找到 LibreOffice，请安装 libreoffice 或 soffice")
        return None
    except subprocess.TimeoutExpired:
        logger.error("LibreOffice 转换超时")
        return None
    except Exception as e:
        logger.error(f"LibreOffice 转换异常: {e}")
        return None
    return None


def _row_id(r) -> Optional[str]:
    if not r:
        return None
    raw = r.get("id") if r.get("id") is not None else r.get("ID")
    if raw is None:
        return None
    return str(raw).strip() or None


def _can_upload_policy(name: str) -> bool:
    """仅 yggl 表中 lsys=综合技术室 且 jb=主任/副主任 可上传、删除"""
    if not (name or "").strip():
        return False
    rows = db.execute_query(
        """SELECT 1 FROM yggl WHERE name = %s AND TRIM(COALESCE(lsys,'')) = '综合技术室'
           AND ((jb = '主任' OR jb LIKE '主任%%') OR (jb = '副主任' OR jb LIKE '副主任%%'))
           AND (COALESCE(zaizhi,0)=0) LIMIT 1""",
        ((name or "").strip(),),
    )
    return bool(rows)


@router.get("/can-upload")
async def get_can_upload(name: str = Query(..., description="当前用户名")):
    """检查当前用户是否有制度上传权限（仅综合技术室主任/副主任）"""
    return {"success": True, "canUpload": _can_upload_policy(name)}


class PolicyUploadRequest(BaseModel):
    title: str
    keywords: Optional[str] = ""
    remark: Optional[str] = ""


@router.post("/upload")
async def upload_policy(
    title: str = Query(..., description="制度标题"),
    issue_time: str = Query(..., description="发行时间，格式 YYYY-MM-DD"),
    remark: Optional[str] = Query("", description="备注"),
    uploader: Optional[str] = Query("", description="上传人"),
    file: UploadFile = File(...),
):
    """上传制度文件，支持 PDF、Word、Excel。仅综合技术室主任/副主任可上传"""
    uploader_name = (uploader or "").strip()
    if not _can_upload_policy(uploader_name):
        raise HTTPException(status_code=403, detail="仅综合技术室主任/副主任可上传制度")
    fn = (file.filename or "").strip()
    if not fn:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    ext = os.path.splitext(fn)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"仅支持 PDF、Word(.doc/.docx)、Excel(.xls/.xlsx) 格式",
        )
    file_type = ext.lstrip(".")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    _ensure_policy_dir()
    rid = uuid.uuid4().hex
    safe_name = f"{rid}{ext}"
    file_path_rel = f"policy_files/{safe_name}"
    full_path = os.path.join(POLICY_DIR, safe_name)

    try:
        with open(full_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"写入文件失败: {e}")
        raise HTTPException(status_code=500, detail="保存文件失败")

    uploader = uploader_name
    issue_time_val = (issue_time or "").strip()
    if not issue_time_val:
        raise HTTPException(status_code=400, detail="发行时间为必填项")
    sql = """INSERT INTO dept_policy (id, title, keywords, file_name, file_path, file_type, uploader, issue_time, remark)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    db.execute_update(
        sql,
        (
            rid,
            (title or "").strip(),
            "",
            fn,
            file_path_rel,
            file_type,
            uploader,
            issue_time_val,
            (remark or "").strip(),
        ),
    )
    # 向量化入库（异步，不阻塞返回）
    try:
        from services.policy_vector import add_to_index
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            None,
            lambda: add_to_index(rid, (title or "").strip(), issue_time_val, (remark or "").strip(), file_path_rel, file_type),
        )
    except Exception as e:
        logger.warning(f"向量入库异步失败: {e}")
    return {"success": True, "message": "上传成功", "id": rid}


@router.get("/list")
async def get_policy_list(
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """制度列表，支持关键词搜索（标题、关键词、备注）"""
    try:
        where, params = [], ()
        if (keyword or "").strip():
            kw = f"%{(keyword or '').strip()}%"
            where.append("title LIKE %s")
            params = (kw,)
        where_sql = " AND ".join(where) if where else "1=1"
        cnt = db.execute_query(f"SELECT COUNT(*) as n FROM dept_policy WHERE {where_sql}", params)
        total = (cnt[0]["n"] or 0) if cnt else 0
        offset = (page - 1) * page_size
        rows = db.execute_query(
            f"SELECT * FROM dept_policy WHERE {where_sql} ORDER BY upload_time DESC LIMIT %s OFFSET %s",
            (*params, page_size, offset),
        )

        def _fmt(r):
            return {
                "id": _row_id(r),
                "title": (r.get("title") or "").strip(),
                "keywords": (r.get("keywords") or "").strip(),
                "file_name": (r.get("file_name") or "").strip(),
                "file_path": (r.get("file_path") or "").strip(),
                "file_type": (r.get("file_type") or "").lower(),
                "uploader": (r.get("uploader") or "").strip(),
                "upload_time": str(r.get("upload_time") or "")[:19] if r.get("upload_time") else "",
                "issue_time": (r.get("issue_time") or "").strip(),
                "remark": (r.get("remark") or "").strip(),
            }

        return {
            "success": True,
            "list": [_fmt(r) for r in (rows or [])],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }
    except Exception as e:
        logger.error(f"查询制度列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vector-search")
async def vector_search_policy(
    query: str = Query(..., description="自然语言查询"),
    top_k: int = Query(20, ge=1, le=50, description="返回条数"),
):
    """AI 深度搜索：基于 bge-small-zh 向量检索"""
    if not (query or "").strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")
    try:
        from services.policy_vector import search
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: search(query.strip(), top_k))
        if not results:
            return {"success": True, "list": []}
        ids = [r[0] for r in results]
        scores = {r[0]: r[1] for r in results}
        snippets = {r[0]: r[2] for r in results}
        placeholders = ",".join(["%s"] * len(ids))
        rows = db.execute_query(
            f"SELECT * FROM dept_policy WHERE id IN ({placeholders})",
            tuple(ids),
        )
        id_order = {pid: i for i, pid in enumerate(ids)}
        def _get_snippet(pid, r):
            s = (snippets.get(pid) or "").strip()
            if s:
                return s
            file_path = (r.get("file_path") or "").strip()
            file_type = (r.get("file_type") or "").lower()
            if file_path and file_type:
                try:
                    from services.policy_vector import extract_text_from_file
                    full = os.path.normpath(os.path.join(_DATA_DIR, file_path.replace("/", os.sep)))
                    text = extract_text_from_file(full, file_type)
                    return (text[:200] + "…") if len(text) > 200 else text
                except Exception:
                    pass
            title = (r.get("title") or "").strip()
            remark = (r.get("remark") or "").strip()
            return f"{title} {remark}".strip() or "—"
        def _fmt(r):
            pid = _row_id(r)
            return {
                "id": pid,
                "title": (r.get("title") or "").strip(),
                "file_name": (r.get("file_name") or "").strip(),
                "file_path": (r.get("file_path") or "").strip(),
                "file_type": (r.get("file_type") or "").lower(),
                "uploader": (r.get("uploader") or "").strip(),
                "upload_time": str(r.get("upload_time") or "")[:19] if r.get("upload_time") else "",
                "issue_time": (r.get("issue_time") or "").strip(),
                "remark": (r.get("remark") or "").strip(),
                "score": scores.get(pid),
                "snippet": _get_snippet(pid, r),
            }
        out = [_fmt(r) for r in (rows or [])]
        out.sort(key=lambda x: id_order.get(x["id"], 999))
        return {"success": True, "list": out}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"向量检索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file")
async def get_policy_file(
    id: str = Query(..., description="记录ID"),
    download: Optional[int] = Query(0, description="1=下载，0=预览"),
):
    """预览或下载制度文件。PDF 直接预览；Word/Excel 通过 LibreOffice 转为 PDF 后预览"""
    if not (id or "").strip():
        raise HTTPException(status_code=400, detail="缺少记录ID")
    rid = (id or "").strip()
    rows = db.execute_query("SELECT file_path, file_name, file_type FROM dept_policy WHERE id=%s", (rid,))
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    r = rows[0]
    rel_path = (r.get("file_path") or "").strip()
    if not rel_path:
        raise HTTPException(status_code=404, detail="文件路径为空")
    full_path = os.path.normpath(os.path.join(_DATA_DIR, rel_path.replace("/", os.sep)))

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    file_name = (r.get("file_name") or "").strip() or os.path.basename(full_path)
    file_type = (r.get("file_type") or "").lower()

    serve_path = full_path
    serve_name = file_name
    media_type = MIME_MAP.get(f"." + file_type, "application/octet-stream")
    disposition = "attachment" if download else "inline"

    # 预览且为 Word/Excel 时，转为 PDF 后返回
    if download == 0 and file_type in CONVERTIBLE_TYPES:
        loop = asyncio.get_event_loop()
        pdf_path = await loop.run_in_executor(None, _convert_to_pdf_sync, full_path)
        if pdf_path:
            serve_path = pdf_path
            serve_name = Path(file_name).stem + ".pdf"
            media_type = "application/pdf"
        else:
            # 转换失败时退化为下载
            disposition = "attachment"

    return FileResponse(
        serve_path,
        media_type=media_type,
        filename=serve_name,
        content_disposition_type=disposition,
    )


@router.delete("/delete")
async def delete_policy(
    id: str = Query(..., description="记录ID"),
    current_user: Optional[str] = Query("", description="当前用户名，用于权限校验"),
):
    """删除制度记录及文件。仅综合技术室主任/副主任可删除"""
    if not _can_upload_policy((current_user or "").strip()):
        raise HTTPException(status_code=403, detail="仅综合技术室主任/副主任可删除制度")
    rid = (id or "").strip()
    if not rid:
        raise HTTPException(status_code=400, detail="缺少记录ID")
    rows = db.execute_query("SELECT file_path FROM dept_policy WHERE id=%s", (rid,))
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    rel_path = (rows[0].get("file_path") or "").strip()
    full_path = os.path.normpath(os.path.join(_DATA_DIR, rel_path.replace("/", os.sep)))
    if os.path.isfile(full_path):
        try:
            os.remove(full_path)
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
        # 删除对应的 PDF 缓存
        base_name = Path(full_path).stem
        pdf_cache = os.path.join(PDF_CACHE_DIR, f"{base_name}.pdf")
        if os.path.isfile(pdf_cache):
            try:
                os.remove(pdf_cache)
            except Exception:
                pass
    try:
        from services.policy_vector import remove_from_index
        remove_from_index(rid)
    except Exception:
        pass
    db.execute_update("DELETE FROM dept_policy WHERE id=%s", (rid,))
    return {"success": True, "message": "已删除"}
