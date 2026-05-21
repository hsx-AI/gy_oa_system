# -*- coding: utf-8 -*-
"""
工艺投标模板库 API

提供投标模板的最新版本上传、下载、版本历史和标签筛选能力。
"""
import json
import logging
import mimetypes
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bid-templates", tags=["工艺投标模板库"])

_BASE = Path(__file__).resolve().parent.parent
_DATA_DIR = _BASE / "data"
TEMPLATE_DIR = _DATA_DIR / "bid_template_files"

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".rar",
    ".7z",
}

DEFAULT_MACHINE_TYPES = ["抽蓄", "混流", "轴流", "贯流", "通用"]
DEFAULT_FILE_SCOPES = ["专用文件", "通用文件", "专用及通用文件"]
DEFAULT_SHAFT_TYPES = ["立式", "卧式", "斜式", "通用"]
DEFAULT_SUPPORT_ARM_COUNTS = ["2", "3", "4", "5", "6", "8", "通用"]


def _ensure_dir() -> None:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_tables() -> None:
    db.execute_update(
        """
        CREATE TABLE IF NOT EXISTS bid_templates (
            id VARCHAR(32) NOT NULL PRIMARY KEY,
            title VARCHAR(300) NOT NULL,
            description TEXT,
            created_by VARCHAR(100) DEFAULT '',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            current_version_id VARCHAR(32) DEFAULT NULL,
            version_count INT NOT NULL DEFAULT 0,
            INDEX idx_title (title),
            INDEX idx_updated_at (updated_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工艺投标模板主表'
        """,
        (),
    )
    db.execute_update(
        """
        CREATE TABLE IF NOT EXISTS bid_template_versions (
            id VARCHAR(32) NOT NULL PRIMARY KEY,
            template_id VARCHAR(32) NOT NULL,
            version_no INT NOT NULL,
            file_name VARCHAR(500) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_type VARCHAR(30) NOT NULL,
            file_size BIGINT NOT NULL DEFAULT 0,
            change_note TEXT,
            uploader VARCHAR(100) DEFAULT '',
            upload_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            machine_type VARCHAR(50) DEFAULT '',
            file_scope VARCHAR(50) DEFAULT '',
            speed VARCHAR(100) DEFAULT '',
            capacity VARCHAR(100) DEFAULT '',
            shaft_type VARCHAR(50) DEFAULT '',
            support_arm_count VARCHAR(50) DEFAULT '',
            reference_project VARCHAR(255) DEFAULT '',
            custom_tags_json TEXT,
            UNIQUE KEY uk_template_version (template_id, version_no),
            INDEX idx_template_upload (template_id, upload_time),
            INDEX idx_machine_type (machine_type),
            INDEX idx_file_scope (file_scope),
            INDEX idx_reference_project (reference_project)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工艺投标模板版本表'
        """,
        (),
    )


_ensure_tables()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _dt(value: Any) -> str:
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)[:19]


def _parse_custom_tags(raw: Any) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text = str(raw).strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
    except Exception:
        pass
    parts = text.replace("，", ",").replace("；", ",").replace(";", ",").split(",")
    return [p.strip() for p in parts if p.strip()]


def _json_tags(tags: List[str]) -> str:
    deduped: List[str] = []
    seen = set()
    for tag in tags:
        t = (tag or "").strip()
        if t and t not in seen:
            seen.add(t)
            deduped.append(t)
    return json.dumps(deduped, ensure_ascii=False)


def _format_version(row: Dict[str, Any]) -> Dict[str, Any]:
    tags = _parse_custom_tags(row.get("custom_tags_json"))
    return {
        "id": _text(row.get("version_id") or row.get("id")),
        "template_id": _text(row.get("template_id")),
        "version_no": int(row.get("version_no") or 0),
        "file_name": _text(row.get("file_name")),
        "file_type": _text(row.get("file_type")).lower(),
        "file_size": int(row.get("file_size") or 0),
        "change_note": _text(row.get("change_note")),
        "uploader": _text(row.get("uploader")),
        "upload_time": _dt(row.get("upload_time")),
        "machine_type": _text(row.get("machine_type")),
        "file_scope": _text(row.get("file_scope")),
        "speed": _text(row.get("speed")),
        "capacity": _text(row.get("capacity")),
        "shaft_type": _text(row.get("shaft_type")),
        "support_arm_count": _text(row.get("support_arm_count")),
        "reference_project": _text(row.get("reference_project")),
        "custom_tags": tags,
    }


def _format_template(row: Dict[str, Any]) -> Dict[str, Any]:
    version = _format_version(row)
    return {
        "id": _text(row.get("template_id") or row.get("id")),
        "title": _text(row.get("title")),
        "description": _text(row.get("description")),
        "created_by": _text(row.get("created_by")),
        "created_at": _dt(row.get("created_at")),
        "updated_at": _dt(row.get("updated_at")),
        "current_version_id": _text(row.get("current_version_id")),
        "version_count": int(row.get("version_count") or 0),
        "latest": version,
    }


@router.get("/options")
async def get_options():
    """获取下拉选项，包含固定选项和历史已用值。"""
    _ensure_tables()

    def distinct(col: str) -> List[str]:
        rows = db.execute_query(
            f"""
            SELECT DISTINCT {col} AS val
            FROM bid_template_versions
            WHERE {col} IS NOT NULL AND TRIM({col}) != ''
            ORDER BY {col}
            """,
            (),
        )
        return [_text(r.get("val")) for r in (rows or []) if _text(r.get("val"))]

    def merge(defaults: List[str], used: List[str]) -> List[str]:
        out: List[str] = []
        for item in defaults + used:
            if item and item not in out:
                out.append(item)
        return out

    return {
        "success": True,
        "machine_types": merge(DEFAULT_MACHINE_TYPES, distinct("machine_type")),
        "file_scopes": merge(DEFAULT_FILE_SCOPES, distinct("file_scope")),
        "shaft_types": merge(DEFAULT_SHAFT_TYPES, distinct("shaft_type")),
        "support_arm_counts": merge(DEFAULT_SUPPORT_ARM_COUNTS, distinct("support_arm_count")),
        "reference_projects": distinct("reference_project"),
    }


@router.get("/list")
async def list_templates(
    keyword: Optional[str] = Query(None),
    machine_type: Optional[str] = Query(None),
    file_scope: Optional[str] = Query(None),
    shaft_type: Optional[str] = Query(None),
    support_arm_count: Optional[str] = Query(None),
    reference_project: Optional[str] = Query(None),
    custom_tag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """查询模板列表，只返回每个模板的最新版本。"""
    _ensure_tables()
    where = ["t.current_version_id IS NOT NULL"]
    params: List[Any] = []

    kw = _text(keyword)
    if kw:
        like = f"%{kw}%"
        where.append(
            """
            (t.title LIKE %s OR t.description LIKE %s OR v.file_name LIKE %s OR
             v.change_note LIKE %s OR v.speed LIKE %s OR v.capacity LIKE %s OR
             v.reference_project LIKE %s OR v.custom_tags_json LIKE %s)
            """
        )
        params.extend([like, like, like, like, like, like, like, like])

    exact_filters = {
        "v.machine_type": machine_type,
        "v.file_scope": file_scope,
        "v.shaft_type": shaft_type,
        "v.support_arm_count": support_arm_count,
    }
    for col, value in exact_filters.items():
        text = _text(value)
        if text:
            where.append(f"{col} = %s")
            params.append(text)

    ref = _text(reference_project)
    if ref:
        where.append("v.reference_project LIKE %s")
        params.append(f"%{ref}%")

    tag = _text(custom_tag)
    if tag:
        where.append("v.custom_tags_json LIKE %s")
        params.append(f"%{tag}%")

    where_sql = " AND ".join(where)
    total = db.execute_scalar(
        f"""
        SELECT COUNT(*) AS cnt
        FROM bid_templates t
        JOIN bid_template_versions v ON v.id = t.current_version_id
        WHERE {where_sql}
        """,
        tuple(params),
    ) or 0
    offset = (page - 1) * page_size
    rows = db.execute_query(
        f"""
        SELECT
            t.id AS template_id, t.title, t.description, t.created_by, t.created_at,
            t.updated_at, t.current_version_id, t.version_count,
            v.id AS version_id, v.version_no, v.file_name, v.file_path, v.file_type,
            v.file_size, v.change_note, v.uploader, v.upload_time,
            v.machine_type, v.file_scope, v.speed, v.capacity, v.shaft_type,
            v.support_arm_count, v.reference_project, v.custom_tags_json
        FROM bid_templates t
        JOIN bid_template_versions v ON v.id = t.current_version_id
        WHERE {where_sql}
        ORDER BY v.upload_time DESC, t.updated_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [page_size, offset]),
    )
    return {
        "success": True,
        "list": [_format_template(r) for r in (rows or [])],
        "total": int(total),
        "page": page,
        "pageSize": page_size,
    }


@router.post("/upload")
async def upload_template(
    title: str = Form(...),
    template_id: str = Form(""),
    description: str = Form(""),
    change_note: str = Form(...),
    uploader: str = Form(""),
    machine_type: str = Form(""),
    file_scope: str = Form(""),
    speed: str = Form(""),
    capacity: str = Form(""),
    shaft_type: str = Form(""),
    support_arm_count: str = Form(""),
    reference_project: str = Form(""),
    custom_tags: str = Form(""),
    file: UploadFile = File(...),
):
    """上传新模板或给已有模板新增一个版本。"""
    _ensure_tables()
    _ensure_dir()

    title = _text(title)
    tid = _text(template_id)
    note = _text(change_note)
    if not title:
        raise HTTPException(status_code=400, detail="模板名称不能为空")
    if not note:
        raise HTTPException(status_code=400, detail="请填写本次更新要点")

    original_name = _text(file.filename)
    if not original_name:
        raise HTTPException(status_code=400, detail="请选择文件")
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支持的文件格式")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    if tid:
        rows = db.execute_query(
            "SELECT id, version_count FROM bid_templates WHERE id = %s LIMIT 1",
            (tid,),
        )
        if not rows:
            raise HTTPException(status_code=404, detail="模板不存在")
        version_no = int(rows[0].get("version_count") or 0) + 1
        db.execute_update(
            "UPDATE bid_templates SET title=%s, description=%s WHERE id=%s",
            (title, _text(description), tid),
        )
    else:
        tid = uuid.uuid4().hex
        version_no = 1
        db.execute_update(
            """
            INSERT INTO bid_templates (id, title, description, created_by)
            VALUES (%s, %s, %s, %s)
            """,
            (tid, title, _text(description), _text(uploader)),
        )

    vid = uuid.uuid4().hex
    safe_name = f"{vid}{ext}"
    file_path = TEMPLATE_DIR / safe_name
    try:
        file_path.write_bytes(content)
    except Exception as e:
        logger.error("保存投标模板文件失败: %s", e)
        raise HTTPException(status_code=500, detail="保存文件失败")

    rel_path = f"bid_template_files/{safe_name}"
    affected = db.execute_update(
        """
        INSERT INTO bid_template_versions
            (id, template_id, version_no, file_name, file_path, file_type, file_size,
             change_note, uploader, machine_type, file_scope, speed, capacity,
             shaft_type, support_arm_count, reference_project, custom_tags_json)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            vid,
            tid,
            version_no,
            original_name,
            rel_path,
            ext.lstrip("."),
            len(content),
            note,
            _text(uploader),
            _text(machine_type),
            _text(file_scope),
            _text(speed),
            _text(capacity),
            _text(shaft_type),
            _text(support_arm_count),
            _text(reference_project),
            _json_tags(_parse_custom_tags(custom_tags)),
        ),
    )
    if affected < 0:
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="保存版本记录失败")

    db.execute_update(
        """
        UPDATE bid_templates
        SET current_version_id=%s, version_count=%s, updated_at=NOW()
        WHERE id=%s
        """,
        (vid, version_no, tid),
    )
    return {
        "success": True,
        "message": "上传成功",
        "template_id": tid,
        "version_id": vid,
        "version_no": version_no,
    }


@router.get("/history")
async def get_history(template_id: str = Query(...)):
    """获取某个模板的历史版本。"""
    _ensure_tables()
    tid = _text(template_id)
    rows = db.execute_query(
        """
        SELECT title, description, current_version_id
        FROM bid_templates
        WHERE id=%s
        LIMIT 1
        """,
        (tid,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="模板不存在")
    versions = db.execute_query(
        """
        SELECT id, template_id, version_no, file_name, file_type, file_size,
               change_note, uploader, upload_time, machine_type, file_scope,
               speed, capacity, shaft_type, support_arm_count, reference_project,
               custom_tags_json
        FROM bid_template_versions
        WHERE template_id=%s
        ORDER BY version_no DESC
        """,
        (tid,),
    )
    return {
        "success": True,
        "template": {
            "id": tid,
            "title": _text(rows[0].get("title")),
            "description": _text(rows[0].get("description")),
            "current_version_id": _text(rows[0].get("current_version_id")),
        },
        "versions": [_format_version(v) for v in (versions or [])],
    }


@router.get("/file")
async def get_file(
    template_id: Optional[str] = Query(None),
    version_id: Optional[str] = Query(None),
):
    """下载最新版本或指定历史版本。"""
    _ensure_tables()
    vid = _text(version_id)
    tid = _text(template_id)
    if not vid:
        if not tid:
            raise HTTPException(status_code=400, detail="缺少模板ID或版本ID")
        rows = db.execute_query(
            "SELECT current_version_id FROM bid_templates WHERE id=%s LIMIT 1",
            (tid,),
        )
        if not rows or not rows[0].get("current_version_id"):
            raise HTTPException(status_code=404, detail="模板不存在")
        vid = _text(rows[0].get("current_version_id"))

    rows = db.execute_query(
        """
        SELECT file_path, file_name, file_type
        FROM bid_template_versions
        WHERE id=%s
        LIMIT 1
        """,
        (vid,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="版本不存在")
    row = rows[0]
    rel = _text(row.get("file_path"))
    full_path = (_DATA_DIR / Path(*rel.split("/"))).resolve()
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    media_type = mimetypes.guess_type(str(full_path))[0] or "application/octet-stream"
    return FileResponse(
        str(full_path),
        media_type=media_type,
        filename=_text(row.get("file_name")) or full_path.name,
        content_disposition_type="attachment",
    )
