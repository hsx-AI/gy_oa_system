# -*- coding: utf-8 -*-
"""
工艺技术问题手册 API
- 问题的增删改查、图片上传与访问、分类列表、模糊搜索
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional, List
from datetime import datetime
from database import db
from config import settings
from pathlib import Path
import uuid
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tech-problem", tags=["工艺技术问题手册"])

_BASE = Path(__file__).resolve().parent.parent
UPLOAD_DIR = _BASE / settings.UPLOAD_DIR / "tech_problem_images"

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def _ensure_upload_dir():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_table():
    sql = """
    CREATE TABLE IF NOT EXISTS tech_problem_manual (
        id INT AUTO_INCREMENT PRIMARY KEY,
        category VARCHAR(100) NOT NULL COMMENT '分类',
        department VARCHAR(100) DEFAULT NULL COMMENT '所属专业（yggl.lsys）',
        title VARCHAR(300) NOT NULL COMMENT '主题',
        recorder VARCHAR(100) NOT NULL COMMENT '记录人',
        record_time VARCHAR(20) DEFAULT NULL COMMENT '记录时间（年-月）',
        problem_desc TEXT COMMENT '问题描述',
        problem_images JSON COMMENT '问题描述配图文件名列表',
        cause_analysis TEXT COMMENT '原因分析',
        cause_images JSON COMMENT '原因分析配图文件名列表',
        measures TEXT COMMENT '采取措施及效果',
        measures_images JSON COMMENT '措施配图文件名列表',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_category (category),
        INDEX idx_department (department),
        FULLTEXT INDEX idx_ft (title, problem_desc, cause_analysis, measures) WITH PARSER ngram
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工艺技术问题手册';
    """
    try:
        db.execute_update(sql)
    except Exception as e:
        logger.warning("tech_problem_manual 建表/检查: %s", e)


_ensure_table()

try:
    db.execute_update(
        "ALTER TABLE tech_problem_manual ADD COLUMN department VARCHAR(100) DEFAULT NULL COMMENT '所属专业（yggl.lsys）' AFTER category"
    )
except Exception:
    pass


def _parse_json_images(val):
    """从数据库读取的 JSON 图片列表"""
    if not val:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return []
    return []


async def _save_uploaded_images(files: List[UploadFile]) -> List[str]:
    """保存上传的图片文件，返回文件名列表"""
    _ensure_upload_dir()
    saved = []
    for f in files:
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXT:
            raise HTTPException(status_code=400, detail=f"不支持的图片格式: {ext}")
        content = await f.read()
        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail=f"图片 {f.filename} 超过 5MB 限制")
        safe_name = f"tp_{uuid.uuid4().hex[:12]}{ext}"
        save_path = UPLOAD_DIR / safe_name
        with open(save_path, "wb") as fp:
            fp.write(content)
        saved.append(safe_name)
    return saved


@router.get("/list")
def list_problems(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
):
    """问题列表，支持分类 / 专业筛选和关键词模糊搜索"""
    where_parts = []
    params = []

    if category:
        where_parts.append("category = %s")
        params.append(category)

    if department:
        where_parts.append("department = %s")
        params.append(department)

    if keyword:
        kw = f"%{keyword}%"
        where_parts.append("(title LIKE %s OR problem_desc LIKE %s OR cause_analysis LIKE %s OR measures LIKE %s OR recorder LIKE %s OR department LIKE %s)")
        params.extend([kw, kw, kw, kw, kw, kw])

    where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

    count_sql = f"SELECT COUNT(*) AS cnt FROM tech_problem_manual{where_sql}"
    row = db.execute_query(count_sql, tuple(params))
    total = (row[0]["cnt"] if row else 0)

    offset = (page - 1) * page_size
    data_sql = f"""
        SELECT id, category, department, title, recorder, record_time, measures,
               created_at, updated_at
        FROM tech_problem_manual{where_sql}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    rows = db.execute_query(data_sql, tuple(params) + (page_size, offset))

    items = []
    for r in (rows or []):
        items.append({
            "id": r["id"],
            "category": r.get("category", ""),
            "department": r.get("department", ""),
            "title": r.get("title", ""),
            "recorder": r.get("recorder", ""),
            "record_time": r.get("record_time", ""),
            "measures": bool(r.get("measures")),
            "created_at": str(r["created_at"]) if r.get("created_at") else "",
        })

    return {"list": items, "total": total, "page": page, "page_size": page_size}


@router.get("/detail")
def get_detail(id: int = Query(...)):
    """获取单条问题详情"""
    rows = db.execute_query(
        "SELECT * FROM tech_problem_manual WHERE id = %s", (id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    r = rows[0]
    return {
        "id": r["id"],
        "category": r.get("category", ""),
        "department": r.get("department", ""),
        "title": r.get("title", ""),
        "recorder": r.get("recorder", ""),
        "record_time": r.get("record_time", ""),
        "problem_desc": r.get("problem_desc", ""),
        "problem_images": _parse_json_images(r.get("problem_images")),
        "cause_analysis": r.get("cause_analysis", ""),
        "cause_images": _parse_json_images(r.get("cause_images")),
        "measures": r.get("measures", ""),
        "measures_images": _parse_json_images(r.get("measures_images")),
        "created_at": str(r["created_at"]) if r.get("created_at") else "",
        "updated_at": str(r["updated_at"]) if r.get("updated_at") else "",
    }


@router.post("/create")
async def create_problem(
    category: str = Form(...),
    department: str = Form(""),
    title: str = Form(...),
    recorder: str = Form(...),
    record_time: str = Form(...),
    problem_desc: str = Form(...),
    cause_analysis: str = Form(...),
    measures: str = Form(""),
    problem_files: List[UploadFile] = File(default=[]),
    cause_files: List[UploadFile] = File(default=[]),
    measures_files: List[UploadFile] = File(default=[]),
    existing_problem_images: str = Form("[]"),
    existing_cause_images: str = Form("[]"),
    existing_measures_images: str = Form("[]"),
):
    """新建问题记录"""
    problem_imgs = await _save_uploaded_images(problem_files)
    cause_imgs = await _save_uploaded_images(cause_files)
    measures_imgs = await _save_uploaded_images(measures_files)

    sql = """
        INSERT INTO tech_problem_manual
            (category, department, title, recorder, record_time, problem_desc, problem_images,
             cause_analysis, cause_images, measures, measures_images)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    db.execute_update(sql, (
        category.strip(), department.strip() or None, title.strip(), recorder.strip(), record_time.strip(),
        problem_desc.strip(), json.dumps(problem_imgs, ensure_ascii=False),
        cause_analysis.strip(), json.dumps(cause_imgs, ensure_ascii=False),
        measures.strip() or None, json.dumps(measures_imgs, ensure_ascii=False),
    ))
    return {"success": True, "message": "创建成功"}


@router.post("/update")
async def update_problem(
    id: int = Query(...),
    category: str = Form(...),
    department: str = Form(""),
    title: str = Form(...),
    recorder: str = Form(...),
    record_time: str = Form(...),
    problem_desc: str = Form(...),
    cause_analysis: str = Form(...),
    measures: str = Form(""),
    problem_files: List[UploadFile] = File(default=[]),
    cause_files: List[UploadFile] = File(default=[]),
    measures_files: List[UploadFile] = File(default=[]),
    existing_problem_images: str = Form("[]"),
    existing_cause_images: str = Form("[]"),
    existing_measures_images: str = Form("[]"),
):
    """更新问题记录"""
    rows = db.execute_query("SELECT id FROM tech_problem_manual WHERE id = %s", (id,))
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")

    try:
        keep_problem = json.loads(existing_problem_images)
    except Exception:
        keep_problem = []
    try:
        keep_cause = json.loads(existing_cause_images)
    except Exception:
        keep_cause = []
    try:
        keep_measures = json.loads(existing_measures_images)
    except Exception:
        keep_measures = []

    new_problem = await _save_uploaded_images(problem_files)
    new_cause = await _save_uploaded_images(cause_files)
    new_measures = await _save_uploaded_images(measures_files)

    final_problem = keep_problem + new_problem
    final_cause = keep_cause + new_cause
    final_measures = keep_measures + new_measures

    sql = """
        UPDATE tech_problem_manual SET
            category = %s, department = %s, title = %s, recorder = %s, record_time = %s,
            problem_desc = %s, problem_images = %s,
            cause_analysis = %s, cause_images = %s,
            measures = %s, measures_images = %s
        WHERE id = %s
    """
    db.execute_update(sql, (
        category.strip(), department.strip() or None, title.strip(), recorder.strip(), record_time.strip(),
        problem_desc.strip(), json.dumps(final_problem, ensure_ascii=False),
        cause_analysis.strip(), json.dumps(final_cause, ensure_ascii=False),
        measures.strip() or None, json.dumps(final_measures, ensure_ascii=False),
        id,
    ))
    return {"success": True, "message": "更新成功"}


@router.delete("/delete")
def delete_problem(id: int = Query(...)):
    """删除问题记录"""
    rows = db.execute_query("SELECT problem_images, cause_images, measures_images FROM tech_problem_manual WHERE id = %s", (id,))
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")

    for field in ["problem_images", "cause_images", "measures_images"]:
        for fname in _parse_json_images(rows[0].get(field)):
            fpath = UPLOAD_DIR / fname
            if fpath.exists():
                try:
                    fpath.unlink()
                except Exception:
                    pass

    db.execute_update("DELETE FROM tech_problem_manual WHERE id = %s", (id,))
    return {"success": True, "message": "删除成功"}


@router.get("/categories")
def get_categories():
    """获取所有已使用的分类"""
    rows = db.execute_query(
        "SELECT DISTINCT category FROM tech_problem_manual WHERE category IS NOT NULL AND category != '' ORDER BY category"
    )
    return {"categories": [r["category"] for r in (rows or [])]}


@router.get("/departments")
def get_departments():
    """获取 yggl 表中的所属专业（lsys）列表，供下拉选择"""
    rows = db.execute_query(
        "SELECT DISTINCT TRIM(lsys) AS lsys FROM yggl "
        "WHERE lsys IS NOT NULL AND TRIM(lsys) != '' "
        "AND TRIM(lsys) NOT IN ('其他部门员工','其他部门成员') "
        "AND COALESCE(zaizhi, 0) = 0 "
        "ORDER BY lsys"
    )
    return {"departments": [r["lsys"] for r in (rows or []) if r.get("lsys")]}


@router.get("/image")
def get_image(filename: str = Query(...)):
    """获取图片文件"""
    safe = Path(filename).name
    fpath = UPLOAD_DIR / safe
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    media_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".bmp": "image/bmp", ".webp": "image/webp",
    }
    ext = fpath.suffix.lower()
    return FileResponse(str(fpath), media_type=media_types.get(ext, "application/octet-stream"))
