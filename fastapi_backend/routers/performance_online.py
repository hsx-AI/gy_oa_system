# -*- coding: utf-8 -*-
"""Online performance filling for the pilot department."""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

import jwt
from fastapi import APIRouter, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database import db
from routers.approvers import _get_user_info, _jb_match, is_admin1_user
from services import onlyoffice_security as oo_sec
from services import performance_workbook as books
from services import shared_file_storage as storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/performance/online", tags=["performance-online"])

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ONLINE_ROOT = BACKEND_ROOT / "data" / "performance_online"
SEED_TEMPLATE = ONLINE_ROOT / "seed" / f"{books.PILOT_DEPARTMENT}.xlsx"
_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_PURPOSE = "performance_download"


class OpenRequest(BaseModel):
    current_user: str
    month: str
    scope: str = Field(..., description="mine ?? summary")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_part(text: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\r\n]+', "_", (text or "").strip()).strip(" .")
    return (cleaned or "unknown")[:80]


def _ensure_tables() -> None:
    db.execute_update(
        """
        CREATE TABLE IF NOT EXISTS perf_online_template (
            id INT AUTO_INCREMENT PRIMARY KEY,
            department VARCHAR(100) NOT NULL,
            storage_relpath VARCHAR(500) NOT NULL,
            sha256 CHAR(64) NOT NULL,
            original_name VARCHAR(255) NOT NULL DEFAULT '',
            updated_by VARCHAR(100) NOT NULL DEFAULT '',
            updated_at DATETIME NULL,
            UNIQUE KEY uk_perf_tpl_dept (department)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    db.execute_update(
        """
        CREATE TABLE IF NOT EXISTS perf_online_doc (
            id INT AUTO_INCREMENT PRIMARY KEY,
            department VARCHAR(100) NOT NULL,
            perf_month CHAR(7) NOT NULL,
            scope VARCHAR(16) NOT NULL,
            owner_name VARCHAR(100) NOT NULL,
            storage_relpath VARCHAR(500) NOT NULL,
            version INT NOT NULL DEFAULT 1,
            template_sha CHAR(64) NOT NULL DEFAULT '',
            last_saved_key VARCHAR(160) NOT NULL DEFAULT '',
            last_saved_url VARCHAR(1000) NOT NULL DEFAULT '',
            updated_at DATETIME NULL,
            UNIQUE KEY uk_perf_doc (department, perf_month, scope, owner_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def _resolve(rel: str) -> Path:
    root = ONLINE_ROOT.resolve()
    full = (root / (rel or "").replace("\\", "/").lstrip("/")).resolve()
    try:
        full.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="invalid performance file path") from exc
    return full


def _template_rel() -> str:
    return f"templates/{_safe_part(books.PILOT_DEPARTMENT)}.xlsx"


def _doc_rel(month: str, owner: str, scope: str) -> str:
    return f"docs/{_safe_part(books.PILOT_DEPARTMENT)}/{month}/{_safe_part(owner)}_{scope}.xlsx"


def _user(name: str) -> Dict[str, Any]:
    user = _get_user_info((name or "").strip())
    if not user and not is_admin1_user(name):
        raise HTTPException(status_code=401, detail="user was not found")
    return user or {"name": (name or "").strip(), "jb": "", "lsys": "", "gh": name}


def _is_leader(job: str) -> bool:
    return any(_jb_match(job, role) for role in ("主任", "副主任", "组长"))


def _is_director(job: str) -> bool:
    return _jb_match(job, "主任") and not _jb_match(job, "副主任")


def _access(name: str) -> Dict[str, Any]:
    clean = (name or "").strip()
    admin = is_admin1_user(clean)
    user = _user(clean)
    job = (user.get("jb") or "").strip()
    dept = (user.get("lsys") or "").strip()
    in_pilot = dept == books.PILOT_DEPARTMENT
    return {
        "name": (user.get("name") or clean).strip(),
        "job": job,
        "department": dept,
        "in_pilot": in_pilot or admin,
        "can_fill": in_pilot,
        "can_summary": in_pilot and (_is_leader(job) or admin),
        "can_update_template": admin or (in_pilot and _is_director(job)),
        "is_admin": admin,
    }


def _month(value: str) -> str:
    text = (value or "").strip()
    if not _MONTH.match(text):
        raise HTTPException(status_code=422, detail="month must be YYYY-MM")
    return text


def _roster() -> list:
    rows = db.execute_query(
        """
        SELECT TRIM(name) AS name
        FROM yggl
        WHERE TRIM(lsys)=%s AND name IS NOT NULL AND TRIM(name) != ''
          AND RIGHT(TRIM(name), 1) != '1' AND COALESCE(zaizhi, 0)=0
        ORDER BY name
        """,
        (books.PILOT_DEPARTMENT,),
    )
    names = []
    for row in rows or []:
        name = (row.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def _template_row() -> Optional[dict]:
    rows = db.execute_query(
        "SELECT * FROM perf_online_template WHERE department=%s LIMIT 1",
        (books.PILOT_DEPARTMENT,),
    )
    return rows[0] if rows else None


def ensure_template() -> Dict[str, Any]:
    _ensure_tables()
    row = _template_row()
    rel = _template_rel()
    path = _resolve(rel)
    if row and path.is_file():
        return row
    if not SEED_TEMPLATE.is_file():
        raise HTTPException(status_code=500, detail="performance template seed is missing")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_bytes(SEED_TEMPLATE.read_bytes())
    digest = books.sha256_file(path)
    now = _now()
    if row:
        db.execute_update(
            "UPDATE perf_online_template SET storage_relpath=%s, sha256=%s, original_name=%s, updated_at=%s WHERE department=%s",
            (rel, digest, SEED_TEMPLATE.name, now, books.PILOT_DEPARTMENT),
        )
    else:
        db.execute_insert(
            """INSERT INTO perf_online_template
               (department, storage_relpath, sha256, original_name, updated_by, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (books.PILOT_DEPARTMENT, rel, digest, SEED_TEMPLATE.name, "system", now),
        )
    row = _template_row()
    if not row:
        raise HTTPException(status_code=500, detail="failed to initialize the performance template")
    return row


def _doc_row(month: str, owner: str, scope: str) -> Optional[dict]:
    rows = db.execute_query(
        """SELECT * FROM perf_online_doc
           WHERE department=%s AND perf_month=%s AND scope=%s AND owner_name=%s LIMIT 1""",
        (books.PILOT_DEPARTMENT, month, scope, owner),
    )
    return rows[0] if rows else None


def _doc_by_id(doc_id: int) -> Optional[dict]:
    rows = db.execute_query("SELECT * FROM perf_online_doc WHERE id=%s LIMIT 1", (doc_id,))
    return rows[0] if rows else None


def _touch_doc(doc_id: int, version: int, template_sha: str) -> None:
    db.execute_update(
        "UPDATE perf_online_doc SET version=%s, template_sha=%s, updated_at=%s WHERE id=%s",
        (version, template_sha, _now(), doc_id),
    )


def _ensure_doc(month: str, owner: str, scope: str, rel: str, template_sha: str) -> dict:
    row = _doc_row(month, owner, scope)
    if row:
        return row
    db.execute_insert(
        """INSERT INTO perf_online_doc
           (department, perf_month, scope, owner_name, storage_relpath, version, template_sha, updated_at)
           VALUES (%s,%s,%s,%s,%s,1,%s,%s)""",
        (books.PILOT_DEPARTMENT, month, scope, owner, rel, template_sha, _now()),
    )
    row = _doc_row(month, owner, scope)
    if not row:
        raise HTTPException(status_code=500, detail="failed to create the performance document")
    return row


def _personal_paths(month: str) -> Dict[str, Path]:
    rows = db.execute_query(
        """SELECT owner_name, storage_relpath FROM perf_online_doc
           WHERE department=%s AND perf_month=%s AND scope='personal'""",
        (books.PILOT_DEPARTMENT, month),
    )
    paths: Dict[str, Path] = {}
    for row in rows or []:
        path = _resolve(row.get("storage_relpath") or "")
        if path.is_file():
            paths[(row.get("owner_name") or "").strip()] = path
    return paths


def _prepare_personal(month: str, owner: str, template: dict) -> dict:
    rel = _doc_rel(month, owner, "personal")
    path = _resolve(rel)
    digest = template.get("sha256") or ""
    row = _ensure_doc(month, owner, "personal", rel, digest)
    template_path = _resolve(template.get("storage_relpath") or "")
    existed = path.is_file()
    sha_match = (row.get("template_sha") or "") == digest
    if existed and sha_match:
        return row
    books.build_personal_workbook(
        template_path=template_path,
        dest_path=path,
        employee=owner,
        previous_path=path if existed else None,
    )
    version = int(row.get("version") or 1)
    if existed and not sha_match:
        version += 1
    _touch_doc(int(row["id"]), version, digest)
    return _doc_by_id(int(row["id"])) or row


def _prepare_summary(month: str, owner: str, template: dict) -> dict:
    rel = _doc_rel(month, owner, "summary")
    digest = template.get("sha256") or ""
    row = _ensure_doc(month, owner, "summary", rel, digest)
    template_path = _resolve(template.get("storage_relpath") or "")
    names = _roster()
    if owner not in names:
        names.append(owner)
    books.build_summary_workbook(
        template_path=template_path,
        dest_path=_resolve(rel),
        owner=owner,
        roster=names,
        personal_paths=_personal_paths(month),
    )
    version = int(row.get("version") or 1) + 1
    _touch_doc(int(row["id"]), version, digest)
    return _doc_by_id(int(row["id"])) or row


def _document_key(doc_id: int, version: int) -> str:
    return f"perf{int(doc_id)}-v{int(version)}"


def _issue_token(doc_id: int, version: int, document_key: str) -> str:
    secret = oo_sec.get_signing_secret()
    now = int(time.time())
    ttl = int(getattr(oo_sec.settings, "SHARED_FILES_DOWNLOAD_TOKEN_TTL_SECONDS", 900) or 900)
    payload = {
        "file_id": int(doc_id),
        "purpose": _PURPOSE,
        "version": int(version),
        "key": document_key,
        "iat": now,
        "exp": now + max(ttl, 300),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def _public_download(doc_id: int, token: str) -> str:
    return f"{oo_sec.get_public_api_base()}/api/performance/online/docs/{int(doc_id)}/download?token={quote(token, safe='')}"


def _public_callback(doc_id: int) -> str:
    return f"{oo_sec.get_public_api_base()}/api/performance/online/callback/{int(doc_id)}"


@router.get("/context")
def context(current_user: str = Query(...), month: str = Query("")):
    access = _access(current_user)
    chosen = _month(month) if month else datetime.now().strftime("%Y-%m")
    template = None
    try:
        template = ensure_template()
    except HTTPException:
        if access["in_pilot"]:
            raise
    people = []
    mine_filled = False
    if access["can_summary"]:
        paths = _personal_paths(chosen) if template else {}
        names = _roster()
        for name in names:
            path = paths.get(name)
            people.append({
                "name": name,
                "filled": bool(path and books.personal_fill_state(path, name)),
                "updated_at": None,
            })
    elif access["can_fill"] and template:
        row = _doc_row(chosen, access["name"], "personal")
        if row:
            path = _resolve(row.get("storage_relpath") or "")
            mine_filled = path.is_file() and books.personal_fill_state(path, access["name"])
    return {
        "success": True,
        "pilot_department": books.PILOT_DEPARTMENT,
        "month": chosen,
        "access": access,
        "template_updated_at": (template or {}).get("updated_at"),
        "template_name": (template or {}).get("original_name") or "",
        "mine_filled": mine_filled,
        "people": people,
    }


@router.post("/template")
async def upload_template(current_user: str = Query(...), file: UploadFile = File(...)):
    access = _access(current_user)
    if not access["can_update_template"]:
        raise HTTPException(status_code=403, detail="only the department director can update the template")
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="please upload an xlsx template")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="template file is empty")
    ensure_template()
    rel = _template_rel()
    path = _resolve(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".upload.xlsx")
    tmp.write_bytes(content)
    try:
        books.validate_template(tmp)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="template does not match the required layout: " + str(exc)) from exc
    tmp.replace(path)
    digest = books.sha256_file(path)
    db.execute_update(
        """UPDATE perf_online_template
           SET sha256=%s, original_name=%s, updated_by=%s, updated_at=%s
           WHERE department=%s""",
        (digest, Path(filename).name, access["name"], _now(), books.PILOT_DEPARTMENT),
    )
    return {"success": True, "message": "template updated; workbooks refresh the next time they are opened"}


@router.post("/open")
def open_doc(body: OpenRequest):
    access = _access(body.current_user)
    month = _month(body.month)
    scope = (body.scope or "").strip()
    if scope not in ("mine", "summary"):
        raise HTTPException(status_code=422, detail="scope must be mine or summary")
    if not access["can_fill"] and not (scope == "summary" and access["is_admin"]):
        raise HTTPException(status_code=403, detail="online performance filling is only open for " + books.PILOT_DEPARTMENT)
    if scope == "summary" and not access["can_summary"]:
        raise HTTPException(status_code=403, detail="only the director, deputy director, and team leader can open the summary")
    if scope == "mine" and not access["can_fill"]:
        raise HTTPException(status_code=403, detail="this account is not in the pilot department")
    template = ensure_template()
    owner = access["name"]
    try:
        if scope == "mine":
            row = _prepare_personal(month, owner, template)
            title = f"{month} {owner} 绩效填报"
        else:
            row = _prepare_summary(month, owner, template)
            title = f"{month} {books.PILOT_DEPARTMENT} 绩效汇总"
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("prepare performance workbook failed")
        raise HTTPException(status_code=500, detail="failed to build the performance workbook: " + str(exc)) from exc
    return {"success": True, "doc_id": int(row["id"]), "title": title, "scope": "personal" if scope == "mine" else "summary"}


@router.get("/docs/{doc_id}/editor-config")
def editor_config(doc_id: int, current_user: str = Query(...)):
    access = _access(current_user)
    row = _doc_by_id(doc_id)
    if not row:
        raise HTTPException(status_code=404, detail="performance document was not found")
    if (row.get("owner_name") or "") != access["name"] and not access["is_admin"]:
        raise HTTPException(status_code=403, detail="you cannot open someone else's performance document")
    path = _resolve(row.get("storage_relpath") or "")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="performance file has not been generated")
    version = int(row.get("version") or 1)
    doc_key = _document_key(doc_id, version)
    title = path.name
    if row.get("scope") == "personal":
        title = f"{row.get('perf_month')} {row.get('owner_name')} 绩效填报.xlsx"
    else:
        title = f"{row.get('perf_month')} {books.PILOT_DEPARTMENT} 绩效汇总.xlsx"
    try:
        token = _issue_token(doc_id, version, doc_key)
        user = _user(access["name"])
        config = {
            "document": {
                "fileType": "xlsx",
                "key": doc_key,
                "title": title,
                "url": _public_download(doc_id, token),
                "permissions": {"edit": True, "download": True, "print": True, "review": False, "comment": False},
            },
            "documentType": "cell",
            "editorConfig": {
                "callbackUrl": _public_callback(doc_id),
                "mode": "edit",
                "lang": "zh-CN",
                "user": {"id": (user.get("gh") or access["name"]), "name": access["name"]},
                "customization": {"forcesave": True, "autosave": True},
            },
        }
        config["token"] = oo_sec.sign_editor_config(config)
    except oo_sec.OnlyOfficeConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "success": True,
        "documentServerUrl": oo_sec.get_onlyoffice_url(),
        "config": config,
        "file": {
            "id": doc_id,
            "name": title,
            "version": version,
            "document_key": doc_key,
            "scope": row.get("scope"),
        },
    }


@router.get("/docs/{doc_id}/download")
def download_doc(doc_id: int, token: str = Query("")):
    row = _doc_by_id(doc_id)
    if not row:
        raise HTTPException(status_code=404, detail="performance document was not found")
    try:
        payload = jwt.decode(token, oo_sec.get_signing_secret(), algorithms=["HS256"])
    except Exception as exc:
        raise HTTPException(status_code=403, detail="download token is invalid or expired") from exc
    if payload.get("purpose") != _PURPOSE or int(payload.get("file_id") or 0) != int(doc_id):
        raise HTTPException(status_code=403, detail="download token is invalid")
    path = _resolve(row.get("storage_relpath") or "")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="file was not found")
    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )


def _callback_token(request: Request, body: dict, authorization: Optional[str]) -> str:
    if authorization:
        parts = authorization.strip().split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        if authorization.count(".") == 2:
            return authorization.strip()
    token = body.get("token")
    return token.strip() if isinstance(token, str) else ""


@router.post("/callback/{doc_id}")
async def onlyoffice_callback(
    doc_id: int,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    try:
        body = await request.json()
    except Exception:
        return {"error": 1}
    if not isinstance(body, dict):
        return {"error": 1}
    try:
        token = _callback_token(request, body, authorization)
        if not token:
            return {"error": 1}
        payload = oo_sec.verify_onlyoffice_callback_token(token)
        if isinstance(payload, dict):
            for key in ("status", "url", "key"):
                if key in payload and key not in body:
                    body[key] = payload[key]
            inner = payload.get("payload")
            if isinstance(inner, dict):
                for key, val in inner.items():
                    body.setdefault(key, val)
    except Exception:
        logger.warning("performance callback jwt invalid doc_id=%s", doc_id)
        return {"error": 1}

    try:
        status = int(body.get("status"))
    except (TypeError, ValueError):
        return {"error": 1}
    if status in (1, 4):
        return {"error": 0}
    if status in (3, 7):
        logger.error("performance callback error status=%s doc_id=%s", status, doc_id)
        return {"error": 0}
    if status not in (2, 6):
        return {"error": 0}

    row = _doc_by_id(doc_id)
    if not row:
        return {"error": 1}
    url = (body.get("url") or "").strip()
    callback_key = str(body.get("key") or "")
    version = int(row.get("version") or 1)
    expected = _document_key(doc_id, version)
    if callback_key and callback_key != expected:
        logger.info("performance callback key mismatch doc_id=%s got=%s expected=%s", doc_id, callback_key, expected)
        return {"error": 0}
    if status == 2 and callback_key and callback_key == (row.get("last_saved_key") or ""):
        return {"error": 0}
    if not url:
        return {"error": 1}
    try:
        headers = oo_sec.make_download_from_ds_auth_header(url)
        tmp_path, size = storage.download_to_temp_file(url=url, headers=headers)
        dest = _resolve(row.get("storage_relpath") or "")
        storage.atomic_replace(tmp_path, dest)
        if row.get("scope") == "summary":
            template = ensure_template()
            personal_rel = _doc_rel(row.get("perf_month"), row.get("owner_name"), "personal")
            personal = _ensure_doc(row.get("perf_month"), row.get("owner_name"), "personal", personal_rel, template.get("sha256") or "")
            books.sync_owner_personal_from_summary(
                summary_path=dest,
                template_path=_resolve(template.get("storage_relpath") or ""),
                personal_path=_resolve(personal.get("storage_relpath") or personal_rel),
                owner=row.get("owner_name") or "",
            )
            personal_version = int(personal.get("version") or 1) + 1
            _touch_doc(int(personal["id"]), personal_version, template.get("sha256") or "")
        new_version = version + 1 if status == 2 else version
        db.execute_update(
            """UPDATE perf_online_doc
               SET version=%s, last_saved_key=%s, last_saved_url=%s, updated_at=%s
               WHERE id=%s AND version=%s""",
            (new_version, callback_key, url[:1000], _now(), doc_id, version),
        )
        logger.info("performance callback saved doc_id=%s scope=%s size=%s", doc_id, row.get("scope"), size)
        return {"error": 0}
    except Exception:
        logger.exception("performance callback save failed doc_id=%s", doc_id)
        return {"error": 1}
