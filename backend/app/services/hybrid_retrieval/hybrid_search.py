"""
混合检索服务 - 向量 + 全文搜索 + RRF 融合 + 降级处理 + 直接返回
"""

import logging
from typing import List, Optional
from dataclasses import dataclass
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from app.services.hybrid_retrieval.config import retrieval_config
from app.services.hybrid_retrieval.vector_search import vector_search, VectorResult
from app.services.hybrid_retrieval.fulltext_search import (
    fulltext_search,
    FulltextResult,
)

logger = logging.getLogger(__name__)


@dataclass
class RetrievalItem:
    """检索结果项"""

    doc_id: str
    content: str
    metadata: dict
    similarity: float
    source: str  # "vector" | "fulltext" | "hybrid"


class HybridRetrieval:
    """混合检索核心类 - 支持依赖注入"""

    def __init__(self, config=None, vector_searcher=None, fulltext_searcher=None):
        """
        初始化混合检索器

        Args:
            config: 检索配置 (默认使用 retrieval_config)
            vector_searcher: 向量搜索函数 (默认使用 vector_search)
            fulltext_searcher: 全文搜索函数 (默认使用 fulltext_search.search)
        """
        self.config = config or retrieval_config
        self.vector_searcher = vector_searcher or vector_search
        self.fulltext_searcher = fulltext_searcher or fulltext_search.search

    def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = None,
        min_similarity: float = None,
        search_mode: str = None,
    ) -> List[RetrievalItem]:
        """
        混合检索入口

        Args:
            query: 查询文本
            user_id: 用户ID
            top_k: 返回数量 (默认 4)
            min_similarity: 最小相似度 (默认 0.5)
            search_mode: 检索模式 (默认 hybrid)

        Returns:
            排序后的检索结果列表
        """
        top_k = top_k or self.config.vector_top_k
        min_similarity = min_similarity or self.config.vector_min_similarity
        search_mode = search_mode or self.config.search_mode

        logger.info(
            f"混合检索: query='{query[:30]}...', mode={search_mode}, top_k={top_k}"
        )

        # 根据模式选择检索策略
        if search_mode == "embedding":
            return self._vector_only(query, user_id, top_k, min_similarity)
        elif search_mode == "keywords":
            return self._fulltext_only(query, user_id, top_k)
        else:  # hybrid
            return self._hybrid_search(query, user_id, top_k, min_similarity)

    def _vector_only(
        self, query: str, user_id: str, top_k: int, min_similarity: float
    ) -> List[RetrievalItem]:
        """仅向量检索"""
        results = self.vector_searcher(query, user_id, top_k, min_similarity)

        return [
            RetrievalItem(
                doc_id=r.doc.metadata.get("chunk_id", ""),
                content=r.doc.page_content,
                metadata=r.doc.metadata,
                similarity=r.score,
                source="vector",
            )
            for r in results
        ]

    def _fulltext_only(
        self, query: str, user_id: str, top_k: int
    ) -> List[RetrievalItem]:
        """仅全文搜索"""
        results = self.fulltext_searcher(query, user_id, top_k)

        # 归一化分数到 0-1
        max_score = max((r.score for r in results), default=1.0)

        return [
            RetrievalItem(
                doc_id=r.doc_id,
                content=r.content,
                metadata=r.metadata,
                similarity=r.score / max_score if max_score > 0 else 0,
                source="fulltext",
            )
            for r in results
        ]

    def _hybrid_search(
        self, query: str, user_id: str, top_k: int, min_similarity: float
    ) -> List[RetrievalItem]:
        """混合检索 - RRF 融合（并行执行 + 降级处理 + 分数归一化统一）"""

        # ===== 并行执行向量和全文检索（带超时和降级） =====
        vector_results = []
        fulltext_results = []

        # 配置超时时间（秒）
        vector_timeout = self.config.vector_timeout
        fulltext_timeout = self.config.fulltext_timeout

        with ThreadPoolExecutor(max_workers=2) as executor:
            # 提交两个检索任务
            vec_future = executor.submit(
                self.vector_searcher, query, user_id, top_k * 2, min_similarity
            )
            ft_future = executor.submit(
                self.fulltext_searcher, query, user_id, top_k * 2
            )

            # ===== 向量检索异常处理 =====
            try:
                vector_results = vec_future.result(timeout=vector_timeout)
                logger.debug(f"向量检索成功，返回 {len(vector_results)} 个结果")
            except TimeoutError:
                logger.warning(f"向量检索超时（>{vector_timeout}秒），使用空结果降级")
                vector_results = []
            except Exception as e:
                logger.error(f"向量检索失败: {e}，使用空结果降级")
                vector_results = []

            # ===== 全文检索异常处理 =====
            try:
                fulltext_results = ft_future.result(timeout=fulltext_timeout)
                logger.debug(f"全文检索成功，返回 {len(fulltext_results)} 个结果")
            except TimeoutError:
                logger.warning(f"全文检索超时（>{fulltext_timeout}秒），使用空结果降级")
                fulltext_results = []
            except Exception as e:
                logger.error(f"全文检索失败: {e}，使用空结果降级")
                fulltext_results = []

        # ===== 记录降级状态 =====
        retrieval_status = []
        if not vector_results:
            retrieval_status.append("vector_degraded")
        if not fulltext_results:
            retrieval_status.append("fulltext_degraded")

        if retrieval_status:
            logger.warning(f"混合检索降级模式: {', '.join(retrieval_status)}")

        # ===== 空结果处理：单边检索 =====
        # 如果向量检索失败，使用全文检索结果
        if not vector_results and fulltext_results:
            logger.info("降级模式：仅使用全文检索结果")
            return self._fulltext_only(query, user_id, top_k)

        # 如果全文检索失败，使用向量检索结果
        if not fulltext_results and vector_results:
            logger.info("降级模式：仅使用向量检索结果")
            return self._vector_only(query, user_id, top_k, min_similarity)

        # 如果两者都失败，返回空结果
        if not vector_results and not fulltext_results:
            logger.error("向量和全文检索均失败，返回空结果")
            return []

        # ===== 分数归一化 =====
        # 归一化向量分数到 0-1 范围
        max_vec_score = max((r.score for r in vector_results), default=1.0)
        normalized_vector_results = []
        for r in vector_results:
            norm_score = r.score / max_vec_score if max_vec_score > 0 else 0
            normalized_vector_results.append((r, norm_score))

        # 归一化全文分数到 0-1 范围
        max_ft_score = max((r.score for r in fulltext_results), default=1.0)
        normalized_fulltext_results = []
        for r in fulltext_results:
            norm_score = r.score / max_ft_score if max_ft_score > 0 else 0
            normalized_fulltext_results.append((r, norm_score))

        # ===== RRF 融合 =====
        doc_scores = defaultdict(float)
        doc_contents = {}
        doc_metadatas = {}

        rrf_k = self.config.rrf_k

        # 向量结果 RRF（使用归一化分数）
        for i, (r, norm_score) in enumerate(normalized_vector_results):
            rrf_score = norm_score * (1.0 / (rrf_k + i + 1))
            doc_id = r.doc.metadata.get("chunk_id", str(i))
            doc_scores[doc_id] += rrf_score
            doc_contents[doc_id] = r.doc.page_content
            doc_metadatas[doc_id] = r.doc.metadata

        # 全文结果 RRF（使用归一化分数）
        for i, (r, norm_score) in enumerate(normalized_fulltext_results):
            rrf_score = norm_score * (1.0 / (rrf_k + i + 1))
            doc_scores[r.doc_id] += rrf_score
            if r.doc_id not in doc_contents:
                doc_contents[r.doc_id] = r.content
                doc_metadatas[r.doc_id] = r.metadata

        # 排序并返回 top_k
        sorted_items = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for doc_id, score in sorted_items[:top_k]:
            results.append(
                RetrievalItem(
                    doc_id=doc_id,
                    content=doc_contents[doc_id],
                    metadata=doc_metadatas[doc_id],
                    similarity=score,
                    source="hybrid",
                )
            )

        logger.info(f"混合检索: 返回 {len(results)} 个结果")
        return results

    def should_direct_return(self, results: List[RetrievalItem]) -> Optional[str]:
        """
        检查是否可以直接返回 (高相似度跳过 LLM)

        Returns:
            如果可以直接返回，返回内容；否则返回 None
        """
        if not self.config.direct_return_enabled:
            return None

        if results and results[0].similarity >= self.config.direct_return_threshold:
            logger.info(
                f"直接返回: doc_id={results[0].doc_id}, similarity={results[0].similarity:.2f}"
            )
            return results[0].content

        return None


# 全局实例
hybrid_retrieval = HybridRetrieval()
