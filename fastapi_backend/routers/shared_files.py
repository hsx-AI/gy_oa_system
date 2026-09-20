# -*- coding: utf-8 -*-
"""Shared documents Phase2: meta, signed download, editor-config."""
from __future__ import annotations

import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from openpyxl import Workbook

from database import db
from services import onlyoffice_security as oo_sec
from services import shared_file_storage as storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shared-files", tags=["shared-files"])

OTHER_DEPT_LSYS = ("其他部门员工", "其他部门成员")

MIME_BY_EXT = {
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

DOC_TYPE_BY_EXT = {
    "doc": "word",
    "docx": "word",
    "xls": "cell",
    "xlsx": "cell",
    "ppt": "slide",
    "pptx": "slide",
}

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
  last_saved_key VARCHAR(100) NOT NULL DEFAULT '',
  last_saved_url VARCHAR(2000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_parent_deleted (parent_id, is_deleted),
  KEY idx_owner (owner_id),
  KEY idx_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='shared documents'
"""


def _ensure_tables() -> None:
    try:
        db.execute_update(DDL, ())
    except Exception as e:
        logger.error("create shared_files failed: %s", e)


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


def can_access_shared_docs(name: str) -> Tuple[bool, str]:
    user = _get_user_row(name)
    if not user:
        return False, "用户不存在或已离职"
    if is_admin1(name):
        return True, ""
    lsys = (user.get("lsys") or "").strip()
    if lsys in OTHER_DEPT_LSYS:
        return False, "外部门用户暂不可访问共享文档"
    if not lsys:
        return False, "未分配科室，无法访问共享文档"
    return True, ""


def require_module_access(name: str) -> Dict[str, Any]:
    ok, msg = can_access_shared_docs(name)
    if not ok:
        logger.warning("shared-docs denied user=%s reason=%s", name, msg)
        raise HTTPException(status_code=403, detail=msg or "没有权限")
    user = _get_user_row(name)
    assert user is not None
    return user


def get_file_row(file_id: int, *, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
    if include_deleted:
        rows = db.execute_query("SELECT * FROM shared_files WHERE id=%s LIMIT 1", (file_id,))
    else:
        rows = db.execute_query(
            "SELECT * FROM shared_files WHERE id=%s AND COALESCE(is_deleted,0)=0 LIMIT 1",
            (file_id,),
        )
    return rows[0] if rows else None


def _ensure_phase2_test_file() -> None:
    try:
        existing = db.execute_query(
            "SELECT id, storage_path FROM shared_files "
            "WHERE name=%s AND COALESCE(is_folder,0)=0 AND COALESCE(is_deleted,0)=0 "
            "ORDER BY id ASC LIMIT 1",
            ("test.xlsx",),
        )
        if existing:
            row = existing[0]
            try:
                path = storage.resolve_storage_path(row.get("storage_path") or "")
                if path.is_file():
                    return
                logger.warning("test.xlsx meta exists but disk missing, rebuild id=%s", row.get("id"))
            except Exception:
                logger.warning("test.xlsx storage_path invalid, rebuild id=%s", row.get("id"))

        rel = storage.build_storage_relpath("xlsx")
        abs_path = storage.resolve_storage_path(rel)
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        wb = Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws["A1"] = "ONLYOFFICE Phase2 Test"
        ws["B1"] = "Edit this cell, close editor, reopen to verify save"
        ws["A2"] = "Phase2 closed loop"
        wb.save(str(abs_path))
        size = abs_path.stat().st_size
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if existing:
            db.execute_update(
                "UPDATE shared_files SET storage_path=%s, size=%s, version=1, "
                "mime_type=%s, file_type=%s, updated_at=%s, last_saved_key='', last_saved_url='', "
                "is_deleted=0 WHERE id=%s",
                (rel, size, MIME_BY_EXT["xlsx"], "xlsx", now, existing[0]["id"]),
            )
            logger.info("rebuilt Phase2 test.xlsx id=%s path=%s", existing[0]["id"], rel)
            return

        new_id = db.execute_insert(
            "INSERT INTO shared_files "
            "(name, file_type, mime_type, parent_id, storage_path, size, owner_id, "
            " created_by, updated_by, version, is_folder, is_deleted, "
            " last_saved_key, last_saved_url, created_at, updated_at) "
            "VALUES (%s,%s,%s,NULL,%s,%s,%s,%s,%s,1,0,0,'','',%s,%s)",
            (
                "test.xlsx",
                "xlsx",
                MIME_BY_EXT["xlsx"],
                rel,
                size,
                "system",
                "system",
                "system",
                now,
                now,
            ),
        )
        logger.info("created Phase2 test.xlsx id=%s path=%s", new_id, rel)
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


@router.get("/phase2-test-info")
def phase2_test_info(current_user: str = Query(..., description="current user name")):
    require_module_access(current_user)
    rows = db.execute_query(
        "SELECT id, name, version, size, updated_at, storage_path FROM shared_files "
        "WHERE name=%s AND COALESCE(is_deleted,0)=0 ORDER BY id ASC LIMIT 1",
        ("test.xlsx",),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="test.xlsx not found")
    r = rows[0]
    return {
        "success": True,
        "data": {
            "id": r["id"],
            "name": r.get("name"),
            "version": r.get("version"),
            "size": r.get("size"),
            "updated_at": str(r.get("updated_at") or ""),
            "edit_path": f"/shared-files/edit/{r['id']}",
        },
    }


@router.get("/{file_id}")
def get_file_meta(file_id: int, current_user: str = Query(...)):
    require_module_access(current_user)
    row = get_file_row(file_id)
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在或已删除")
    return {
        "success": True,
        "data": {
            "id": row["id"],
            "name": row.get("name"),
            "file_type": row.get("file_type"),
            "mime_type": row.get("mime_type"),
            "size": row.get("size"),
            "version": row.get("version"),
            "is_folder": bool(row.get("is_folder")),
            "created_by": row.get("created_by"),
            "updated_by": row.get("updated_by"),
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
            "document_key": oo_sec.build_document_key(row["id"], int(row.get("version") or 1)),
        },
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
        logger.warning("download missing file_id=%s", file_id)
        raise HTTPException(status_code=404, detail="文件不存在或已删除")
    if row.get("is_folder"):
        raise HTTPException(status_code=400, detail="文件夹不可下载")

    token_clean = (token or "").strip()
    user_clean = (current_user or "").strip()

    if token_clean:
        try:
            oo_sec.verify_onlyoffice_download_token(token_clean, expected_file_id=file_id)
        except Exception:
            logger.warning("onlyoffice download token rejected file_id=%s", file_id)
            raise HTTPException(status_code=403, detail="下载凭证无效或已过期")
        logger.info("shared download(onlyoffice) file_id=%s ok", file_id)
    elif user_clean:
        require_module_access(user_clean)
        logger.info("shared download(browser) file_id=%s user=%s ok", file_id, user_clean)
    else:
        raise HTTPException(status_code=401, detail="缺少下载凭证")

    try:
        path = storage.resolve_storage_path(row.get("storage_path") or "")
    except ValueError:
        raise HTTPException(status_code=500, detail="文件路径无效")
    if not path.is_file():
        logger.error("disk missing file_id=%s path=%s", file_id, path)
        raise HTTPException(status_code=404, detail="磁盘文件不存在")

    filename = (row.get("name") or path.name).strip() or path.name
    media = (row.get("mime_type") or "").strip() or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return FileResponse(
        path=str(path),
        media_type=media,
        filename=filename,
        content_disposition_type="attachment",
    )


@router.get("/{file_id}/editor-config")
def get_editor_config(file_id: int, current_user: str = Query(...)):
    user = require_module_access(current_user)
    row = get_file_row(file_id)
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在或已删除")
    if row.get("is_folder"):
        raise HTTPException(status_code=400, detail="文件夹无法在线编辑")

    ext = (row.get("file_type") or Path(row.get("name") or "").suffix.lstrip(".")).lower()
    if ext not in DOC_TYPE_BY_EXT:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

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
            file_id=file_id,
            version=version,
            document_key=doc_key,
        )
        config = {
            "document": {
                "fileType": ext,
                "key": doc_key,
                "title": row.get("name") or f"file.{ext}",
                "url": _public_download_url(file_id, download_token),
                "permissions": {
                    "edit": True,
                    "download": True,
                    "print": True,
                    "review": True,
                },
            },
            "documentType": DOC_TYPE_BY_EXT[ext],
            "editorConfig": {
                "callbackUrl": _public_callback_url(file_id),
                "mode": "edit",
                "lang": "zh-CN",
                "user": _editor_user_payload(user),
                "customization": {
                    "forcesave": True,
                    "autosave": True,
                },
            },
        }
        config["token"] = oo_sec.sign_editor_config(config)
    except oo_sec.OnlyOfficeConfigError as e:
        logger.error("editor-config config error file_id=%s: %s", file_id, e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("editor-config failed file_id=%s", file_id)
        raise HTTPException(status_code=500, detail=f"生成编辑配置失败: {e}")

    logger.info(
        "open editor file_id=%s user=%s key=%s version=%s",
        file_id,
        current_user,
        config["document"]["key"],
        version,
    )
    return {
        "success": True,
        "documentServerUrl": document_server_url,
        "config": config,
        "file": {
            "id": file_id,
            "name": row.get("name"),
            "version": version,
            "document_key": doc_key,
        },
    }
