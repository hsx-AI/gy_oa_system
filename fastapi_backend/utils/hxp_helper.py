# -*- coding: utf-8 -*-
"""换休票(hxp)工具：过期规则、扣减逻辑"""
from datetime import datetime
from dateutil.relativedelta import relativedelta


def compute_expire_date(sj) -> str:
    """
    根据获得时间计算过期日期
    规则：换休票有效期均为 1 年（获得日 + 1 年）
    """
    if sj is None:
        return ""
    if isinstance(sj, str):
        try:
            sj = datetime.strptime(sj[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return ""
    if not hasattr(sj, "year"):
        return ""
    exp = sj + relativedelta(years=1)
    return f"{exp.year}-{exp.month:02d}-{exp.day:02d}"


def parse_expire_for_sort(exp_str: str) -> tuple:
    """解析过期日期字符串用于排序 (year, month)"""
    if not exp_str or len(exp_str) < 7:
        return (9999, 12)
    try:
        parts = exp_str.split("-")
        return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 12)
    except (ValueError, IndexError):
        return (9999, 12)
