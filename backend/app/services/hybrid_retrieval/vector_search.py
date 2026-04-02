"""
向量检索服务 - 基于 LangChain PGVector，添加缓存和相似度过滤
"""

import logging
from typing import List
from dataclasses import dataclass
from langchain_core.documents import Document

from app.retriever.pgvector_store import get_pgvector_store

logger = logging.getLogger(__name__)


@dataclass
class VectorResult:
    """向量检索结果"""

    doc: Document
    score: float


def vector_search(
    query: str, user_id: str, top_k: int = 4, min_similarity: float = 0.0
) -> List[VectorResult]:
    """
    向量相似度搜索（带缓存）

    Args:
        query: 查询文本
        user_id: 用户ID
        top_k: 返回数量
        min_similarity: 最小相似度 (0-1)

    Returns:
        检索结果列表，包含文档和相似度分数
    """

    vector_store = get_pgvector_store()

    # 使用 filter 过滤用户和文档类型
    filter_dict = {
        "$and": [{"user_id": {"$eq": user_id}}, {"doc_type": {"$eq": "chunk"}}]
    }
    # 执行相似度搜索 (带分数)
    results_with_scores = vector_store.similarity_search_with_score(
        query=query,
        k=top_k * 2,  # 获取更多结果用于过滤
        filter=filter_dict,
    )

    # 过滤相似度低于阈值的結果
    filtered_results = []
    for doc, score in results_with_scores:
        # LangChain PGVector 返回的 score 是距离，需要转换为相似度
        similarity = 1 - score

        if similarity >= min_similarity:
            filtered_results.append(VectorResult(doc=doc, score=similarity))

            if len(filtered_results) >= top_k:
                break

    logger.info(
        f"向量检索: query='{query[:30]}...', 返回 {len(filtered_results)} 个结果"
    )

    return filtered_results
