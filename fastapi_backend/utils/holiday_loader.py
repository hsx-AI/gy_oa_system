# -*- coding: utf-8 -*-
"""
假期数据加载
数据来源：数据库 holiday 表（year, date, type）。
"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def load_holidays_for_year(year: str) -> List[Dict[str, str]]:
    """
    从数据库 holiday 表加载某年的假期数据。
    返回: [{"date": "2025-1-1", "type": "放假", "festival": "元旦"}, ...]
    """
    year = str(year).strip()
    if not year:
        return []

    try:
        from database import db
        try:
            rows = db.execute_query(
                "SELECT date, type, festival FROM holiday WHERE year = %s ORDER BY date",
                (int(year),)
            )
        except Exception:
            rows = db.execute_query(
                "SELECT date, type FROM holiday WHERE year = %s ORDER BY date",
                (int(year),)
            )
        if rows:
            return [
                {
                    "date": str(r.get("date", "")).strip(),
                    "type": str(r.get("type", "")).strip(),
                    "festival": str(r.get("festival", "")).strip() if r.get("festival") is not None else ""
                }
                for r in rows if r.get("date")
            ]
    except Exception as e:
        logger.warning(f"从 holiday 表读取假期数据失败: {e}")
    return []


def load_holidays_dict(year: str = None) -> Dict[str, str]:
    """
    加载某年假期为 日期 -> 类型 字典，供智能建议等使用。
    """
    from datetime import datetime
    if not year:
        year = str(datetime.now().year)
    rows = load_holidays_for_year(year)
    return {r["date"]: r["type"] for r in rows if r.get("date")}
