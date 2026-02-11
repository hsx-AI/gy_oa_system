# -*- coding: utf-8 -*-
"""
考勤数据库模块 - MySQL 实现
"""
import logging
import uuid
from typing import List, Dict, Optional
from database import db

logger = logging.getLogger(__name__)

# 进程内只执行一次：确保 attendance_records 有 (employee_id, attendance_date) 唯一约束，避免重复上传重复录入
_attendance_unique_key_ensured = False


class AttendanceDatabase:
    """考勤数据库类"""
    
    def __init__(self):
        """初始化"""
        # 这里的初始化主要依赖 database.py 的 db 实例
        pass
    
    def get_connection(self):
        """获取数据库连接 (直接返回 db 的连接，用于特殊操作)"""
        return db.get_connection()

    def get_employee_by_gh(self, gh: str) -> Optional[Dict]:
        """按工号(gh)查 yggl，返回 name、lsys，用于打卡上传时映射姓名与科室。"""
        if not gh or not str(gh).strip():
            return None
        try:
            rows = db.execute_query(
                "SELECT name, lsys FROM yggl WHERE TRIM(gh) = %s LIMIT 1",
                (str(gh).strip(),),
            )
            if rows:
                return {"name": (rows[0].get("name") or "").strip(), "lsys": (rows[0].get("lsys") or "").strip()}
            return None
        except Exception as e:
            logger.warning(f"按工号查询 yggl 失败: {e}")
            return None

    def insert_or_update_record(self, record: Dict) -> bool:
        """插入或更新考勤记录（表有 id 列且无默认值时需显式传入）"""
        try:
            record_id = record.get("id") or uuid.uuid4().hex
            # 使用 ON DUPLICATE KEY UPDATE 语法；id 列无默认值，需显式传入
            sql = """
                INSERT INTO attendance_records 
                (id, employee_id, employee_name, department, attendance_date,
                 time_1, time_2, time_3, time_4, time_5,
                 time_6, time_7, time_8, time_9, time_10)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                employee_name=VALUES(employee_name), department=VALUES(department),
                time_1=VALUES(time_1), time_2=VALUES(time_2), time_3=VALUES(time_3),
                time_4=VALUES(time_4), time_5=VALUES(time_5), time_6=VALUES(time_6),
                time_7=VALUES(time_7), time_8=VALUES(time_8), time_9=VALUES(time_9),
                time_10=VALUES(time_10), updated_at=CURRENT_TIMESTAMP
            """
            params = (
                record_id,
                record['employee_id'], record['employee_name'], record['department'],
                record['attendance_date'],
                record.get('time_1'), record.get('time_2'), record.get('time_3'),
                record.get('time_4'), record.get('time_5'), record.get('time_6'),
                record.get('time_7'), record.get('time_8'), record.get('time_9'),
                record.get('time_10')
            )
            
            result = db.execute_update(sql, params)
            return result >= 0
        except Exception as e:
            logger.error(f"插入/更新记录失败: {str(e)}")
            return False
    
    def _ensure_attendance_unique_key_once(self):
        """确保 attendance_records 存在 (employee_id, attendance_date) 唯一约束，进程内只执行一次。"""
        global _attendance_unique_key_ensured
        if _attendance_unique_key_ensured:
            return
        try:
            rows = db.execute_query(
                "SELECT COUNT(*) AS cnt FROM information_schema.STATISTICS "
                "WHERE table_schema = DATABASE() AND table_name = 'attendance_records' AND index_name = 'uk_employee_date'",
                (),
            )
            if rows and (rows[0].get("cnt") or 0) > 0:
                _attendance_unique_key_ensured = True
                return
            # 先去重再加唯一键。employee_id 若为 TEXT/VARCHAR 很长，需指定前缀长度否则报 1170
            db.execute_update(
                "DELETE t1 FROM attendance_records t1 "
                "INNER JOIN attendance_records t2 "
                "ON t1.employee_id = t2.employee_id AND t1.attendance_date = t2.attendance_date AND t1.id > t2.id",
                (),
            )
            n = db.execute_update(
                "ALTER TABLE attendance_records ADD UNIQUE KEY uk_employee_date (employee_id(100), attendance_date(20))",
                (),
            )
            if n < 0:
                logger.warning("添加 attendance_records 唯一约束失败，重复上传可能仍会重复录入，请检查 employee_id 列类型或手动执行脚本")
                return
            _attendance_unique_key_ensured = True
            logger.info("attendance_records 已确保唯一约束 uk_employee_date(employee_id, attendance_date)，重复上传将更新而非新增")
        except Exception as e:
            if "Duplicate key name" in str(e) or "already exists" in str(e).lower():
                _attendance_unique_key_ensured = True
            else:
                logger.warning(f"确保 attendance_records 唯一约束时出错（重复上传可能仍会重复录入）: {e}")

    def batch_insert_records(self, records: List[Dict]) -> tuple:
        """批量插入记录。整批单连接 + 多行 INSERT 分块提交，减少往返，加快上传。"""
        if not records:
            return 0, 0
        self._ensure_attendance_unique_key_once()
        chunk_size = 500  # 每 500 行一次 INSERT，平衡速度与单条 SQL 大小
        success_count = 0
        fail_count = 0
        conn = None
        try:
            conn = db.get_connection()
            if not conn:
                raise Exception("无法连接到数据库")
            with conn.cursor() as cursor:
                for i in range(0, len(records), chunk_size):
                    chunk = records[i : i + chunk_size]
                    placeholders = ", ".join(
                        ["(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"] * len(chunk)
                    )
                    sql = f"""
                        INSERT INTO attendance_records
                        (id, employee_id, employee_name, department, attendance_date,
                         time_1, time_2, time_3, time_4, time_5,
                         time_6, time_7, time_8, time_9, time_10)
                        VALUES {placeholders}
                        ON DUPLICATE KEY UPDATE
                        employee_name=VALUES(employee_name), department=VALUES(department),
                        time_1=VALUES(time_1), time_2=VALUES(time_2), time_3=VALUES(time_3),
                        time_4=VALUES(time_4), time_5=VALUES(time_5), time_6=VALUES(time_6),
                        time_7=VALUES(time_7), time_8=VALUES(time_8), time_9=VALUES(time_9),
                        time_10=VALUES(time_10), updated_at=CURRENT_TIMESTAMP
                    """
                    params = []
                    for record in chunk:
                        record_id = record.get("id") or uuid.uuid4().hex
                        params.extend((
                            record_id,
                            record['employee_id'], record['employee_name'], record['department'],
                            record['attendance_date'],
                            record.get('time_1'), record.get('time_2'), record.get('time_3'),
                            record.get('time_4'), record.get('time_5'), record.get('time_6'),
                            record.get('time_7'), record.get('time_8'), record.get('time_9'),
                            record.get('time_10')
                        ))
                    try:
                        cursor.execute(sql, tuple(params))
                        success_count += len(chunk)
                    except Exception as e:
                        logger.warning(f"分块插入失败（本块 {len(chunk)} 条）: {e}")
                        fail_count += len(chunk)
            if conn:
                conn.commit()
        except Exception as e:
            logger.error(f"批量插入失败: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            fail_count += len(records) - success_count
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return success_count, fail_count
    
    def query_by_name_and_dept(self, name: str, dept: str) -> List[Dict]:
        """根据姓名和部门查询记录"""
        try:
            sql = """
                SELECT * FROM attendance_records 
                WHERE employee_name = %s AND department = %s
                ORDER BY attendance_date DESC
            """
            return db.execute_query(sql, (name, dept))
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            return []
    
    def query_by_date_range(self, start_date: str, end_date: str, 
                           name: str = None, dept: str = None) -> List[Dict]:
        """根据日期范围查询记录"""
        try:
            sql = """
                SELECT * FROM attendance_records 
                WHERE attendance_date >= %s AND attendance_date <= %s
            """
            params = [start_date, end_date]
            
            if name:
                sql += " AND employee_name = %s"
                params.append(name)
            
            if dept:
                sql += " AND department = %s"
                params.append(dept)
            
            sql += " ORDER BY attendance_date DESC, employee_name"
            
            return db.execute_query(sql, tuple(params))
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            return []

    def get_all_records_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """按日期范围查询所有考勤记录（不按人筛选，用于考勤异常管理）"""
        try:
            sql = """
                SELECT * FROM attendance_records
                WHERE attendance_date >= %s AND attendance_date <= %s
                ORDER BY attendance_date DESC, employee_name
            """
            return db.execute_query(sql, (start_date, end_date))
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            return []
    
    def get_all_attendance_dates(self, name: str, dept: str) -> List[str]:
        """获取某个员工的所有打卡日期"""
        try:
            sql = """
                SELECT DISTINCT attendance_date 
                FROM attendance_records 
                WHERE employee_name = %s AND department = %s
                ORDER BY attendance_date
            """
            rows = db.execute_query(sql, (name, dept))
            
            # rows 是字典列表，需要提取日期并转为字符串
            dates = []
            for row in rows:
                date_val = row.get('attendance_date')
                if date_val:
                    # 如果是 date 对象，转字符串
                    dates.append(str(date_val))
            return dates
        except Exception as e:
            logger.error(f"查询日期失败: {str(e)}")
            return []
    
    def log_upload(self, filename: str, records_count: int, status: str, message: str = ""):
        """记录上传日志"""
        try:
            sql = """
                INSERT INTO upload_logs (filename, records_count, status, message)
                VALUES (%s, %s, %s, %s)
            """
            db.execute_update(sql, (filename, records_count, status, message))
        except Exception as e:
            logger.error(f"记录上传日志失败: {str(e)}")

    # ==================== 智能建议表 ====================

    def ensure_suggestions_table(self) -> bool:
        """确保 attendance_suggestions 表存在"""
        try:
            sql = """
                CREATE TABLE IF NOT EXISTS attendance_suggestions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    employee_name VARCHAR(100) NOT NULL,
                    department VARCHAR(200) NOT NULL,
                    year INT NOT NULL,
                    month INT NOT NULL,
                    day_type VARCHAR(50) DEFAULT NULL,
                    message TEXT NOT NULL,
                    start_time DATETIME(0) NULL DEFAULT NULL,
                    end_time DATETIME(0) NULL DEFAULT NULL,
                    status TINYINT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_lookup (employee_name(50), department(100), year, month)
                )
            """
            db.execute_update(sql, ())
            self._migrate_suggestions_table_if_needed()
            return True
        except Exception as e:
            logger.error(f"创建智能建议表失败: {str(e)}")
            return False

    def _migrate_suggestions_table_if_needed(self) -> None:
        """若表仍有 suggestion_date 或 start_time/end_time 为 VARCHAR，则迁移为无 suggestion_date、start/end 为 DATETIME(0)"""
        try:
            rows = db.execute_query(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'attendance_suggestions' AND COLUMN_NAME = 'suggestion_date'"
            )
            if not rows:
                return  # 已无 suggestion_date，无需迁移
            # 存在 suggestion_date：先加新列，迁移数据，再删旧列
            db.execute_update("ALTER TABLE attendance_suggestions ADD COLUMN start_time_new DATETIME(0) NULL", ())
            db.execute_update("ALTER TABLE attendance_suggestions ADD COLUMN end_time_new DATETIME(0) NULL", ())
            db.execute_update("""
                UPDATE attendance_suggestions
                SET start_time_new = CONCAT(suggestion_date, ' ', TRIM(COALESCE(start_time,'00:00')), CASE WHEN CHAR_LENGTH(TRIM(COALESCE(start_time,'00:00'))) = 5 THEN ':00' ELSE '' END),
                    end_time_new = CONCAT(suggestion_date, ' ', TRIM(COALESCE(end_time,'00:00:00')), CASE WHEN CHAR_LENGTH(TRIM(COALESCE(end_time,'00:00'))) = 5 THEN ':00' ELSE '' END)
                WHERE suggestion_date IS NOT NULL
            """, ())
            db.execute_update("ALTER TABLE attendance_suggestions DROP COLUMN suggestion_date", ())
            db.execute_update("ALTER TABLE attendance_suggestions DROP COLUMN start_time", ())
            db.execute_update("ALTER TABLE attendance_suggestions DROP COLUMN end_time", ())
            db.execute_update("ALTER TABLE attendance_suggestions CHANGE COLUMN start_time_new start_time DATETIME(0) NULL", ())
            db.execute_update("ALTER TABLE attendance_suggestions CHANGE COLUMN end_time_new end_time DATETIME(0) NULL", ())
        except Exception as e:
            logger.warning(f"attendance_suggestions 迁移跳过或失败: {e}")

    def delete_suggestions_for_month(self, employee_name: str, department: str, year: int, month: int) -> int:
        """删除指定人、指定年月的所有建议，返回删除行数"""
        try:
            sql = """
                DELETE FROM attendance_suggestions
                WHERE employee_name = %s AND department = %s AND year = %s AND month = %s
            """
            n = db.execute_update(sql, (employee_name, department, year, month))
            return n
        except Exception as e:
            logger.error(f"删除智能建议失败: {str(e)}")
            return 0

    def insert_suggestions(self, employee_name: str, department: str, year: int, month: int,
                           suggestions: List[Dict]) -> int:
        """批量插入智能建议。每项为 { date, dayType, suggestion/message, start_time, end_time, status }；start_time/end_time 须为完整 YYYY-MM-DD HH:MM:SS"""
        if not suggestions:
            return 0
        try:
            sql = """
                INSERT INTO attendance_suggestions
                (employee_name, department, year, month, day_type, message, start_time, end_time, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            count = 0
            for s in suggestions:
                msg = (s.get("suggestion") or s.get("message") or "").strip()
                if not msg:
                    continue
                start_t = s.get("start_time") or None
                end_t = s.get("end_time") or None
                if not start_t or not end_t:
                    continue
                status = s.get("status")
                if status is None:
                    status = 0
                day_type = s.get("dayType") or s.get("day_type") or ""
                db.execute_update(sql, (
                    employee_name, department, year, month, day_type, msg,
                    start_t, end_t, status
                ))
                count += 1
            return count
        except Exception as e:
            logger.error(f"插入智能建议失败: {str(e)}")
            return 0

    def get_suggestions(self, employee_name: str, department: str, year: int, month: int) -> List[Dict]:
        """按人、年月查询已存储的智能建议"""
        try:
            sql = """
                SELECT DATE(start_time) AS date, day_type AS dayType, message AS suggestion,
                       start_time AS start_time, end_time AS end_time, status AS status
                FROM attendance_suggestions
                WHERE employee_name = %s AND department = %s AND year = %s AND month = %s
                ORDER BY start_time, id
            """
            rows = db.execute_query(sql, (employee_name, department, year, month))
            return [
                {
                    "date": str(r.get("date") or ""),
                    "dayType": r.get("dayType") or "",
                    "suggestion": r.get("suggestion") or "",
                    "start_time": r.get("start_time"),
                    "end_time": r.get("end_time"),
                    "status": r.get("status") if r.get("status") is not None else 0,
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"查询智能建议失败: {str(e)}")
            return []

    def get_distinct_employees_for_suggestions(self, year: int, month: int) -> List[Dict]:
        """按年月从 attendance_suggestions 取不重复的 (employee_name, department)，用于考勤异常统计"""
        try:
            sql = """
                SELECT DISTINCT employee_name, department
                FROM attendance_suggestions
                WHERE year = %s AND month = %s
                ORDER BY department, employee_name
            """
            return db.execute_query(sql, (year, month))
        except Exception as e:
            logger.error(f"查询建议人员列表失败: {str(e)}")
            return []


# 创建全局数据库实例
attendance_db = AttendanceDatabase()
