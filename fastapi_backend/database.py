# -*- coding: utf-8 -*-
"""
数据库连接模块 - MySQL 版本，带连接池以缓解 Windows 下短时间大量建连导致 WinError 10048
"""
import pymysql
import threading
from config import settings
from typing import Optional, List, Dict, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 连接池大小，限制并发连接数，避免端口耗尽
POOL_SIZE = 5


class _PooledConnection:
    """包装连接，close 时归还连接池而非真正关闭"""
    __slots__ = ("_conn", "_pool_ref", "_closed")

    def __init__(self, conn, pool_ref):
        self._conn = conn
        self._pool_ref = pool_ref
        self._closed = False

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._conn.rollback()
        except Exception:
            pass
        pool = self._pool_ref()
        if pool is not None:
            pool._put_back(self._conn)

    def __getattr__(self, name):
        return getattr(self._conn, name)


class MySQLDatabase:
    """MySQL数据库连接类（带连接池）"""
    
    def __init__(self):
        self.host = settings.MYSQL_HOST
        self.port = settings.MYSQL_PORT
        self.user = settings.MYSQL_USER
        self.password = settings.MYSQL_PASSWORD
        self.db_name = settings.MYSQL_DB
        self.charset = 'utf8mb4'
        self._pool: List[pymysql.Connection] = []
        self._lock = threading.Lock()
        self._sem = threading.Semaphore(POOL_SIZE)

    def _create_conn(self) -> Optional[pymysql.Connection]:
        try:
            return pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.db_name,
                charset=self.charset,
                cursorclass=pymysql.cursors.DictCursor,
            )
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            return None

    def _put_back(self, conn: pymysql.Connection):
        with self._lock:
            if len(self._pool) < POOL_SIZE:
                self._pool.append(conn)
            else:
                try:
                    conn.close()
                except Exception:
                    pass
        self._sem.release()

    def get_connection(self) -> Optional[Any]:
        """从池中获取连接或新建（受 POOL_SIZE 限制，避免 WinError 10048）"""
        self._sem.acquire()
        try:
            with self._lock:
                if self._pool:
                    conn = self._pool.pop()
                else:
                    conn = self._create_conn()
            if conn is None:
                self._sem.release()
                return None
            return _PooledConnection(conn, lambda: self)
        except Exception as e:
            logger.error(f"获取连接失败: {str(e)}")
            self._sem.release()
            return None
    
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询并返回字典列表"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                raise Exception("无法连接到数据库")
            
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchall()
                return result
        except Exception as e:
            logger.error(f"查询执行失败: {str(e)}\nSQL: {sql}\nParams: {params}")
            return []
        finally:
            if conn:
                conn.close()
    
    def execute_scalar(self, sql: str, params: tuple = None) -> Any:
        """执行查询并返回单个值"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                raise Exception("无法连接到数据库")
            
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
                if row:
                    # 返回字典中的第一个值
                    return list(row.values())[0]
                return None
        except Exception as e:
            logger.error(f"查询执行失败: {str(e)}")
            return None
        finally:
            if conn:
                conn.close()

    def execute_update(self, sql: str, params: tuple = None) -> int:
        """执行更新/插入/删除操作，返回受影响行数"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                raise Exception("无法连接到数据库")
            
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                affected_rows = cursor.rowcount
            
            conn.commit()
            return affected_rows
        except Exception as e:
            logger.error(f"更新执行失败: {str(e)}")
            if conn:
                conn.rollback()
            return -1
        finally:
            if conn:
                conn.close()

    def execute_insert(self, sql: str, params: tuple = None) -> Optional[int]:
        """执行插入操作，返回新插入行的ID"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                raise Exception("无法连接到数据库")
            
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                last_id = cursor.lastrowid
            
            conn.commit()
            return last_id
        except Exception as e:
            logger.error(f"插入执行失败: {str(e)}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()


# 创建全局数据库实例
db = MySQLDatabase()
