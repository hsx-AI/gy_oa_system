# -*- coding: utf-8 -*-
"""
转轮叶片配重计算结果追溯 API
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rotor-blade-balance", tags=["转轮叶片配重"])


ALLOWED_LSYS = {"焊接工艺室", "部办"}


def _ensure_table():
    try:
        db.execute_update(
            """
            CREATE TABLE IF NOT EXISTS rotor_blade_balance_records (
                id VARCHAR(32) NOT NULL PRIMARY KEY,
                title VARCHAR(255) DEFAULT '',
                station VARCHAR(100) DEFAULT '',
                turbine_no VARCHAR(100) DEFAULT '',
                work_no VARCHAR(100) DEFAULT '',
                mode VARCHAR(10) NOT NULL,
                blade_count INT NOT NULL,
                iz DECIMAL(18, 6) DEFAULT NULL,
                compiler VARCHAR(100) DEFAULT '',
                checker VARCHAR(100) DEFAULT '',
                created_by VARCHAR(100) NOT NULL,
                created_lsys VARCHAR(100) DEFAULT '',
                created_at DATETIME NOT NULL,
                meta_json LONGTEXT,
                input_json LONGTEXT,
                result_json LONGTEXT,
                INDEX idx_created_at (created_at),
                INDEX idx_work_no (work_no),
                INDEX idx_created_by (created_by)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            (),
        )
    except Exception as e:
        logger.warning("创建 rotor_blade_balance_records 表失败: %s", e)


_ensure_table()


def _user_lsys(name: str) -> str:
    rows = db.execute_query(
        "SELECT lsys FROM yggl WHERE name = %s AND COALESCE(zaizhi,0) = 0 LIMIT 1",
        ((name or "").strip(),),
    )
    if not rows:
        return ""
    return (rows[0].get("lsys") or "").strip()


def _assert_allowed_user(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise HTTPException(status_code=403, detail="未登录")
    lsys = _user_lsys(name)
    if lsys not in ALLOWED_LSYS:
        raise HTTPException(status_code=403, detail="仅焊接工艺室和部办可使用")
    return lsys


def _json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, separators=(",", ":"))


def _json_loads(value: Any, fallback: Any):
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _dt_text(value: Any) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value or "")


class RotorBladeBalanceSaveRequest(BaseModel):
    current_user: str
    title: str = ""
    meta: Dict[str, Any] = Field(default_factory=dict)
    inputData: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)


def _format_record(row: Dict[str, Any], include_payload: bool = False) -> Dict[str, Any]:
    item = {
        "id": row.get("id") or "",
        "title": row.get("title") or "",
        "station": row.get("station") or "",
        "turbineNo": row.get("turbine_no") or "",
        "workNo": row.get("work_no") or "",
        "mode": row.get("mode") or "",
        "bladeCount": int(row.get("blade_count") or 0),
        "iz": float(row.get("iz") or 0),
        "compiler": row.get("compiler") or "",
        "checker": row.get("checker") or "",
        "createdBy": row.get("created_by") or "",
        "createdLsys": row.get("created_lsys") or "",
        "createdAt": _dt_text(row.get("created_at")),
    }
    if include_payload:
        item["meta"] = _json_loads(row.get("meta_json"), {})
        item["inputData"] = _json_loads(row.get("input_json"), {})
        item["result"] = _json_loads(row.get("result_json"), {})
    return item


@router.post("/records")
def save_record(req: RotorBladeBalanceSaveRequest):
    lsys = _assert_allowed_user(req.current_user)
    result = req.result or {}
    mode = (result.get("mode") or req.inputData.get("mode") or "").strip()
    blade_count = int(result.get("bladeCount") or req.inputData.get("bladeCount") or 0)
    if mode not in ("V1", "V2"):
        raise HTTPException(status_code=400, detail="计算结果缺少叶片形式")
    if blade_count <= 0:
        raise HTTPException(status_code=400, detail="计算结果缺少叶片数量")
    rows = result.get("rows")
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=400, detail="计算结果为空，无法保存")

    meta = req.meta or {}
    station = (meta.get("station") or "").strip()
    turbine_no = (meta.get("turbineNo") or "").strip()
    work_no = (meta.get("workNo") or "").strip()
    compiler = (meta.get("compiler") or "").strip()
    checker = (meta.get("checker") or "").strip()
    title = (req.title or "").strip()
    if not title:
        title_parts = [p for p in [station, turbine_no, work_no] if p]
        title = " / ".join(title_parts) or f"转轮叶片配重 {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    rid = uuid.uuid4().hex
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    affected = db.execute_update(
        """
        INSERT INTO rotor_blade_balance_records
        (id, title, station, turbine_no, work_no, mode, blade_count, iz,
         compiler, checker, created_by, created_lsys, created_at,
         meta_json, input_json, result_json)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            rid,
            title,
            station,
            turbine_no,
            work_no,
            mode,
            blade_count,
            float(result.get("iz") or 0),
            compiler,
            checker,
            req.current_user.strip(),
            lsys,
            now_str,
            _json_dumps(meta),
            _json_dumps(req.inputData),
            _json_dumps(result),
        ),
    )
    if affected < 0:
        raise HTTPException(status_code=500, detail="保存失败")
    return {"success": True, "id": rid, "message": "保存成功"}


@router.get("/records")
def list_records(
    current_user: str = Query(..., description="当前用户姓名"),
    keyword: Optional[str] = Query(None, description="电站/水轮机号/工作号/保存人/标题"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    _assert_allowed_user(current_user)
    where = ["1=1"]
    params = []
    kw = (keyword or "").strip()
    if kw:
        like = f"%{kw}%"
        where.append("(title LIKE %s OR station LIKE %s OR turbine_no LIKE %s OR work_no LIKE %s OR created_by LIKE %s)")
        params.extend([like, like, like, like, like])
    where_sql = " AND ".join(where)
    total = db.execute_scalar(
        f"SELECT COUNT(*) AS cnt FROM rotor_blade_balance_records WHERE {where_sql}",
        tuple(params),
    ) or 0
    offset = (page - 1) * page_size
    rows = db.execute_query(
        f"""
        SELECT id, title, station, turbine_no, work_no, mode, blade_count, iz,
               compiler, checker, created_by, created_lsys, created_at
        FROM rotor_blade_balance_records
        WHERE {where_sql}
        ORDER BY created_at DESC, id DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [page_size, offset]),
    )
    return {
        "success": True,
        "list": [_format_record(r) for r in (rows or [])],
        "total": int(total),
        "page": page,
        "pageSize": page_size,
    }


@router.get("/records/{record_id}")
def get_record(record_id: str, current_user: str = Query(..., description="当前用户姓名")):
    _assert_allowed_user(current_user)
    rows = db.execute_query(
        """
        SELECT id, title, station, turbine_no, work_no, mode, blade_count, iz,
               compiler, checker, created_by, created_lsys, created_at,
               meta_json, input_json, result_json
        FROM rotor_blade_balance_records
        WHERE id = %s
        LIMIT 1
        """,
        ((record_id or "").strip(),),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "record": _format_record(rows[0], include_payload=True)}
