# -*- coding: utf-8 -*-
"""文件页数统计 API"""
import logging
import os
import shutil
import tempfile
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from utils.file_page_counter import SUPPORTED_EXTENSIONS, build_summary, count_files

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/file-page-counter", tags=["文件页数统计"])

MAX_FILES = 200
MAX_FILE_MB = 100


@router.post("/count")
async def count_uploaded_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个文件")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"单次最多上传 {MAX_FILES} 个文件")

    temp_dir = tempfile.mkdtemp(prefix="oa_page_counter_")
    saved_paths: List[str] = []

    try:
        for upload in files:
            filename = os.path.basename((upload.filename or "").strip())
            if not filename:
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的文件格式：{filename}，仅支持 PDF、Word、PPT、Excel",
                )

            content = await upload.read()
            size_mb = len(content) / (1024 * 1024)
            if size_mb > MAX_FILE_MB:
                raise HTTPException(
                    status_code=400,
                    detail=f"文件 {filename} 超过 {MAX_FILE_MB}MB 上限",
                )

            target = os.path.join(temp_dir, filename)
            base, ext_name = os.path.splitext(filename)
            counter = 1
            while os.path.exists(target):
                target = os.path.join(temp_dir, f"{base}_{counter}{ext_name}")
                counter += 1

            with open(target, "wb") as fp:
                fp.write(content)
            saved_paths.append(target)

        if not saved_paths:
            raise HTTPException(status_code=400, detail="未收到有效文件")

        items = count_files(saved_paths)
        summary = build_summary(items)
        return {
            "success": True,
            "data": {
                "items": items,
                "summary": summary,
            },
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
