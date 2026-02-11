# -*- coding: utf-8 -*-
"""
Excel 考勤数据处理模块
"""
import openpyxl
from openpyxl import load_workbook
import xlrd
from typing import List, Dict
from datetime import datetime, time, timedelta
import logging
from collections import defaultdict
import os

logger = logging.getLogger(__name__)


class ExcelProcessor:
    """Excel 处理器"""
    
    def __init__(self, file_path: str):
        """初始化处理器"""
        self.file_path = file_path
        self.workbook = None
        self.worksheet = None
        self.is_xls = file_path.lower().endswith('.xls')
        self.xlrd_book = None
        self.xlrd_sheet = None
    
    def load_file(self) -> bool:
        """加载 Excel 文件（支持 .xls 和 .xlsx）"""
        try:
            if self.is_xls:
                # 使用 xlrd 读取 .xls 文件
                self.xlrd_book = xlrd.open_workbook(self.file_path)
                self.xlrd_sheet = self.xlrd_book.sheet_by_index(0)
                logger.info(f"成功加载 .xls 文件: {self.file_path}")
            else:
                # 使用 openpyxl 读取 .xlsx 文件
                self.workbook = load_workbook(self.file_path, data_only=True)
                self.worksheet = self.workbook.active
                logger.info(f"成功加载 .xlsx 文件: {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"加载文件失败: {str(e)}")
            return False
    
    def parse_time_value(self, value) -> str:
        """解析时间值"""
        if value is None or value == "":
            return ""
        
        # 如果是 datetime 对象
        if isinstance(value, datetime):
            return value.strftime("%H:%M:%S")
        
        # 如果是 time 对象
        if isinstance(value, time):
            return value.strftime("%H:%M:%S")
        
        # 如果是字符串
        if isinstance(value, str):
            value = value.strip()
            # 尝试解析各种时间格式
            for fmt in ["%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"]:
                try:
                    t = datetime.strptime(value, fmt)
                    return t.strftime("%H:%M:%S")
                except:
                    continue
            return value
        
        # 如果是数字（Excel 中时间可能以小数形式存储）
        if isinstance(value, (int, float)):
            try:
                # Excel 时间是以天的分数表示的
                total_seconds = int(value * 24 * 3600)
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            except:
                pass
        
        return str(value)
    
    def parse_date_value(self, value) -> str:
        """解析日期值（含 Excel 序列号，避免 .xlsx 中日期被读成数字导致 25-12 等错误）"""
        if value is None or value == "":
            return ""

        # 如果是 datetime 对象
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")

        # Excel 序列号：整数或小数（Windows 基准 1899-12-30）
        if isinstance(value, (int, float)):
            try:
                days = int(round(float(value)))
                base = datetime(1899, 12, 30)
                d = base + timedelta(days=days)
                return d.strftime("%Y-%m-%d")
            except (ValueError, OverflowError):
                pass
            return ""

        # 如果是字符串
        if isinstance(value, str):
            value = value.strip()
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%m/%d/%Y", "%d/%m/%Y"]:
                try:
                    d = datetime.strptime(value, fmt)
                    return d.strftime("%Y-%m-%d")
                except Exception:
                    continue
            return value

        return ""
    
    def read_attendance_data(self, start_row: int = 6) -> List[Dict]:
        """
        读取考勤数据（从指定行开始）
        返回: 原始记录列表
        """
        if self.is_xls:
            return self._read_xls_data(start_row)
        else:
            return self._read_xlsx_data(start_row)
    
    def _read_xls_data(self, start_row: int) -> List[Dict]:
        """读取 .xls 文件数据"""
        if not self.xlrd_sheet:
            logger.error("工作表未加载")
            return []
        
        records = []
        
        try:
            # xlrd 使用0为基准的索引，所以 start_row=6 需要转为索引 5
            for row_idx in range(start_row - 1, self.xlrd_sheet.nrows):
                try:
                    # 读取 A-F 列（0-5）
                    row = self.xlrd_sheet.row(row_idx)
                    
                    if len(row) < 6:
                        continue
                    
                    employee_id = row[0].value
                    employee_name = row[1].value
                    department1 = row[2].value
                    department2 = row[3].value
                    attendance_date = row[4].value
                    attendance_time = row[5].value
                    
                    # 跳过空行
                    if not employee_id or not employee_name:
                        continue
                    
                    # xlrd 日期处理
                    if row[4].ctype == 3:  # XL_CELL_DATE
                        date_tuple = xlrd.xldate_as_tuple(attendance_date, self.xlrd_book.datemode)
                        parsed_date = datetime(*date_tuple[:3]).strftime("%Y-%m-%d")
                    else:
                        parsed_date = self.parse_date_value(attendance_date)
                    
                    # xlrd 时间处理
                    if row[5].ctype == 3:  # XL_CELL_DATE
                        time_tuple = xlrd.xldate_as_tuple(attendance_time, self.xlrd_book.datemode)
                        parsed_time = f"{time_tuple[3]:02d}:{time_tuple[4]:02d}:{time_tuple[5]:02d}"
                    else:
                        parsed_time = self.parse_time_value(attendance_time)
                    
                    if not parsed_date or not parsed_time:
                        logger.warning(f"第{row_idx+1}行数据不完整，跳过")
                        continue
                    
                    record = {
                        'employee_id': str(employee_id).strip() if employee_id else "",
                        'employee_name': str(employee_name).strip() if employee_name else "",
                        'department': str(department1).strip() if department1 else "",
                        'attendance_date': parsed_date,
                        'attendance_time': parsed_time
                    }
                    
                    records.append(record)
                
                except Exception as e:
                    logger.warning(f"读取第{row_idx+1}行失败: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"读取数据失败: {str(e)}")
        
        logger.info(f"共读取 {len(records)} 条原始记录")
        return records
    
    def _read_xlsx_data(self, start_row: int) -> List[Dict]:
        """读取 .xlsx 文件数据"""
        if not self.worksheet:
            logger.error("工作表未加载")
            return []
        
        records = []
        
        try:
            # 从第6行开始读取（A6:F6开始）
            for row_idx, row in enumerate(self.worksheet.iter_rows(min_row=start_row), start=start_row):
                # 读取 A-F 列（员工编号、姓名、部门1、部门2、考勤日期、考勤时间）
                if len(row) < 6:
                    continue
                
                employee_id = row[0].value  # A列：员工编号
                employee_name = row[1].value  # B列：姓名
                department1 = row[2].value  # C列：部门1
                department2 = row[3].value  # D列：部门2（暂时不用）
                attendance_date = row[4].value  # E列：考勤日期
                attendance_time = row[5].value  # F列：考勤时间
                
                # 跳过空行
                if not employee_id or not employee_name:
                    continue
                
                # 解析日期和时间
                parsed_date = self.parse_date_value(attendance_date)
                parsed_time = self.parse_time_value(attendance_time)
                
                if not parsed_date or not parsed_time:
                    logger.warning(f"第{row_idx}行数据不完整，跳过")
                    continue
                
                # 添加记录
                record = {
                    'employee_id': str(employee_id).strip() if employee_id else "",
                    'employee_name': str(employee_name).strip() if employee_name else "",
                    'department': str(department1).strip() if department1 else "",
                    'attendance_date': parsed_date,
                    'attendance_time': parsed_time
                }
                
                records.append(record)
        
        except Exception as e:
            logger.error(f"读取数据失败: {str(e)}")
        
        logger.info(f"共读取 {len(records)} 条原始记录")
        return records
    
    def merge_records_by_employee_and_date(self, records: List[Dict]) -> List[Dict]:
        """
        按员工和日期合并记录
        将同一个人同一天的多条打卡记录合并为一行
        """
        # 使用字典来分组记录
        grouped = defaultdict(list)
        
        for record in records:
            key = (record['employee_id'], record['attendance_date'])
            grouped[key].append(record)
        
        merged_records = []
        
        for (employee_id, attendance_date), group in grouped.items():
            # 按时间排序
            group.sort(key=lambda x: x['attendance_time'])
            
            # 构建合并后的记录
            merged = {
                'employee_id': employee_id,
                'employee_name': group[0]['employee_name'],
                'department': group[0]['department'],
                'attendance_date': attendance_date
            }
            
            # 添加时间字段（最多10个）
            for i, record in enumerate(group[:10], start=1):
                merged[f'time_{i}'] = record['attendance_time']
            
            # 补充剩余的时间字段为None
            for i in range(len(group) + 1, 11):
                merged[f'time_{i}'] = None
            
            merged_records.append(merged)
        
        logger.info(f"合并后共 {len(merged_records)} 条记录")
        return merged_records
    
    def process_file(self, start_row: int = 6) -> tuple:
        """
        处理文件的完整流程
        返回: (是否成功, 合并后的记录列表, 错误信息)
        """
        try:
            # 1. 加载文件
            if not self.load_file():
                return False, [], "文件加载失败"
            
            # 2. 读取原始数据
            raw_records = self.read_attendance_data(start_row)
            
            if not raw_records:
                return False, [], "未读取到有效数据"
            
            # 3. 合并记录
            merged_records = self.merge_records_by_employee_and_date(raw_records)
            
            return True, merged_records, "处理成功"
        
        except Exception as e:
            error_msg = f"处理文件时出错: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
        
        finally:
            # 关闭工作簿
            if self.workbook:
                self.workbook.close()
            # xlrd 不需要显式关闭

