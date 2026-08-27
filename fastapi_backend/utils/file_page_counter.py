# -*- coding: utf-8 -*-
"""文件页数统计：PDF / Word / PPT / Excel"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

PageCount = Union[int, str]
SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def _count_pdf(path: str) -> PageCount:
    try:
        import fitz

        doc = fitz.open(path)
        try:
            return doc.page_count
        finally:
            doc.close()
    except Exception as exc:
        logger.warning("PDF 页数统计失败 [%s]: %s", os.path.basename(path), exc)
        return "PDF错误"


def _count_pptx(path: str) -> PageCount:
    try:
        from pptx import Presentation

        prs = Presentation(path)
        return len(prs.slides)
    except Exception as exc:
        logger.warning("PPT 页数统计失败 [%s]: %s", os.path.basename(path), exc)
        return "PPT错误"


def _create_word_app():
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word_app = win32com.client.DispatchEx("Word.Application")
    word_app.Visible = False
    return word_app


def _quit_word_app(word_app) -> None:
    if not word_app:
        return
    try:
        word_app.Quit()
    except Exception as exc:
        logger.warning("退出 Word 失败: %s", exc)
    try:
        import pythoncom

        pythoncom.CoUninitialize()
    except Exception:
        pass


def _count_word(path: str, word_app=None, *, own_instance: bool = False) -> PageCount:
    doc = None
    local_app = None
    try:
        if word_app is None:
            local_app = _create_word_app()
            word_app = local_app

        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return "路径错误"

        doc = word_app.Documents.Open(
            FileName=abs_path,
            ReadOnly=True,
            AddToRecentFiles=False,
        )
        return int(doc.ComputeStatistics(2))
    except Exception as exc:
        logger.warning("Word 页数统计失败 [%s]: %s", os.path.basename(path), exc)
        return "读取错误"
    finally:
        if doc is not None:
            try:
                doc.Close(SaveChanges=0)
            except Exception as exc:
                logger.warning("关闭 Word 文档失败: %s", exc)
        if own_instance and local_app is not None:
            _quit_word_app(local_app)


def _count_ppt(path: str) -> PageCount:
    app = None
    presentation = None
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        app = win32com.client.DispatchEx("PowerPoint.Application")
        app.Visible = False
        abs_path = os.path.abspath(path)
        presentation = app.Presentations.Open(abs_path, WithWindow=False)
        return int(presentation.Slides.Count)
    except Exception as exc:
        logger.warning("PPT 页数统计失败 [%s]: %s", os.path.basename(path), exc)
        return "PPT错误"
    finally:
        if presentation is not None:
            try:
                presentation.Close()
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
            try:
                import pythoncom

                pythoncom.CoUninitialize()
            except Exception:
                pass


def count_single_file(path: str, word_app=None) -> Dict[str, Any]:
    filename = os.path.basename(path)
    ext = _ext(path)
    file_type = ext.lstrip(".").upper() if ext else "未知"
    page_count: PageCount = "不适用"

    if ext == ".pdf":
        page_count = _count_pdf(path)
    elif ext in {".doc", ".docx"}:
        page_count = _count_word(path, word_app)
    elif ext == ".pptx":
        page_count = _count_pptx(path)
    elif ext == ".ppt":
        page_count = _count_ppt(path)
    elif ext in {".xls", ".xlsx"}:
        page_count = 1
    else:
        file_type = "未知"
        page_count = "不适用"

    return {
        "filename": filename,
        "page_count": page_count,
        "file_type": file_type,
    }


def count_files(file_paths: List[str]) -> List[Dict[str, Any]]:
    needs_word = any(_ext(path) in {".doc", ".docx"} for path in file_paths)
    word_app = None
    results: List[Dict[str, Any]] = []

    try:
        if needs_word:
            try:
                word_app = _create_word_app()
            except Exception as exc:
                logger.warning("无法启动 Word 实例，Word 文件将返回错误: %s", exc)
                word_app = None

        for path in file_paths:
            results.append(count_single_file(path, word_app))
        return results
    finally:
        _quit_word_app(word_app)


def build_summary(items: List[Dict[str, Any]]) -> Dict[str, int]:
    summary = {
        "total": 0,
        "pdf": 0,
        "word": 0,
        "ppt": 0,
        "excel": 0,
    }
    for item in items:
        value = item.get("page_count")
        if not isinstance(value, (int, float)):
            continue
        pages = int(value)
        summary["total"] += pages
        file_type = (item.get("file_type") or "").upper()
        if file_type == "PDF":
            summary["pdf"] += pages
        elif file_type in {"DOC", "DOCX"}:
            summary["word"] += pages
        elif file_type in {"PPT", "PPTX"}:
            summary["ppt"] += pages
        elif file_type in {"XLS", "XLSX"}:
            summary["excel"] += pages
    return summary
