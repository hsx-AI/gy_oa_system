# -*- coding: utf-8 -*-
"""
辅助函数
"""
from datetime import datetime, date
from typing import Any, Optional


def safe_str(val: Any) -> str:
    """安全转换为字符串"""
    if val is None:
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d %H:%M:%S") if isinstance(val, datetime) else val.strftime("%Y-%m-%d")
    return str(val).strip()


def format_datetime_plain(val: Any) -> str:
    """
    格式化为 YYYY-MM-DD HH:MM:SS，无小数秒（不输出 .000000）。
    用于 API 返回的 timefrom、timeto 等，便于前端展示且与其他时间比较一致。
    """
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(val, date) and not isinstance(val, datetime):
        return val.strftime("%Y-%m-%d") + " 00:00:00"
    s = str(val).strip()
    if not s:
        return ""
    if "." in s:
        s = s.split(".")[0]
    return s[:19] if len(s) > 19 else s


def normalize_datetime_for_db(val: Any) -> str:
    """
    规范为 YYYY-MM-DD HH:MM:SS，用于写入 DATETIME(0) 列（如 qj/timefrom、timeto）。
    支持前端 datetime-local 的 "2025-03-15T08:00" 或 "2025-03-15 08:00:00"。
    若无效则返回当天 00:00:00。
    """
    if val is None:
        val = ""
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(val, date) and not isinstance(val, datetime):
        return val.strftime("%Y-%m-%d") + " 00:00:00"
    s = str(val).strip().replace("T", " ").replace("  ", " ")
    if "." in s:
        s = s.split(".")[0]
    s = s.strip()
    if not s:
        return datetime.now().strftime("%Y-%m-%d 00:00:00")
    parts = s.split(" ", 1)
    date_part = (parts[0] or "").strip()[:10]
    time_part = (parts[1] if len(parts) > 1 else "").strip() or "00:00:00"
    if len(date_part) < 10:
        date_part = datetime.now().strftime("%Y-%m-%d")
    if ":" not in time_part:
        time_part = "00:00:00"
    else:
        segs = time_part.split(":")
        h = segs[0].zfill(2) if segs else "00"
        m = segs[1].zfill(2) if len(segs) > 1 else "00"
        sec = segs[2].zfill(2) if len(segs) > 2 else "00"
        time_part = f"{h}:{m}:{sec}"
    return f"{date_part} {time_part}"


def safe_time_str(val: Any) -> str:
    """安全转换时间为字符串"""
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.strftime("%H:%M:%S")
    return str(val).strip()


def is_overtime(jiaban_value: Any) -> bool:
    """判断是否为加班"""
    if jiaban_value is None:
        return False
    
    jiaban_str = str(jiaban_value).strip().lower()
    
    # 判断为加班的情况
    if jiaban_str in ["1", "true", "yes", "是"]:
        return True
    
    # 如果有值且不是明确的"否"
    if jiaban_str and jiaban_str not in ["0", "false", "no", "否", ""]:
        return True
    
    return False


def normalize_date_str(date_obj: Any) -> str:
    """标准化日期字符串为 YYYY-MM-DD 格式"""
    if date_obj is None:
        return ""
    
    if isinstance(date_obj, str):
        return date_obj
    
    if isinstance(date_obj, (datetime, date)):
        return date_obj.strftime("%Y-%m-%d")
    
    return str(date_obj)


def time_to_decimal(time_obj: Any) -> float:
    """将时间转换为小时的小数形式"""
    if time_obj is None:
        return 0.0
    
    if isinstance(time_obj, datetime):
        return time_obj.hour + time_obj.minute / 60.0
    
    if isinstance(time_obj, str):
        try:
            # 尝试解析时间字符串
            if ":" in time_obj:
                parts = time_obj.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                return hour + minute / 60.0
        except:
            pass
    
    return 0.0


def format_time(time_obj: Any) -> str:
    """格式化时间显示"""
    if time_obj is None:
        return ""
    
    if isinstance(time_obj, datetime):
        return time_obj.strftime("%H:%M")
    
    if isinstance(time_obj, str):
        # 如果已经是字符串，尝试格式化
        if ":" in time_obj:
            parts = time_obj.split(":")
            return f"{parts[0]}:{parts[1]}"
    
    return str(time_obj)

