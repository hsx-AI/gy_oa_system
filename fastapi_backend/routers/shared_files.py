# -*- coding: utf-8 -*-
"""Collaborative office module: folders visibility + leader file ops + blank docs."""
from __future__ import annotations

import io
import json
import logging
import mimetypes
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from openpyxl import Workbook
from pydantic import BaseModel, Field

from config import settings
from database import db
from services import onlyoffice_security as oo_sec
from services import shared_file_storage as storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shared-files", tags=["collab-office"])

OTHER_DEPT_LSYS = ("其他部门员工", "其他部门成员")
ALLOWED_UPLOAD_EXT = {"doc", "docx", "xls", "xlsx", "ppt", "pptx"}
BLANK_CREATE_EXT = {"docx", "xlsx", "pptx"}

MIME_BY_EXT = {
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
DOC_TYPE_BY_EXT = {
    "doc": "word", "docx": "word",
    "xls": "cell", "xlsx": "cell",
    "ppt": "slide", "pptx": "slide",
}

# Level keys used in folder visibility_levels JSON
LEVEL_OPTIONS = [{'key': '部长', 'label': '部领导（部长/经理）'}, {'key': '副部长', 'label': '部领导（副部长/副经理/经理助理）'}, {'key': '主任', 'label': '室主任'}, {'key': '副主任', 'label': '室副主任'}, {'key': '组长', 'label': '班组长/组长'}]

ROLE_MAP = {'部长': ['部长', '经理'], '副部长': ['副部长', '副经理', '经理助理'], '主任': ['主任'], '副主任': ['副主任'], '组长': ['组长', '班组长']}

DDL = """
CREATE TABLE IF NOT EXISTS shared_files (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(500) NOT NULL,
  file_type VARCHAR(50) NOT NULL DEFAULT '',
  mime_type VARCHAR(200) NOT NULL DEFAULT '',
  parent_id BIGINT NULL,
  storage_path VARCHAR(1000) NOT NULL DEFAULT '',
  size BIGINT NOT NULL DEFAULT 0,
  owner_id VARCHAR(100) NOT NULL DEFAULT '',
  created_by VARCHAR(100) NOT NULL DEFAULT '',
  updated_by VARCHAR(100) NOT NULL DEFAULT '',
  version INT NOT NULL DEFAULT 1,
  is_folder TINYINT NOT NULL DEFAULT 0,
  is_deleted TINYINT NOT NULL DEFAULT 0,
  visibility_type VARCHAR(20) NOT NULL DEFAULT 'all',
  visibility_depts TEXT NULL,
  visibility_levels TEXT NULL,
  last_saved_key VARCHAR(100) NOT NULL DEFAULT '',
  last_saved_url VARCHAR(2000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_parent_deleted (parent_id, is_deleted),
  KEY idx_owner (owner_id),
  KEY idx_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='collab office files'
"""

_NAME_BAD = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _ensure_tables() -> None:
    try:
        db.execute_update(DDL, ())
    except Exception as e:
        logger.error("create shared_files failed: %s", e)
    for stmt in (
        "ALTER TABLE shared_files ADD COLUMN visibility_type VARCHAR(20) NOT NULL DEFAULT 'all'",
        "ALTER TABLE shared_files ADD COLUMN visibility_depts TEXT NULL",
        "ALTER TABLE shared_files ADD COLUMN visibility_levels TEXT NULL",
    ):
        try:
            db.execute_update(stmt, ())
        except Exception:
            pass


def _get_admin1() -> Optional[str]:
    try:
        from routers.db_manager import _get_admin1 as _admin1
        return _admin1()
    except Exception:
        return None


def _get_user_row(name: str) -> Optional[Dict[str, Any]]:
    clean = (name or "").strip()
    if not clean:
        return None
    rows = db.execute_query(
        "SELECT name, lsys, jb, gh FROM yggl WHERE name=%s AND COALESCE(zaizhi,0)=0 LIMIT 1",
        (clean,),
    )
    return rows[0] if rows else None


def is_admin1(name: str) -> bool:
    admin1 = _get_admin1()
    return bool(admin1 and (name or "").strip() == admin1)


def _jb_norm(jb: str) -> str:
    return (jb or "").strip()


def _jb_match(jb: str, target: str) -> bool:
    j = _jb_norm(jb)
    if not j:
        return False
    titles = ROLE_MAP.get(target)
    if titles:
        for t in titles:
            if j == t or j.startswith(t):
                return True
        if target == "副主任" and "副主任" in j:
            return True
        return False
    return j == target or j.startswith(target)


def is_minister_level(jb: str) -> bool:
    return _jb_match(jb, "部长") or _jb_match(jb, "副部长")


def is_director_level(jb: str) -> bool:
    return _jb_match(jb, "主任") or _jb_match(jb, "副主任")


def is_team_leader(jb: str) -> bool:
    return _jb_match(jb, "组长")


def can_manage_files(user: Dict[str, Any]) -> bool:
    """Upload / create blank / delete files: dept leaders + room directors + team leaders + admin1."""
    name = (user.get("name") or "").strip()
    if is_admin1(name):
        return True
    jb = user.get("jb") or ""
    return is_minister_level(jb) or is_director_level(jb) or is_team_leader(jb)


def can_access_module(name: str) -> Tuple[bool, str]:
    user = _get_user_row(name)
    if not user:
        return False, "用户不存在或已离职"
    if is_admin1(name):
        return True, ""
    lsys = (user.get("lsys") or "").strip()
    if lsys in OTHER_DEPT_LSYS:
        return False, "外部门用户暂不可访问协同办公"
    if not lsys:
        return False, "未分配科室，无法访问协同办公"
    return True, ""


def require_module_access(name: str) -> Dict[str, Any]:
    ok, msg = can_access_module(name)
    if not ok:
        logger.warning("collab denied user=%s reason=%s", name, msg)
        raise HTTPException(status_code=403, detail=msg or "没有权限")
    user = _get_user_row(name)
    assert user is not None
    return user


def require_admin1(name: str) -> Dict[str, Any]:
    user = require_module_access(name)
    if not is_admin1(name):
        raise HTTPException(status_code=403, detail="仅系统管理员可管理文件夹")
    return user


def require_file_manager(name: str) -> Dict[str, Any]:
    user = require_module_access(name)
    if not can_manage_files(user):
        raise HTTPException(status_code=403, detail="仅部领导、室主任、班组长可上传/新建/删除文件")
    return user


def _parse_json_list(raw: Any) -> List[str]:
    if raw is None:
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
    return []


def _visibility_of(row: Dict[str, Any]) -> Dict[str, Any]:
    vtype = (row.get("visibility_type") or "all").strip().lower()
    if vtype not in ("all", "restricted"):
        vtype = "all"
    return {
        "visibility_type": vtype,
        "visibility_depts": _parse_json_list(row.get("visibility_depts")),
        "visibility_levels": _parse_json_list(row.get("visibility_levels")),
    }


def user_can_see_folder(user: Dict[str, Any], folder_row: Dict[str, Any]) -> bool:
    name = (user.get("name") or "").strip()
    if is_admin1(name):
        return True
    vis = _visibility_of(folder_row)
    if vis["visibility_type"] == "all":
        return True
    depts = vis["visibility_depts"]
    levels = vis["visibility_levels"]
    lsys = (user.get("lsys") or "").strip()
    jb = user.get("jb") or ""
    dept_ok = (not depts) or (lsys in depts)
    level_ok = True
    if levels:
        level_ok = any(_jb_match(jb, lv) for lv in levels)
    return bool(dept_ok and level_ok)


def get_file_row(file_id: int, *, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
    if include_deleted:
        rows = db.execute_query("SELECT * FROM shared_files WHERE id=%s LIMIT 1", (file_id,))
    else:
        rows = db.execute_query(
            "SELECT * FROM shared_files WHERE id=%s AND COALESCE(is_deleted,0)=0 LIMIT 1",
            (file_id,),
        )
    return rows[0] if rows else None


def _assert_folder_visible(user: Dict[str, Any], folder_id: Optional[int]) -> None:
    if folder_id is None:
        return
    folder = get_file_row(folder_id)
    if not folder or not folder.get("is_folder"):
        raise HTTPException(status_code=404, detail="父目录不存在")
    if not user_can_see_folder(user, folder):
        raise HTTPException(status_code=403, detail="无权访问该文件夹")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean_name(name: str) -> str:
    clean = (name or "").strip()
    if not clean:
        raise HTTPException(status_code=400, detail="名称不能为空")
    if _NAME_BAD.search(clean) or clean in (".", ".."):
        raise HTTPException(status_code=400, detail="名称包含非法字符")
    return clean[:200]


def _normalize_parent_id(parent_id: Optional[int]) -> Optional[int]:
    if parent_id is None or int(parent_id) <= 0:
        return None
    return int(parent_id)


def _assert_parent_folder(parent_id: Optional[int]) -> None:
    if parent_id is None:
        return
    parent = get_file_row(parent_id)
    if not parent:
        raise HTTPException(status_code=404, detail="父目录不存在")
    if not parent.get("is_folder"):
        raise HTTPException(status_code=400, detail="父级必须是文件夹")


def _name_exists(parent_id: Optional[int], name: str, *, exclude_id: Optional[int] = None) -> bool:
    if parent_id is None:
        sql = "SELECT id FROM shared_files WHERE parent_id IS NULL AND name=%s AND COALESCE(is_deleted,0)=0"
        params: tuple = (name,)
    else:
        sql = "SELECT id FROM shared_files WHERE parent_id=%s AND name=%s AND COALESCE(is_deleted,0)=0"
        params = (parent_id, name)
    if exclude_id:
        sql += " AND id<>%s"
        params = params + (exclude_id,)
    sql += " LIMIT 1"
    return bool(db.execute_query(sql, params))


def _max_upload_bytes() -> int:
    mb = int(getattr(settings, "SHARED_FILES_MAX_SIZE_MB", 50) or 50)
    return max(1, mb) * 1024 * 1024


def _perm_flags(user: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, bool]:
    name = (user.get("name") or "").strip()
    admin = is_admin1(name)
    file_mgr = can_manage_files(user)
    is_folder = bool(row.get("is_folder"))
    file_type = (row.get("file_type") or "").lower()
    return {
        "can_edit": (not is_folder) and file_type in DOC_TYPE_BY_EXT,
        "can_rename": admin if is_folder else (admin or file_mgr),
        "can_delete": admin if is_folder else file_mgr,
        "can_set_visibility": admin and is_folder,
    }


def _serialize_item(row: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    fid = int(row["id"])
    version = int(row.get("version") or 1)
    is_folder = bool(row.get("is_folder"))
    file_type = (row.get("file_type") or "").lower()
    flags = _perm_flags(user, row)
    data = {
        "id": fid,
        "name": row.get("name"),
        "file_type": file_type,
        "mime_type": row.get("mime_type") or "",
        "parent_id": row.get("parent_id"),
        "size": int(row.get("size") or 0),
        "version": version,
        "is_folder": is_folder,
        "created_by": row.get("created_by") or "",
        "updated_by": row.get("updated_by") or "",
        "created_at": str(row.get("created_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
        "document_key": None if is_folder else oo_sec.build_document_key(fid, version),
        **flags,
    }
    if is_folder:
        data.update(_visibility_of(row))
    return data


def _breadcrumb(file_id: Optional[int], user: Dict[str, Any]) -> List[Dict[str, Any]]:
    crumbs: List[Dict[str, Any]] = []
    seen = set()
    cur = file_id
    while cur:
        if cur in seen:
            break
        seen.add(cur)
        row = get_file_row(cur)
        if not row:
            break
        crumbs.append({"id": int(row["id"]), "name": row.get("name") or ""})
        parent = row.get("parent_id")
        cur = int(parent) if parent else None
    crumbs.reverse()
    return crumbs


def _ensure_phase2_test_file() -> None:
    try:
        existing = db.execute_query(
            "SELECT id, storage_path FROM shared_files "
            "WHERE name=%s AND COALESCE(is_folder,0)=0 AND COALESCE(is_deleted,0)=0 "
            "ORDER BY id ASC LIMIT 1",
            ("test.xlsx",),
        )
        if existing:
            try:
                path = storage.resolve_storage_path(existing[0].get("storage_path") or "")
                if path.is_file():
                    return
            except Exception:
                pass
        rel = storage.build_storage_relpath("xlsx")
        abs_path = storage.resolve_storage_path(rel)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        wb = Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws["A1"] = "Collab Office Test"
        wb.save(str(abs_path))
        size = abs_path.stat().st_size
        now = _now()
        if existing:
            db.execute_update(
                "UPDATE shared_files SET storage_path=%s, size=%s, version=1, mime_type=%s, file_type=%s, "
                "updated_at=%s, last_saved_key='', last_saved_url='', is_deleted=0 WHERE id=%s",
                (rel, size, MIME_BY_EXT["xlsx"], "xlsx", now, existing[0]["id"]),
            )
            return
        db.execute_insert(
            "INSERT INTO shared_files "
            "(name, file_type, mime_type, parent_id, storage_path, size, owner_id, "
            " created_by, updated_by, version, is_folder, is_deleted, visibility_type, "
            " last_saved_key, last_saved_url, created_at, updated_at) "
            "VALUES (%s,%s,%s,NULL,%s,%s,%s,%s,%s,1,0,0,'all','','',%s,%s)",
            ("test.xlsx", "xlsx", MIME_BY_EXT["xlsx"], rel, size, "system", "system", "system", now, now),
        )
    except Exception as e:
        logger.error("init test.xlsx failed: %s", e)


_ensure_tables()
_ensure_phase2_test_file()


def _public_download_url(file_id: int, token: str) -> str:
    base = oo_sec.get_public_api_base()
    return f"{base}/api/shared-files/{int(file_id)}/download?token={quote(token, safe='')}"


def _public_callback_url(file_id: int) -> str:
    base = oo_sec.get_public_api_base()
    return f"{base}/api/onlyoffice/callback/{int(file_id)}"


def _editor_user_payload(user: Dict[str, Any]) -> Dict[str, str]:
    name = (user.get("name") or "").strip()
    gh = (user.get("gh") or "").strip()
    return {"id": gh or name, "name": name}


def _build_blank_bytes(ext: str) -> bytes:
    if ext == "xlsx":
        wb = Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
    if ext == "docx":
        from docx import Document
        doc = Document()
        doc.add_paragraph("")
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
    if ext == "pptx":
        from pptx import Presentation
        prs = Presentation()
        # blank layout
        try:
            layout = prs.slide_layouts[6]
        except Exception:
            layout = prs.slide_layouts[0]
        prs.slides.add_slide(layout)
        buf = io.BytesIO()
        prs.save(buf)
        return buf.getvalue()
    raise HTTPException(status_code=400, detail="不支持的文件类型")


class FolderCreateRequest(BaseModel):
    name: str
    parent_id: Optional[int] = None
    current_user: str
    visibility_type: str = "all"
    visibility_depts: List[str] = Field(default_factory=list)
    visibility_levels: List[str] = Field(default_factory=list)


class RenameRequest(BaseModel):
    name: str
    current_user: str


class VisibilityRequest(BaseModel):
    current_user: str
    visibility_type: str = "all"
    visibility_depts: List[str] = Field(default_factory=list)
    visibility_levels: List[str] = Field(default_factory=list)


class BlankCreateRequest(BaseModel):
    name: str
    file_type: str
    parent_id: Optional[int] = None
    current_user: str


def _normalize_visibility(vtype: str, depts: List[str], levels: List[str]) -> Tuple[str, str, str]:
    vt = (vtype or "all").strip().lower()
    if vt not in ("all", "restricted"):
        vt = "all"
    dept_list = [d.strip() for d in (depts or []) if d and str(d).strip()]
    level_list = [lv.strip() for lv in (levels or []) if lv and str(lv).strip()]
    allowed_keys = {x["key"] for x in LEVEL_OPTIONS}
    level_list = [lv for lv in level_list if lv in allowed_keys]
    if vt == "all":
        return "all", "[]", "[]"
    return "restricted", json.dumps(dept_list, ensure_ascii=False), json.dumps(level_list, ensure_ascii=False)


@router.get("/meta/options")
def get_options(current_user: str = Query(...)):
    require_module_access(current_user)
    depts = db.execute_query(
        "SELECT DISTINCT TRIM(lsys) AS lsys FROM yggl "
        "WHERE lsys IS NOT NULL AND TRIM(lsys) != '' "
        "AND TRIM(lsys) NOT IN (%s,%s) AND COALESCE(zaizhi,0)=0 "
        "ORDER BY lsys",
        (OTHER_DEPT_LSYS[0], OTHER_DEPT_LSYS[1]),
    )
    return {
        "success": True,
        "departments": [r["lsys"] for r in (depts or []) if r.get("lsys")],
        "levels": LEVEL_OPTIONS,
        "blank_types": [
            {"ext": "docx", "label": "Word (.docx)"},
            {"ext": "xlsx", "label": "Excel (.xlsx)"},
            {"ext": "pptx", "label": "PPT (.pptx)"},
        ],
    }


@router.get("")
@router.get("/")
def list_shared_files(current_user: str = Query(...), parent_id: Optional[int] = Query(None)):
    user = require_module_access(current_user)
    pid = _normalize_parent_id(parent_id)
    _assert_folder_visible(user, pid)
    if pid is not None:
        _assert_parent_folder(pid)
        rows = db.execute_query(
            "SELECT * FROM shared_files WHERE parent_id=%s AND COALESCE(is_deleted,0)=0 "
            "ORDER BY is_folder DESC, name ASC, id ASC",
            (pid,),
        )
    else:
        rows = db.execute_query(
            "SELECT * FROM shared_files WHERE parent_id IS NULL AND COALESCE(is_deleted,0)=0 "
            "ORDER BY is_folder DESC, name ASC, id ASC",
            (),
        )
    items = []
    for r in rows or []:
        if r.get("is_folder") and not user_can_see_folder(user, r):
            continue
        items.append(_serialize_item(r, user))
    name = (user.get("name") or "").strip()
    return {
        "success": True,
        "parent_id": pid,
        "breadcrumb": _breadcrumb(pid, user),
        "items": items,
        "permissions": {
            "is_admin": is_admin1(name),
            "can_create_folder": is_admin1(name),
            "can_upload": can_manage_files(user),
            "can_create_blank": can_manage_files(user),
            "can_delete_file": can_manage_files(user),
        },
    }


@router.post("/folders")
def create_folder(req: FolderCreateRequest):
    user = require_admin1(req.current_user)
    name = _clean_name(req.name)
    pid = _normalize_parent_id(req.parent_id)
    _assert_parent_folder(pid)
    if pid is not None:
        _assert_folder_visible(user, pid)
    if _name_exists(pid, name):
        raise HTTPException(status_code=400, detail="同目录下已存在同名项目")
    vt, vd, vl = _normalize_visibility(req.visibility_type, req.visibility_depts, req.visibility_levels)
    uname = (user.get("name") or "").strip()
    now = _now()
    new_id = db.execute_insert(
        "INSERT INTO shared_files "
        "(name, file_type, mime_type, parent_id, storage_path, size, owner_id, "
        " created_by, updated_by, version, is_folder, is_deleted, "
        " visibility_type, visibility_depts, visibility_levels, "
        " last_saved_key, last_saved_url, created_at, updated_at) "
        "VALUES (%s,'folder','',%s,'',0,%s,%s,%s,1,1,0,%s,%s,%s,'','',%s,%s)",
        (name, pid, uname, uname, uname, vt, vd, vl, now, now),
    )
    if not new_id:
        raise HTTPException(status_code=500, detail="create folder failed")
    logger.info("collab folder create id=%s user=%s", new_id, uname)
    return {"success": True, "message": "文件夹已创建", "data": _serialize_item(get_file_row(int(new_id)), user)}


@router.patch("/{file_id}/visibility")
def update_visibility(file_id: int, req: VisibilityRequest):
    user = require_admin1(req.current_user)
    row = get_file_row(file_id)
    if not row or not row.get("is_folder"):
        raise HTTPException(status_code=404, detail="文件不存在或已删除")
    vt, vd, vl = _normalize_visibility(req.visibility_type, req.visibility_depts, req.visibility_levels)
    now = _now()
    uname = (user.get("name") or "").strip()
    db.execute_update(
        "UPDATE shared_files SET visibility_type=%s, visibility_depts=%s, visibility_levels=%s, "
        "updated_by=%s, updated_at=%s WHERE id=%s",
        (vt, vd, vl, uname, now, file_id),
    )
    logger.info("collab visibility updated file_id=%s user=%s type=%s", file_id, uname, vt)
    return {"success": True, "message": "可见性已更新", "data": _serialize_item(get_file_row(file_id), user)}


@router.post("/upload")
async def upload_file(
    current_user: str = Form(...),
    parent_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
):
    user = require_file_manager(current_user)
    uname = (user.get("name") or "").strip()
    pid = _normalize_parent_id(parent_id)
    _assert_parent_folder(pid)
    _assert_folder_visible(user, pid)

    raw_name = os.path.basename((file.filename or "").replace("\\", "/").strip())
    if not raw_name:
        raise HTTPException(status_code=400, detail="名称不能为空")
    ext = Path(raw_name).suffix.lower().lstrip(".")
    if ext not in ALLOWED_UPLOAD_EXT:
        raise HTTPException(status_code=400, detail="仅支持 Word/Excel/PPT 文件")
    display_name = _clean_name(raw_name)
    if _name_exists(pid, display_name):
        raise HTTPException(status_code=400, detail="同目录下已存在同名项目")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if len(content) > _max_upload_bytes():
        raise HTTPException(status_code=400, detail="文件超过大小限制")

    rel = storage.build_storage_relpath(ext)
    abs_path = storage.resolve_storage_path(rel)
    size = storage.write_bytes_atomic(abs_path, content)
    now = _now()
    mime = MIME_BY_EXT.get(ext) or (file.content_type or "")
    new_id = db.execute_insert(
        "INSERT INTO shared_files "
        "(name, file_type, mime_type, parent_id, storage_path, size, owner_id, "
        " created_by, updated_by, version, is_folder, is_deleted, visibility_type, "
        " last_saved_key, last_saved_url, created_at, updated_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1,0,0,'all','','',%s,%s)",
        (display_name, ext, mime, pid, rel, size, uname, uname, uname, now, now),
    )
    if not new_id:
        try:
            abs_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="upload failed")
    logger.info("collab upload id=%s user=%s name=%s", new_id, uname, display_name)
    return {"success": True, "message": "上传成功", "data": _serialize_item(get_file_row(int(new_id)), user)}


@router.post("/create-blank")
def create_blank(req: BlankCreateRequest):
    user = require_file_manager(req.current_user)
    uname = (user.get("name") or "").strip()
    ext = (req.file_type or "").lower().lstrip(".")
    if ext not in BLANK_CREATE_EXT:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    name = _clean_name(req.name)
    if not name.lower().endswith("." + ext):
        name = f"{name}.{ext}"
    pid = _normalize_parent_id(req.parent_id)
    _assert_parent_folder(pid)
    _assert_folder_visible(user, pid)
    if _name_exists(pid, name):
        raise HTTPException(status_code=400, detail="同目录下已存在同名项目")

    content = _build_blank_bytes(ext)
    rel = storage.build_storage_relpath(ext)
    abs_path = storage.resolve_storage_path(rel)
    size = storage.write_bytes_atomic(abs_path, content)
    now = _now()
    new_id = db.execute_insert(
        "INSERT INTO shared_files "
        "(name, file_type, mime_type, parent_id, storage_path, size, owner_id, "
        " created_by, updated_by, version, is_folder, is_deleted, visibility_type, "
        " last_saved_key, last_saved_url, created_at, updated_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1,0,0,'all','','',%s,%s)",
        (name, ext, MIME_BY_EXT.get(ext, ""), pid, rel, size, uname, uname, uname, now, now),
    )
    if not new_id:
        raise HTTPException(status_code=500, detail="create blank failed")
    logger.info("collab blank create id=%s user=%s name=%s", new_id, uname, name)
    return {"success": True, "message": "已创建", "data": _serialize_item(get_file_row(int(new_id)), user)}


@router.get("/{file_id}")
def get_file_meta(file_id: int, current_user: str = Query(...)):
    user = require_module_access(current_user)
    row = get_file_row(file_id)
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在或已删除")
    parent_id = row.get("parent_id")
    _assert_folder_visible(user, int(parent_id) if parent_id else None)
    if row.get("is_folder") and not user_can_see_folder(user, row):
        raise HTTPException(status_code=403, detail="无权访问该文件夹")
    return {
        "success": True,
        "data": _serialize_item(row, user),
        "breadcrumb": _breadcrumb(file_id if row.get("is_folder") else row.get("parent_id"), user),
    }


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    request: Request,
    current_user: str = Query(""),
    token: str = Query(""),
):
    row = get_file_row(file_id)
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在或已删除")
    if row.get("is_folder"):
        raise HTTPException(status_code=400, detail="文件夹不可下载")

    token_clean = (token or "").strip()
    user_clean = (current_user or "").strip()
    if token_clean:
        try:
            oo_sec.verify_onlyoffice_download_token(token_clean, expected_file_id=file_id)
        except Exception:
            raise HTTPException(status_code=403, detail="下载凭证无效或已过期")
    elif user_clean:
        user = require_module_access(user_clean)
        parent_id = row.get("parent_id")
        _assert_folder_visible(user, int(parent_id) if parent_id else None)
    else:
        raise HTTPException(status_code=401, detail="缺少下载凭证")

    try:
        path = storage.resolve_storage_path(row.get("storage_path") or "")
    except ValueError:
        raise HTTPException(status_code=500, detail="文件路径无效")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="磁盘文件不存在")
    filename = (row.get("name") or path.name).strip() or path.name
    media = (row.get("mime_type") or "").strip() or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return FileResponse(path=str(path), media_type=media, filename=filename, content_disposition_type="attachment")


@router.patch("/{file_id}")
def rename_file(file_id: int, req: RenameRequest):
    user = require_module_access(req.current_user)
    uname = (user.get("name") or "").strip()
    row = get_file_row(file_id)
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在或已删除")
    flags = _perm_flags(user, row)
    if not flags["can_rename"]:
        raise HTTPException(status_code=403, detail="没有权限")
    new_name = _clean_name(req.name)
    if not row.get("is_folder"):
        old_ext = Path(row.get("name") or "").suffix
        if old_ext and not Path(new_name).suffix:
            new_name = new_name + old_ext
    parent_id = row.get("parent_id")
    pid = int(parent_id) if parent_id else None
    if _name_exists(pid, new_name, exclude_id=file_id):
        raise HTTPException(status_code=400, detail="同目录下已存在同名项目")
    now = _now()
    db.execute_update(
        "UPDATE shared_files SET name=%s, updated_by=%s, updated_at=%s WHERE id=%s AND COALESCE(is_deleted,0)=0",
        (new_name, uname, now, file_id),
    )
    return {"success": True, "message": "已重命名", "data": _serialize_item(get_file_row(file_id), user)}


@router.delete("/{file_id}")
def delete_file(file_id: int, current_user: str = Query(...)):
    user = require_module_access(current_user)
    uname = (user.get("name") or "").strip()
    row = get_file_row(file_id)
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在或已删除")
    if row.get("is_folder"):
        require_admin1(current_user)
    else:
        require_file_manager(current_user)

    now = _now()
    to_delete = [file_id]
    queue = [file_id]
    while queue:
        cur = queue.pop(0)
        kids = db.execute_query(
            "SELECT id FROM shared_files WHERE parent_id=%s AND COALESCE(is_deleted,0)=0",
            (cur,),
        )
        for k in kids or []:
            kid = int(k["id"])
            to_delete.append(kid)
            queue.append(kid)
    for fid in to_delete:
        db.execute_update(
            "UPDATE shared_files SET is_deleted=1, updated_by=%s, updated_at=%s WHERE id=%s",
            (uname, now, fid),
        )
    logger.info("collab soft-delete file_id=%s user=%s count=%s", file_id, uname, len(to_delete))
    return {"success": True, "message": "已删除", "deleted_count": len(to_delete)}


@router.get("/{file_id}/editor-config")
def get_editor_config(file_id: int, current_user: str = Query(...)):
    user = require_module_access(current_user)
    row = get_file_row(file_id)
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在或已删除")
    if row.get("is_folder"):
        raise HTTPException(status_code=400, detail="文件夹无法在线编辑")
    parent_id = row.get("parent_id")
    _assert_folder_visible(user, int(parent_id) if parent_id else None)

    ext = (row.get("file_type") or Path(row.get("name") or "").suffix.lstrip(".")).lower()
    if ext not in DOC_TYPE_BY_EXT:
        raise HTTPException(status_code=400, detail=f"{"不支持的文件类型"}: {ext}")
    try:
        path = storage.resolve_storage_path(row.get("storage_path") or "")
    except ValueError:
        raise HTTPException(status_code=500, detail="文件路径无效")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="磁盘文件不存在")

    try:
        document_server_url = oo_sec.get_onlyoffice_url()
        version = int(row.get("version") or 1)
        doc_key = oo_sec.build_document_key(file_id, version)
        download_token = oo_sec.issue_onlyoffice_download_token(
            file_id=file_id, version=version, document_key=doc_key
        )
        user_payload = _editor_user_payload(user)
        config = {
            "document": {
                "fileType": ext,
                "key": doc_key,
                "title": row.get("name") or f"file.{ext}",
                "url": _public_download_url(file_id, download_token),
                "permissions": {"edit": True, "download": True, "print": True, "review": True, "comment": True},
            },
            "documentType": DOC_TYPE_BY_EXT[ext],
            "editorConfig": {
                "callbackUrl": _public_callback_url(file_id),
                "mode": "edit",
                "lang": "zh-CN",
                "user": user_payload,
                "customization": {"forcesave": True, "autosave": True},
            },
        }
        config["token"] = oo_sec.sign_editor_config(config)
    except oo_sec.OnlyOfficeConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("editor-config failed file_id=%s", file_id)
        raise HTTPException(status_code=500, detail=f"{"生成编辑配置失败"}: {e}")

    logger.info("open editor file_id=%s user=%s key=%s v=%s", file_id, current_user, doc_key, version)
    return {
        "success": True,
        "documentServerUrl": document_server_url,
        "config": config,
        "file": {"id": file_id, "name": row.get("name"), "version": version, "document_key": doc_key},
    }
