from ..config import settings
from typing import Optional

# 根据配置选择向量数据库
if settings.VECTOR_DB_TYPE == "postgresql":
    from .pgvector_store import get_pgvector_store as get_vector_store_impl
    from .pgvector_store import get_retriever as get_vector_retriever_impl
else:
    # 默认使用 Chroma
    from langchain_chroma import Chroma
    from .embeddings_model import get_embeddings_model

    def get_vector_store_impl(collection_name: str = None):
        if collection_name is None:
            collection_name = settings.CHROMA_COLLECTION_NAME
        return Chroma(
            embedding_function=get_embeddings_model(),
            persist_directory=str(settings.CHROMA_PERSIST_DIR),
            collection_name=collection_name
        )

    def get_vector_retriever_impl(k=4, user_id: Optional[str] = None):
        """获取 Chroma 检索器"""
        vector_store = Chroma(
            embedding_function=get_embeddings_model(),
            persist_directory=str(settings.CHROMA_PERSIST_DIR),
            collection_name=settings.CHROMA_COLLECTION_NAME
        )
        if user_id:
            return vector_store.as_retriever(
                search_kwargs={
                    "k": k,
                    "filter": {"user_id": user_id}
                }
            )
        else:
            return vector_store.as_retriever(search_kwargs={"k": k})


def get_vector_store(collection_name: str = None):
    """获取向量存储实例"""
    return get_vector_store_impl(collection_name)


def get_vector_retriever(k: int = 4, user_id: Optional[str] = None):
    """
    获取向量检索器（使用统一 Collection）

    Args:
        k: 返回的最相关文档数量
        user_id: 用户ID，用于过滤文档（可选）
    """
    return get_vector_retriever_impl(k=k, user_id=user_id)