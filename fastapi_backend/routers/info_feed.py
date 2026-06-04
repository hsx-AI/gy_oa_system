# -*- coding: utf-8 -*-
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel


router = APIRouter(prefix="/info-feed", tags=["天气新闻"])

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "info_feed"
MEDIA_DIR = DATA_DIR / "uploads"
STORE_FILE = DATA_DIR / "store.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


class PushDataRequest(BaseModel):
    type: str
    key: str
    data: Any


class ClearCacheRequest(BaseModel):
    scope: str = "news"
    clear_media: bool = True


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_store() -> dict[str, Any]:
    if not STORE_FILE.exists():
        return {}
    try:
        with STORE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_store(store: dict[str, Any]) -> None:
    tmp_file = STORE_FILE.with_suffix(".tmp")
    with tmp_file.open("w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, STORE_FILE)


def _get_cached(cache_key: str) -> Any:
    store = _load_store()
    item = store.get(cache_key)
    if not item:
        raise HTTPException(status_code=404, detail=f"暂无缓存数据: {cache_key}")
    return item.get("data")


@router.post("/push/data")
async def push_data(req: PushDataRequest):
    cache_key = f"{req.type}:{req.key}"
    store = _load_store()
    store[cache_key] = {
        "type": req.type,
        "key": req.key,
        "data": req.data,
        "updated_at": _now_text(),
    }
    _save_store(store)
    return {"success": True, "status": "ok", "key": cache_key, "time": _now_text()}


@router.post("/push/media")
async def push_media(name: str = Form(...), file: UploadFile = File(...)):
    safe_name = Path(name).name
    if not safe_name:
        raise HTTPException(status_code=400, detail="缺少文件名")
    target = MEDIA_DIR / safe_name
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    target.write_bytes(content)
    return {"success": True, "status": "ok", "url": f"/api/info-feed/uploads/{safe_name}"}


@router.post("/push/clear")
async def clear_cache(req: ClearCacheRequest):
    store = _load_store()
    if req.scope == "all":
        removed_keys = len(store)
        store = {}
    elif req.scope == "news":
        old_count = len(store)
        store = {k: v for k, v in store.items() if not k.startswith("news:")}
        removed_keys = old_count - len(store)
    else:
        raise HTTPException(status_code=400, detail="scope 仅支持 news/all")
    _save_store(store)

    removed_media = 0
    if req.clear_media and MEDIA_DIR.exists():
        for path in MEDIA_DIR.iterdir():
            try:
                if path.is_file() or path.is_symlink():
                    path.unlink()
                    removed_media += 1
                elif path.is_dir():
                    shutil.rmtree(path)
                    removed_media += 1
            except Exception:
                pass
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    return {
        "success": True,
        "status": "ok",
        "scope": req.scope,
        "removedKeys": removed_keys,
        "removedMedia": removed_media,
        "time": _now_text(),
    }


@router.get("/weather/now")
async def weather_now(location: str = Query(...)):
    return _get_cached(f"weather:now:{location}")


@router.get("/weather/hourly/{hours}")
async def weather_hourly(hours: str, location: str = Query(...)):
    return _get_cached(f"weather:hourly:{hours}:{location}")


@router.get("/weather/daily/{days}")
async def weather_daily(days: str, location: str = Query(...)):
    return _get_cached(f"weather:daily:{days}:{location}")


@router.get("/news/list")
async def news_list(type: str = Query("top"), page: str = Query("1")):
    return _get_cached(f"news:list:{type}:{page}")


@router.get("/news/detail")
async def news_detail(uniquekey: str = Query(...)):
    return _get_cached(f"news:detail:{uniquekey}")


@router.get("/summary")
async def summary():
    store = _load_store()
    keys = sorted(store.keys())
    latest = ""
    for item in store.values():
        updated_at = item.get("updated_at", "")
        if updated_at > latest:
            latest = updated_at
    return {"success": True, "count": len(keys), "latestUpdate": latest, "keys": keys}


@router.get("/uploads/{filename}")
async def uploaded_media(filename: str):
    safe_name = Path(filename).name
    path = MEDIA_DIR / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path)
