import os
from ..config import settings

from .embeddings_model import get_embeddings_model

# 根据配置选择向量数据库
if settings.VECTOR_DB_TYPE == "postgresql":
    from .pgvector_store import get_pgvector_retriever as get_vector_retriever_impl
else:
    # 默认使用 Chroma
    from langchain_chroma import Chroma
    from langchain_chroma import Chroma

    def get_vector_retriever_impl(k=4):
        embeddings_model = get_embeddings_model()
        vectordb = Chroma(
            persist_directory=os.getenv("CHROMA_PERSIST_DIR"),
            embedding_function=embeddings_model
        )
        return vectordb.as_retriever(search_kwargs={"k": k})


def get_retriever(k: int = 4):
    """获取向量检索器"""
    return get_vector_retriever_impl(k=k)
