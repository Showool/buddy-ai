from ..config import settings

# 根据配置选择向量数据库
if settings.VECTOR_DB_TYPE == "postgresql":
    from .pgvector_store import get_pgvector_store as get_vector_store_impl
else:
    # 默认使用 Chroma
    from langchain_chroma import Chroma
    from .embeddings_model import get_embeddings_model

    def get_vector_store_impl():
        return Chroma(
            embedding_function=get_embeddings_model(),
            persist_directory=str(settings.CHROMA_PERSIST_DIR),
        )


def get_vector_store():
    """获取向量存储实例"""
    return get_vector_store_impl()