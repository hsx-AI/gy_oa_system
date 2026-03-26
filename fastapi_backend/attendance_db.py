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
            sql = """
                INSERT INTO attendance_records 
                (id, employee_id, employee_name, department, attendance_date,
                 time_1, time_1_mark, time_2, time_2_mark, time_3, time_3_mark,
                 time_4, time_4_mark, time_5, time_5_mark,
                 time_6, time_6_mark, time_7, time_7_mark, time_8, time_8_mark,
                 time_9, time_9_mark, time_10, time_10_mark)
                VALUES (%s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                employee_name=VALUES(employee_name), department=VALUES(department),
                time_1=VALUES(time_1), time_1_mark=VALUES(time_1_mark),
                time_2=VALUES(time_2), time_2_mark=VALUES(time_2_mark),
                time_3=VALUES(time_3), time_3_mark=VALUES(time_3_mark),
                time_4=VALUES(time_4), time_4_mark=VALUES(time_4_mark),
                time_5=VALUES(time_5), time_5_mark=VALUES(time_5_mark),
                time_6=VALUES(time_6), time_6_mark=VALUES(time_6_mark),
                time_7=VALUES(time_7), time_7_mark=VALUES(time_7_mark),
                time_8=VALUES(time_8), time_8_mark=VALUES(time_8_mark),
                time_9=VALUES(time_9), time_9_mark=VALUES(time_9_mark),
                time_10=VALUES(time_10), time_10_mark=VALUES(time_10_mark),
                updated_at=CURRENT_TIMESTAMP
            """
            params = (
                record_id,
                record['employee_id'], record['employee_name'], record['department'],
                record['attendance_date'],
                record.get('time_1'), record.get('time_1_mark'),
                record.get('time_2'), record.get('time_2_mark'),
                record.get('time_3'), record.get('time_3_mark'),
                record.get('time_4'), record.get('time_4_mark'),
                record.get('time_5'), record.get('time_5_mark'),
                record.get('time_6'), record.get('time_6_mark'),
                record.get('time_7'), record.get('time_7_mark'),
                record.get('time_8'), record.get('time_8_mark'),
                record.get('time_9'), record.get('time_9_mark'),
                record.get('time_10'), record.get('time_10_mark'),
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

    _UPSERT_COLUMNS = (
        "id, employee_id, employee_name, department, attendance_date, "
        "time_1, time_1_mark, time_2, time_2_mark, time_3, time_3_mark, "
        "time_4, time_4_mark, time_5, time_5_mark, "
        "time_6, time_6_mark, time_7, time_7_mark, time_8, time_8_mark, "
        "time_9, time_9_mark, time_10, time_10_mark"
    )
    _UPSERT_PH = ", ".join(["%s"] * 25)
    _UPSERT_ON_DUP = (
        "employee_name=VALUES(employee_name), department=VALUES(department), "
        + ", ".join(
            f"time_{i}=VALUES(time_{i}), time_{i}_mark=VALUES(time_{i}_mark)"
            for i in range(1, 11)
        )
        + ", updated_at=CURRENT_TIMESTAMP"
    )

    def _build_single_upsert_sql(self):
        return (
            f"INSERT INTO attendance_records ({self._UPSERT_COLUMNS}) "
            f"VALUES ({self._UPSERT_PH}) "
            f"ON DUPLICATE KEY UPDATE {self._UPSERT_ON_DUP}"
        )

    @staticmethod
    def _record_to_params(record: Dict) -> tuple:
        record_id = record.get("id") or uuid.uuid4().hex
        parts = [
            record_id,
            record['employee_id'], record['employee_name'], record['department'],
            record['attendance_date'],
        ]
        for i in range(1, 11):
            parts.append(record.get(f'time_{i}'))
            parts.append(record.get(f'time_{i}_mark'))
        return tuple(parts)

    def batch_insert_records(self, records: List[Dict]) -> tuple:
        """批量插入记录。分块批量 INSERT，失败的块降级逐条重试，避免一条坏数据丢掉整块。"""
        if not records:
            return 0, 0
        self._ensure_attendance_unique_key_once()
        chunk_size = 500
        success_count = 0
        fail_count = 0
        single_sql = self._build_single_upsert_sql()
        conn = None
        try:
            conn = db.get_connection()
            if not conn:
                raise Exception("无法连接到数据库")
            with conn.cursor() as cursor:
                for i in range(0, len(records), chunk_size):
                    chunk = records[i : i + chunk_size]
                    placeholders = ", ".join(
                        [f"({self._UPSERT_PH})"] * len(chunk)
                    )
                    bulk_sql = (
                        f"INSERT INTO attendance_records ({self._UPSERT_COLUMNS}) "
                        f"VALUES {placeholders} "
                        f"ON DUPLICATE KEY UPDATE {self._UPSERT_ON_DUP}"
                    )
                    params = []
                    for record in chunk:
                        params.extend(self._record_to_params(record))
                    try:
                        cursor.execute(bulk_sql, tuple(params))
                        success_count += len(chunk)
                    except Exception as e:
                        logger.warning(f"分块插入失败（本块 {len(chunk)} 条），降级逐条重试: {e}")
                        for j, record in enumerate(chunk):
                            try:
                                cursor.execute(single_sql, self._record_to_params(record))
                                success_count += 1
                            except Exception as e2:
                                fail_count += 1
                                logger.warning(
                                    f"  逐条插入失败 employee_id={record.get('employee_id')} "
                                    f"date={record.get('attendance_date')}: {e2}"
                                )
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

    def delete_suggestions_batch(self, keys: list) -> int:
        """批量删除多个人月组合的建议。keys: [(name, dept, year, month), ...]"""
        if not keys:
            return 0
        try:
            conditions = " OR ".join(
                ["(employee_name = %s AND department = %s AND year = %s AND month = %s)"] * len(keys)
            )
            sql = f"DELETE FROM attendance_suggestions WHERE {conditions}"
            params = []
            for k in keys:
                params.extend(k)
            n = db.execute_update(sql, tuple(params))
            return n
        except Exception as e:
            logger.error(f"批量删除智能建议失败: {str(e)}")
            return 0

    def insert_suggestions(self, employee_name: str, department: str, year: int, month: int,
                           suggestions: List[Dict]) -> int:
        """批量插入智能建议（使用 executemany 一次提交）"""
        if not suggestions:
            return 0
        try:
            sql = """
                INSERT INTO attendance_suggestions
                (employee_name, department, year, month, day_type, message, start_time, end_time, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            rows = []
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
                rows.append((
                    employee_name, department, year, month, day_type, msg,
                    start_t, end_t, status
                ))
            if not rows:
                return 0
            result = db.execute_many(sql, rows)
            return result if result >= 0 else 0
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
