"""
PostgreSQL 向量存储模块 - 使用 PGVector 扩展
"""
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector

from .embeddings_model import get_embeddings_model
from ..config import settings


def get_pgvector_store(collection_name: str = None) -> PGVector:
    """
    获取 PostgreSQL 向量存储实例

    Args:
        collection_name: 集合名称（表名）

    Returns:
        PGVector 实例
    """
    if collection_name is None:
        collection_name = settings.PGVECTOR_COLLECTION_NAME

    # 使用连接字符串
    connection_string = settings.POSTGRESQL_URL

    return PGVector(
        embeddings=get_embeddings_model(),
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True,  # 使用 JSONB 存储元数据
    )


def get_pgvector_retriever(collection_name: str = None, k: int = 4):
    """
    获取 PostgreSQL 向量检索器

    Args:
        collection_name: 集合名称
        k: 返回的最相关文档数量

    Returns:
        检索器实例
    """
    vector_store = get_pgvector_store(collection_name)
    return vector_store.as_retriever(search_kwargs={"k": k})