"""
数据库连接池 + 缓存模块 - 统一管理 PostgreSQL 连接和查询缓存

提供线程安全的连接池和查询缓存功能
"""

import logging
import threading
from functools import lru_cache
from typing import Optional, List

from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from app.config import settings

logger = logging.getLogger(__name__)

# ============== 数据库连接池 ==============
_connection_pool: Optional[pool.ThreadedConnectionPool] = None
_connection_pool_lock = threading.Lock()


def get_db_pool() -> pool.ThreadedConnectionPool:
    """获取数据库连接池（线程安全单例模式）"""
    global _connection_pool

    if _connection_pool is None:
        with _connection_pool_lock:
            if _connection_pool is None:
                _connection_pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=settings.POSTGRESQL_URL,
                    cursor_factory=RealDictCursor,
                )
                logger.info("数据库连接池创建成功")

    return _connection_pool


def get_conn():
    """从连接池获取连接"""
    return get_db_pool().getconn()


def return_conn(conn):
    """归还连接到连接池"""
    get_db_pool().putconn(conn)



# ============== 分词缓存 ==============
@lru_cache(maxsize=5000)
def _to_query_cached(text: str) -> str:
    """带缓存的 jieba 分词（用于查询）"""
    import jieba

    words = jieba.lcut(text, cut_all=True)
    return " ".join(words)


# ============== 全文搜索工具函数 ==============
def to_ts_vector(text: str) -> str:
    """
    使用 jieba 分词生成 tsvector (用于索引)

    Args:
        text: 原始文本

    Returns:
        分词后的文本字符串
    """
    import jieba

    words = jieba.lcut(text, cut_all=True)
    return " ".join(words)


def to_query(text: str) -> str:
    """
    使用 jieba 分词生成查询 (用于搜索)
    带缓存以提升性能

    Args:
        text: 查询文本

    Returns:
        分词后的文本字符串
    """
    return _to_query_cached(text)
