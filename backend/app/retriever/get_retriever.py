"""
向量检索器 - 使用 PostgreSQL+pgvector
"""
from typing import Optional
from ..config import settings

from .embeddings_model import get_embeddings_model
import logging

logger = logging.getLogger(__name__)

# 使用 pgvector_store 的检索器
from .pgvector_store import get_retriever as get_pgvector_retriever
from .pgvector_store import get_retriever_with_user_filter as get_pgvector_retriever_with_user_filter


def get_retriever(k: int = 4):
    """
    获取向量检索器

    Args:
        k: 返回的最相关文档数量
    """
    return get_pgvector_retriever(k=k)


def get_retriever_with_user_filter(user_id: Optional[str] = None, k: int = 4):
    """
    获取带用户过滤的向量检索器

    Args:
        user_id: 用户ID，用于过滤文档
        k: 返回的最相关文档数量

    Returns:
        检索器实例
    """
    if user_id:
        return get_pgvector_retriever_with_user_filter(user_id, k=k)
    else:
        return get_pgvector_retriever(k=k)