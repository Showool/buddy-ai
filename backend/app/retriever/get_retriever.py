import os
from typing import Optional
from ..config import settings

from .embeddings_model import get_embeddings_model
import logging

logger = logging.getLogger(__name__)

# 根据配置选择向量数据库
if settings.VECTOR_DB_TYPE == "postgresql":
    from .pgvector_store import get_retriever as get_vector_retriever_impl
    from .pgvector_store import get_retriever_with_user_filter as get_vector_retriever_with_user_filter_impl
else:
    # 默认使用 Chroma
    from langchain_chroma import Chroma

    def get_vector_retriever_impl(k=4):
        """获取 Chroma 检索器"""
        embeddings_model = get_embeddings_model()
        vectordb = Chroma(
            persist_directory=os.getenv("CHROMA_PERSIST_DIR"),
            embedding_function=embeddings_model,
            collection_name=os.getenv("CHROMA_COLLECTION_NAME", "buddy_ai_knowledge")
        )
        return vectordb.as_retriever(search_kwargs={"k": k})

    def get_vector_retriever_with_user_filter_impl(user_id: str, k=4):
        """获取带用户过滤的 Chroma 检索器"""
        embeddings_model = get_embeddings_model()
        vectordb = Chroma(
            persist_directory=os.getenv("CHROMA_PERSIST_DIR"),
            embedding_function=embeddings_model,
            collection_name=os.getenv("CHROMA_COLLECTION_NAME", "buddy_ai_knowledge")
        )
        return vectordb.as_retriever(
            search_kwargs={
                "k": k,
                "filter": {"user_id": user_id}
            }
        )


def get_retriever(k: int = 4):
    """
    获取向量检索器（使用统一 Collection）

    Args:
        k: 返回的最相关文档数量
    """
    return get_vector_retriever_impl(k=k)


def get_retriever_with_user_filter(user_id: Optional[str] = None, k: int = 4):
    """
    获取带用户过滤的向量检索器（使用统一 Collection）

    Args:
        user_id: 用户ID，用于过滤文档
        k: 返回的最相关文档数量

    Returns:
        检索器实例
    """
    if user_id:
        return get_vector_retriever_with_user_filter_impl(user_id, k=k)
    else:
        return get_vector_retriever_impl(k=k)