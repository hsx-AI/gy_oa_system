# -*- coding: utf-8 -*-
"""Shared-files disk storage: path safety and atomic replace."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Union

from config import settings

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def get_shared_files_root() -> Path:
    raw = (settings.SHARED_FILES_DIR or "data/shared_files").strip()
    path = Path(raw)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def build_storage_relpath(ext: str) -> str:
    now = datetime.now()
    safe_ext = (ext or "").lower().lstrip(".")
    if not safe_ext:
        raise ValueError("missing file extension")
    name = f"{uuid.uuid4().hex}.{safe_ext}"
    return f"{now.year:04d}/{now.month:02d}/{name}"


def resolve_storage_path(storage_path: str) -> Path:
    root = get_shared_files_root()
    rel = (storage_path or "").replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        raise ValueError("invalid storage_path")
    full = (root / rel).resolve()
    try:
        full.relative_to(root)
    except ValueError as e:
        raise ValueError("storage_path out of root") from e
    return full


def atomic_replace(src_tmp: Union[str, Path], dest: Union[str, Path]) -> None:
    src = Path(src_tmp)
    dst = Path(dest)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, "rb") as f:
        f.flush()
        os.fsync(f.fileno())
    os.replace(str(src), str(dst))


def write_bytes_atomic(dest: Union[str, Path], content: bytes) -> int:
    if not content:
        raise ValueError("empty file content")
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(dest_path.suffix + f".{uuid.uuid4().hex}.tmp")
    try:
        with open(tmp_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_path), str(dest_path))
        return len(content)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def download_to_temp_file(
    *,
    url: str,
    headers: Optional[dict] = None,
    dest_dir: Optional[Path] = None,
    timeout: float = 120.0,
) -> Tuple[Path, int]:
    import httpx

    directory = dest_dir or get_shared_files_root() / "_tmp"
    directory.mkdir(parents=True, exist_ok=True)
    tmp_path = directory / f"oo_save_{uuid.uuid4().hex}.tmp"
    total = 0
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            with client.stream("GET", url, headers=headers or {}) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"download failed HTTP {resp.status_code}")
                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_bytes():
                        if not chunk:
                            continue
                        f.write(chunk)
                        total += len(chunk)
                    f.flush()
                    os.fsync(f.fileno())
        if total <= 0:
            raise RuntimeError("downloaded file is empty")
        return tmp_path, total
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise
