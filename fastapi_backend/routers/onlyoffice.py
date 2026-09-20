# -*- coding: utf-8 -*-
"""ONLYOFFICE Document Server callback handler."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, Request

from database import db
from routers.shared_files import get_file_row
from services import onlyoffice_security as oo_sec
from services import shared_file_storage as storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onlyoffice", tags=["onlyoffice"])


def _extract_callback_token(request: Request, body: Dict[str, Any], authorization: Optional[str]) -> Optional[str]:
    if authorization:
        parts = authorization.strip().split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        if authorization.count(".") == 2:
            return authorization.strip()
    tok = body.get("token")
    if isinstance(tok, str) and tok.strip():
        return tok.strip()
    return None


def _resolve_updater(body: Dict[str, Any]) -> str:
    users = body.get("users") or []
    if isinstance(users, list) and users:
        first = users[0]
        if isinstance(first, str) and first.strip():
            return first.strip()[:100]
        if isinstance(first, dict):
            return str(first.get("id") or first.get("name") or "onlyoffice")[:100]
    actions = body.get("actions") or []
    if isinstance(actions, list) and actions:
        act = actions[0]
        if isinstance(act, dict) and act.get("userid"):
            return str(act.get("userid"))[:100]
    return "onlyoffice"


async def _save_from_callback(
    *,
    file_id: int,
    row: Dict[str, Any],
    body: Dict[str, Any],
    bump_version: bool,
) -> None:
    url = (body.get("url") or "").strip()
    if not url:
        raise RuntimeError("callback missing url")

    callback_key = str(body.get("key") or "")
    current_version = int(row.get("version") or 1)
    expected_key = oo_sec.build_document_key(file_id, current_version)
    last_saved_key = (row.get("last_saved_key") or "").strip()
    last_saved_url = (row.get("last_saved_url") or "").strip()

    if bump_version:
        if callback_key and callback_key == last_saved_key:
            logger.info("callback idempotent skip (key finalized) file_id=%s key=%s", file_id, callback_key)
            return
        if callback_key != expected_key:
            logger.info(
                "callback skip key mismatch file_id=%s callback_key=%s expected=%s version=%s",
                file_id,
                callback_key,
                expected_key,
                current_version,
            )
            return
    else:
        if url and url == last_saved_url:
            logger.info("callback idempotent skip (same forcesave url) file_id=%s key=%s", file_id, callback_key)
            return
        if callback_key and callback_key != expected_key:
            logger.info(
                "forcesave key mismatch skip file_id=%s callback_key=%s expected=%s",
                file_id,
                callback_key,
                expected_key,
            )
            return

    headers = oo_sec.make_download_from_ds_auth_header(url)
    tmp_path, size = storage.download_to_temp_file(url=url, headers=headers)

    try:
        dest = storage.resolve_storage_path(row.get("storage_path") or "")
        storage.atomic_replace(tmp_path, dest)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updater = _resolve_updater(body)
    new_version = current_version + 1 if bump_version else current_version

    if bump_version:
        affected = db.execute_update(
            "UPDATE shared_files SET size=%s, updated_at=%s, updated_by=%s, version=%s, "
            "last_saved_key=%s, last_saved_url=%s "
            "WHERE id=%s AND version=%s AND COALESCE(is_deleted,0)=0",
            (size, now, updater, new_version, callback_key, url, file_id, current_version),
        )
    else:
        affected = db.execute_update(
            "UPDATE shared_files SET size=%s, updated_at=%s, updated_by=%s, last_saved_url=%s "
            "WHERE id=%s AND version=%s AND COALESCE(is_deleted,0)=0",
            (size, now, updater, url, file_id, current_version),
        )

    if affected is not None and affected < 0:
        raise RuntimeError("db update failed")
    if affected == 0:
        logger.warning(
            "callback db affected 0 rows file_id=%s version=%s bump=%s",
            file_id,
            current_version,
            bump_version,
        )
        return

    logger.info(
        "callback save ok file_id=%s key=%s size=%s version=%s->%s bump=%s updater=%s",
        file_id,
        callback_key,
        size,
        current_version,
        new_version,
        bump_version,
        updater,
    )


@router.post("/callback/{file_id}")
async def onlyoffice_callback(
    file_id: int,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    try:
        body = await request.json()
    except Exception:
        logger.error("callback body not json file_id=%s", file_id)
        return {"error": 1}

    if not isinstance(body, dict):
        return {"error": 1}

    try:
        oo_sec.get_onlyoffice_jwt_secret()
        jwt_required = True
    except oo_sec.OnlyOfficeConfigError:
        jwt_required = False

    if jwt_required:
        token = _extract_callback_token(request, body, authorization)
        if not token:
            logger.warning("callback missing JWT file_id=%s", file_id)
            return {"error": 1}
        try:
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
            logger.warning("callback JWT invalid file_id=%s", file_id)
            return {"error": 1}

    try:
        status = int(body.get("status"))
    except (TypeError, ValueError):
        logger.warning("callback invalid status file_id=%s keys=%s", file_id, list(body.keys()))
        return {"error": 1}

    logger.info(
        "ONLYOFFICE callback file_id=%s status=%s key=%s has_url=%s",
        file_id,
        status,
        body.get("key"),
        bool(body.get("url")),
    )

    row = get_file_row(file_id)
    if not row:
        logger.error("callback file missing file_id=%s", file_id)
        return {"error": 1}

    try:
        if status in (1, 4):
            return {"error": 0}

        if status in (3, 7):
            logger.error("callback save error status file_id=%s status=%s key=%s", file_id, status, body.get("key"))
            return {"error": 0}

        if status == 2:
            await _save_from_callback(file_id=file_id, row=row, body=body, bump_version=True)
            return {"error": 0}

        if status == 6:
            await _save_from_callback(file_id=file_id, row=row, body=body, bump_version=False)
            return {"error": 0}

        logger.info("callback ignore status=%s file_id=%s", status, file_id)
        return {"error": 0}
    except Exception as e:
        logger.exception("callback save failed file_id=%s status=%s err=%s", file_id, status, e)
        return {"error": 1}
