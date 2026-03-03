"""
PostgreSQL 向量存储模块 - 使用 PGVector 扩展，支持用户过滤

使用统一 Collection 设计，通过 metadata 过滤实现多租户
"""
from langchain_postgres import PGVector

from .embeddings_model import get_embeddings_model
from ..config import settings


def get_pgvector_store(collection_name: str = None) -> PGVector:
    """
    获取 PostgreSQL 向量存储实例

    Args:
        collection_name: 集合名称（可选，默认使用配置中的 PGVECTOR_COLLECTION_NAME）

    Returns:
        PGVector 实例
    """
    # 使用连接字符串
    connection_string = settings.POSTGRESQL_URL
    # 如果未指定 collection_name，使用配置中的默认值
    if collection_name is None:
        collection_name = settings.PGVECTOR_COLLECTION_NAME

    return PGVector(
        embeddings=get_embeddings_model(),
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True,  # 使用 JSONB 存储元数据
    )


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
        search_kwargs={
            "k": k,
            "filter": {"user_id": user_id}
        }
    )