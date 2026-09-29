# -*- coding: utf-8 -*-
"""
Cross-process ephemeral key-value store (MySQL).

Used by auth verification codes / captchas so multi-worker uvicorn
shares state. Falls back to process-local memory if DB is unavailable.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

from database import db

logger = logging.getLogger(__name__)

_TABLE = "oa_auth_ephemeral"
_table_ready = False
_table_lock = threading.Lock()
_memory: Dict[str, Dict[str, Any]] = {}
_memory_lock = threading.Lock()
_use_memory_only = False


def _ensure_table() -> bool:
    global _table_ready, _use_memory_only
    if _use_memory_only:
        return False
    if _table_ready:
        return True
    with _table_lock:
        if _use_memory_only:
            return False
        if _table_ready:
            return True
        try:
            affected = db.execute_update(
                f"""
                CREATE TABLE IF NOT EXISTS `{_TABLE}` (
                  `cache_key` VARCHAR(191) NOT NULL,
                  `payload` MEDIUMTEXT NOT NULL,
                  `expires_at` DOUBLE NOT NULL,
                  PRIMARY KEY (`cache_key`),
                  KEY `idx_expires_at` (`expires_at`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """,
                (),
            )
            if affected < 0:
                raise RuntimeError("CREATE TABLE returned error")
            _table_ready = True
            return True
        except Exception as e:
            logger.warning("ephemeral store table unavailable, using memory: %s", e)
            _use_memory_only = True
            return False


def _lock_name(key: str) -> str:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:20]
    return f"oa_eph_{digest}"


def _mem_get(key: str) -> Optional[dict]:
    now = time.time()
    with _memory_lock:
        item = _memory.get(key)
        if not item:
            return None
        if float(item.get("expires_at") or 0) < now:
            _memory.pop(key, None)
            return None
        payload = item.get("payload")
        return dict(payload) if isinstance(payload, dict) else None


def _mem_set(key: str, payload: dict, expires_at: float) -> None:
    with _memory_lock:
        _memory[key] = {"payload": dict(payload), "expires_at": float(expires_at)}


def _mem_delete(key: str) -> None:
    with _memory_lock:
        _memory.pop(key, None)


def get_item(key: str) -> Optional[dict]:
    clean = (key or "").strip()
    if not clean:
        return None
    if not _ensure_table():
        return _mem_get(clean)
    now = time.time()
    rows = db.execute_query(
        f"SELECT payload, expires_at FROM `{_TABLE}` WHERE cache_key=%s LIMIT 1",
        (clean,),
    )
    if not rows:
        return None
    expires_at = float(rows[0].get("expires_at") or 0)
    if expires_at < now:
        delete_item(clean)
        return None
    try:
        payload = json.loads(rows[0].get("payload") or "{}")
    except Exception:
        delete_item(clean)
        return None
    return payload if isinstance(payload, dict) else None


def set_item(key: str, payload: dict, expires_at: float) -> None:
    clean = (key or "").strip()
    if not clean:
        return
    body = dict(payload or {})
    exp = float(expires_at)
    if not _ensure_table():
        _mem_set(clean, body, exp)
        return
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    affected = db.execute_update(
        f"""
        INSERT INTO `{_TABLE}` (cache_key, payload, expires_at)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE payload=VALUES(payload), expires_at=VALUES(expires_at)
        """,
        (clean, raw, exp),
    )
    if affected < 0:
        _mem_set(clean, body, exp)


def delete_item(key: str) -> None:
    clean = (key or "").strip()
    if not clean:
        return
    if not _ensure_table():
        _mem_delete(clean)
        return
    db.execute_update(f"DELETE FROM `{_TABLE}` WHERE cache_key=%s", (clean,))
    _mem_delete(clean)


def mutate_item(
    key: str,
    mutator: Callable[[Optional[dict]], Optional[dict]],
    *,
    default_ttl: float = 300,
) -> Optional[dict]:
    """
    Atomic read-modify-write across workers.
    mutator(current_or_None) -> new_payload to keep, or None to delete.
    Returns the payload left in store (None if deleted/missing).
    """
    clean = (key or "").strip()
    if not clean:
        return None

    if not _ensure_table():
        current = _mem_get(clean)
        nxt = mutator(dict(current) if current else None)
        if nxt is None:
            _mem_delete(clean)
            return None
        expires_at = float(nxt.get("expires") or nxt.get("expires_at") or (time.time() + default_ttl))
        _mem_set(clean, nxt, expires_at)
        return dict(nxt)

    lock = _lock_name(clean)
    conn = None
    try:
        conn = db.get_connection()
        if not conn:
            current = _mem_get(clean)
            nxt = mutator(dict(current) if current else None)
            if nxt is None:
                _mem_delete(clean)
                return None
            expires_at = float(nxt.get("expires") or nxt.get("expires_at") or (time.time() + default_ttl))
            _mem_set(clean, nxt, expires_at)
            return dict(nxt)

        with conn.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK(%s, 5) AS acquired", (lock,))
            row = cursor.fetchone() or {}
            acquired = int(row.get("acquired") or 0) == 1
            if not acquired:
                logger.warning("ephemeral lock timeout for %s", clean)

            now = time.time()
            cursor.execute(
                f"SELECT payload, expires_at FROM `{_TABLE}` WHERE cache_key=%s LIMIT 1",
                (clean,),
            )
            row = cursor.fetchone()
            current = None
            if row:
                exp = float(row.get("expires_at") or 0)
                if exp >= now:
                    try:
                        parsed = json.loads(row.get("payload") or "{}")
                        if isinstance(parsed, dict):
                            current = parsed
                    except Exception:
                        current = None

            nxt = mutator(dict(current) if current else None)
            if nxt is None:
                cursor.execute(f"DELETE FROM `{_TABLE}` WHERE cache_key=%s", (clean,))
            else:
                expires_at = float(
                    nxt.get("expires") or nxt.get("expires_at") or (time.time() + default_ttl)
                )
                raw = json.dumps(nxt, ensure_ascii=False, separators=(",", ":"))
                cursor.execute(
                    f"""
                    INSERT INTO `{_TABLE}` (cache_key, payload, expires_at)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE payload=VALUES(payload), expires_at=VALUES(expires_at)
                    """,
                    (clean, raw, expires_at),
                )
            conn.commit()
            if acquired:
                cursor.execute("SELECT RELEASE_LOCK(%s)", (lock,))
            return dict(nxt) if nxt is not None else None
    except Exception as e:
        logger.warning("ephemeral mutate failed for %s: %s", clean, e)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        current = _mem_get(clean)
        nxt = mutator(dict(current) if current else None)
        if nxt is None:
            _mem_delete(clean)
            return None
        expires_at = float(nxt.get("expires") or nxt.get("expires_at") or (time.time() + default_ttl))
        _mem_set(clean, nxt, expires_at)
        return dict(nxt)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
