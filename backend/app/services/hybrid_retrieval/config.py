"""
检索配置 - 统一管理 RAG 检索参数
"""

from typing import Literal

from pydantic import BaseModel

from app.config import settings


class RetrievalConfig(BaseModel):
    """检索配置 - 从 settings 读取"""

    # 向量检索
    vector_top_k: int = settings.RAG_VECTOR_TOP_K
    vector_min_similarity: float = settings.RAG_MIN_SIMILARITY

    # 全文搜索
    fulltext_top_k: int = settings.RAG_VECTOR_TOP_K

    # 混合检索模式: embedding / keywords / hybrid
    search_mode: Literal["embedding", "keywords", "hybrid"] = settings.RAG_SEARCH_MODE

    # RRF 融合参数
    rrf_k: int = settings.RAG_RRF_K

    # 直接返回 (高相似度跳过 LLM)
    direct_return_enabled: bool = True
    direct_return_threshold: float = settings.RAG_DIRECT_RETURN_THRESHOLD

    # 向量库配置 (从现有配置读取)
    collection_name: str = settings.PGVECTOR_COLLECTION_NAME
    embedding_dimensions: int = settings.EMBEDDING_DIMENSIONS

    # 并行执行超时配置
    vector_timeout: float = settings.RAG_VECTOR_TIMEOUT
    fulltext_timeout: float = settings.RAG_FULLTEXT_TIMEOUT


# 全局配置实例
retrieval_config = RetrievalConfig()
