# -*- coding: utf-8 -*-
"""ONLYOFFICE / shared-docs security token service."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import jwt

from config import settings

logger = logging.getLogger(__name__)

PURPOSE_ONLYOFFICE_DOWNLOAD = "onlyoffice_download"
ALGORITHM = "HS256"


class OnlyOfficeConfigError(RuntimeError):
    """Missing or invalid ONLYOFFICE settings."""


def _strip(value: Optional[str]) -> str:
    return (value or "").strip()


def get_onlyoffice_url() -> str:
    url = _strip(settings.ONLYOFFICE_URL).rstrip("/")
    if not url:
        raise OnlyOfficeConfigError("ONLYOFFICE_URL is not configured")
    return url


def get_public_api_base() -> str:
    base = _strip(settings.ONLYOFFICE_PUBLIC_API_BASE).rstrip("/")
    if not base:
        raise OnlyOfficeConfigError("ONLYOFFICE_PUBLIC_API_BASE is not configured")
    return base


def get_onlyoffice_jwt_secret() -> str:
    secret = _strip(settings.ONLYOFFICE_JWT_SECRET)
    if not secret:
        raise OnlyOfficeConfigError("ONLYOFFICE_JWT_SECRET is not configured")
    return secret


def get_signing_secret() -> str:
    """Prefer SHARED_FILES_SIGNING_SECRET; fallback to ONLYOFFICE_JWT_SECRET."""
    dedicated = _strip(settings.SHARED_FILES_SIGNING_SECRET)
    if dedicated:
        return dedicated
    return get_onlyoffice_jwt_secret()


def get_jwt_header_name() -> str:
    return _strip(settings.ONLYOFFICE_JWT_HEADER) or "Authorization"


def build_document_key(file_id: int, version: int) -> str:
    return f"{int(file_id)}-v{int(version)}"


def sign_editor_config(config: Dict[str, Any]) -> str:
    secret = get_onlyoffice_jwt_secret()
    payload = {k: v for k, v in config.items() if k != "token"}
    token = jwt.encode(payload, secret, algorithm=ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def verify_onlyoffice_callback_token(token: str) -> Dict[str, Any]:
    secret = get_onlyoffice_jwt_secret()
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as e:
        logger.warning("ONLYOFFICE callback JWT verify failed: %s", type(e).__name__)
        raise


def make_download_from_ds_auth_header(file_url: str) -> Dict[str, str]:
    secret = get_onlyoffice_jwt_secret()
    token = jwt.encode({"url": file_url}, secret, algorithm=ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return {get_jwt_header_name(): f"Bearer {token}"}


def issue_onlyoffice_download_token(
    *,
    file_id: int,
    version: int,
    document_key: str,
    ttl_seconds: Optional[int] = None,
) -> str:
    secret = get_signing_secret()
    ttl = int(ttl_seconds if ttl_seconds is not None else settings.SHARED_FILES_DOWNLOAD_TOKEN_TTL_SECONDS)
    if ttl <= 0:
        ttl = 900
    now = int(time.time())
    payload = {
        "file_id": int(file_id),
        "purpose": PURPOSE_ONLYOFFICE_DOWNLOAD,
        "version": int(version),
        "key": document_key,
        "iat": now,
        "exp": now + ttl,
    }
    token = jwt.encode(payload, secret, algorithm=ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def verify_onlyoffice_download_token(token: str, *, expected_file_id: int) -> Dict[str, Any]:
    secret = get_signing_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.warning("shared-file download token expired file_id=%s", expected_file_id)
        raise
    except jwt.PyJWTError as e:
        logger.warning(
            "shared-file download token invalid file_id=%s err=%s",
            expected_file_id,
            type(e).__name__,
        )
        raise

    purpose = str(payload.get("purpose") or "")
    if purpose != PURPOSE_ONLYOFFICE_DOWNLOAD:
        raise jwt.InvalidTokenError(f"unexpected purpose: {purpose}")

    try:
        token_file_id = int(payload.get("file_id"))
    except (TypeError, ValueError) as e:
        raise jwt.InvalidTokenError("invalid file_id in token") from e

    if token_file_id != int(expected_file_id):
        raise jwt.InvalidTokenError("file_id mismatch")

    return payload
