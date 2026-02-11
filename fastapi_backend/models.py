# -*- coding: utf-8 -*-
"""
数据模型
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class DakaRecord(BaseModel):
    """打卡记录模型"""
    部门: str
    姓名: str
    日期: str
    时间1: Optional[str] = ""
    时间2: Optional[str] = ""
    时间3: Optional[str] = ""
    时间4: Optional[str] = ""
    时间5: Optional[str] = ""
    时间6: Optional[str] = ""
    状态: Optional[str] = ""


class DakaResponse(BaseModel):
    """打卡数据响应"""
    success: bool
    message: Optional[str] = None
    userName: Optional[str] = None
    userDept: Optional[str] = None
    data: List[DakaRecord] = []


class Holiday(BaseModel):
    """假期模型"""
    date: str
    type: str
    # 新增：节日名称（如 元旦/春节/清明/五一/端午/中秋/国庆 等）
    festival: Optional[str] = None


class HolidayResponse(BaseModel):
    """假期数据响应"""
    success: bool
    year: str
    holidays: List[Holiday] = []


class Suggestion(BaseModel):
    """建议模型"""
    date: str
    dayType: str
    suggestion: str
    status: int = 0  # 0=加班 1=缺勤
    handled: bool = False  # 是否已处理完成（已审批通过并覆盖该建议区间）
    under_review: bool = False  # 是否正在审核（已提交但未审批通过）


class SuggestionResponse(BaseModel):
    """建议数据响应"""
    success: bool
    suggestions: List[Suggestion] = []

