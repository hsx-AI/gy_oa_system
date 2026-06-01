# -*- coding: utf-8 -*-
"""
数据库连接模块 - MySQL 版本，带连接池以缓解 Windows 下短时间大量建连导致 WinError 10048
"""
import pymysql
import threading
from config import settings
from typing import Optional, List, Dict, Any
import logging
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    def __init__(self, database: Optional[str] = None):
        """
        :param database: 库名；不传则使用 settings.MYSQL_DB（主 OA 库）
        """
        self.host = settings.MYSQL_HOST
        self.port = settings.MYSQL_PORT
        self.user = settings.MYSQL_USER
        self.password = settings.MYSQL_PASSWORD
        self.db_name = database if database is not None else settings.MYSQL_DB
        self.charset = 'utf8mb4'
        self._pool: List[pymysql.Connection] = []
        self._lock = threading.Lock()
        self.pool_size = max(1, int(getattr(settings, "MYSQL_POOL_SIZE", 10) or 10))
        self.acquire_timeout = max(0.1, float(getattr(settings, "MYSQL_POOL_ACQUIRE_TIMEOUT", 3.0) or 3.0))
        self.slow_query_ms = max(0, int(getattr(settings, "MYSQL_SLOW_QUERY_MS", 800) or 0))
        self._sem = threading.Semaphore(self.pool_size)

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
                connect_timeout=getattr(settings, "MYSQL_CONNECT_TIMEOUT", 5),
                read_timeout=getattr(settings, "MYSQL_READ_TIMEOUT", 30),
                write_timeout=getattr(settings, "MYSQL_WRITE_TIMEOUT", 30),
                autocommit=False,
            )
        except Exception as e:
            logger.error(f"数据库连接失败 [{self.db_name}]: {str(e)}")
            return None

    def _put_back(self, conn: pymysql.Connection):
        with self._lock:
            if len(self._pool) < self.pool_size:
                self._pool.append(conn)
            else:
                try:
                    conn.close()
                except Exception:
                    pass
        self._sem.release()

    def _ping_or_discard(self, conn: pymysql.Connection) -> Optional[pymysql.Connection]:
        """检测池中取出的连接是否仍然存活，断开则丢弃并返回 None"""
        try:
            conn.ping(reconnect=True)
            return conn
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return None

    def get_connection(self) -> Optional[Any]:
        """从池中获取连接或新建（受配置的 pool_size 限制，避免连接数失控）"""
        acquired = self._sem.acquire(timeout=self.acquire_timeout)
        if not acquired:
            logger.error(
                "获取数据库连接超时 [%s]: pool_size=%s, wait=%.1fs",
                self.db_name,
                self.pool_size,
                self.acquire_timeout,
            )
            return None
        try:
            conn = None
            with self._lock:
                while self._pool:
                    candidate = self._pool.pop()
                    alive = self._ping_or_discard(candidate)
                    if alive is not None:
                        conn = alive
                        break
            if conn is None:
                conn = self._create_conn()
            if conn is None:
                self._sem.release()
                return None
            return _PooledConnection(conn, lambda: self)
        except Exception as e:
            logger.error(f"获取连接失败: {str(e)}")
            self._sem.release()
            return None

    def _log_slow_query(self, elapsed_ms: float, sql: str, params: Any = None) -> None:
        if not self.slow_query_ms or elapsed_ms < self.slow_query_ms:
            return
        compact_sql = " ".join((sql or "").split())
        if len(compact_sql) > 800:
            compact_sql = compact_sql[:800] + "..."
        logger.warning(
            "慢 SQL [%s] %.0f ms: %s | Params: %s",
            self.db_name,
            elapsed_ms,
            compact_sql,
            params,
        )
    
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询并返回字典列表"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                raise Exception("无法连接到数据库")
            
            with conn.cursor() as cursor:
                start = time.monotonic()
                cursor.execute(sql, params)
                result = cursor.fetchall()
                self._log_slow_query((time.monotonic() - start) * 1000, sql, params)
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
                start = time.monotonic()
                cursor.execute(sql, params)
                row = cursor.fetchone()
                self._log_slow_query((time.monotonic() - start) * 1000, sql, params)
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
                start = time.monotonic()
                cursor.execute(sql, params)
                affected_rows = cursor.rowcount
                self._log_slow_query((time.monotonic() - start) * 1000, sql, params)
            
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

    def execute_many(self, sql: str, params_list: list) -> int:
        """批量执行 INSERT/UPDATE/DELETE，一次连接提交多行，返回受影响总行数。

        使用逐条 execute 而非 PyMySQL executemany：executemany 对
        INSERT ... VALUES (...) ON DUPLICATE KEY UPDATE ... 只会用 VALUES 段占位符数量
        去格式化整条参数元组，导致占位符与参数个数不一致而报错。
        """
        if not params_list:
            return 0
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                raise Exception("无法连接到数据库")
            affected = 0
            with conn.cursor() as cursor:
                start = time.monotonic()
                for params in params_list:
                    cursor.execute(sql, params)
                    rc = cursor.rowcount
                    if rc is not None and rc >= 0:
                        affected += rc
                self._log_slow_query((time.monotonic() - start) * 1000, sql, f"{len(params_list)} rows")
            conn.commit()
            return affected
        except Exception as e:
            logger.error(f"批量执行失败: {str(e)}")
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
                start = time.monotonic()
                cursor.execute(sql, params)
                last_id = cursor.lastrowid
                self._log_slow_query((time.monotonic() - start) * 1000, sql, params)
            
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


# 创建全局数据库实例（主库 + demo 库，同主机/端口/账号/密码）
db = MySQLDatabase()
db_demo = MySQLDatabase(settings.MYSQL_DB_DEMO)
