# -*- coding: utf-8 -*-
"""加班登记换休票张数计算（与前端 overtimeExchangeTickets.js 一致）"""
import math


def calc_overtime_exchange_tickets(hours: float, jb: str = "") -> float:
    """
    加班换休票张数（向下取整到最小单位）。
    - 平时加班：1 小时 = 0.25 张，步长 0.25（1 天 8 小时 = 2 张）
    - 值班：1 小时 = 0.125 张，步长 0.125
    """
    try:
        h = float(hours or 0)
    except (TypeError, ValueError):
        return 0.0
    if h <= 0:
        return 0.0
    is_duty = (jb or "").strip() == "值班"
    step = 0.125 if is_duty else 0.25
    per_hour = 0.125 if is_duty else 0.25
    raw = h * per_hour
    n = math.floor(raw / step + 1e-9)
    return round(n * step, 3)
