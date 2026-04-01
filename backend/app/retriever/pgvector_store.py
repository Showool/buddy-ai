"""
PostgreSQL 向量存储模块 - 使用 PGVector 扩展，支持用户过滤

使用统一 Collection 设计，通过 metadata 过滤实现多租户
使用线程安全的单例模式避免重复创建连接
"""

import logging
import threading
from typing import Optional

from langchain_postgres import PGVector as LangchainPGVector

from .embeddings_model import get_embeddings_model
from ..config import settings

logger = logging.getLogger(__name__)

# 单例实例（线程安全）
_vector_store: Optional[LangchainPGVector] = None
_vector_store_lock = threading.Lock()


def get_pgvector_store() -> LangchainPGVector:
    """
    获取 PostgreSQL 向量存储实例（线程安全单例模式）

    Returns:
        PGVector 实例
    """
    global _vector_store

    if _vector_store is None:
        with _vector_store_lock:
            # 双重检查锁定
            if _vector_store is None:
                _vector_store = LangchainPGVector(
                    embeddings=get_embeddings_model(),
                    collection_name=settings.PGVECTOR_COLLECTION_NAME,
                    connection=settings.POSTGRESQL_URL,
                    use_jsonb=True,  # 使用 JSONB 存储元数据
                )
                logger.info("PGVector 实例创建成功（线程安全单例模式）")

    return _vector_store


def get_retriever(k: int = 4):
    """
    获取 PostgreSQL 向量检索器（使用统一 Collection）

    Args:
        k: 返回的最相关文档数量

    Returns:
        检索器实例
    """
    vector_store = get_pgvector_store()
    return vector_store.as_retriever(search_kwargs={"k": k})


def get_retriever_with_user_filter(user_id: str, k: int = 4):
    """
    获取带用户过滤的 PostgreSQL 向量检索器（使用统一 Collection）

    Args:
        user_id: 用户ID，用于过滤文档
        k: 返回的最相关文档数量

    Returns:
        带用户过滤的检索器实例
    """
    vector_store = get_pgvector_store()

    # PGVector 支持通过元数据过滤
    return vector_store.as_retriever(
        search_kwargs={"k": k, "filter": {"user_id": user_id}}
    )


def reset_vector_store():
    """
    重置向量存储实例（主要用于测试）
    """
    global _vector_store

    with _vector_store_lock:
        _vector_store = None
        logger.info("PGVector 实例已重置")
