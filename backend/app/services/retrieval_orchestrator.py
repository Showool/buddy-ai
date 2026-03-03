"""
检索编排服务 - 整合向量检索、全文搜索、重排序
"""
import logging
import asyncio
from typing import List, Optional
from dataclasses import dataclass

from langchain_core.documents import Document

from app.config import settings
from app.retriever.embeddings_model import get_embeddings_model
from app.services.fulltext_search_service import fulltext_search_service
from app.services.qwen_rerank_service import qwen_rerank_service
from app.services.pgvector_singleton import pgvector_singleton

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    documents: List[Document]
    scores: List[float]
    sources: List[str]
    strategy: str = "hybrid"
    metadata: dict = None


class RetrievalOrchestrator:
    def __init__(self):
        self.reranker = qwen_rerank_service
        self.fulltext = fulltext_search_service
        self.collection_name = settings.PGVECTOR_COLLECTION_NAME  # 从配置获取

    async def retrieve(
        self,
        query: str,
        user_id: str,
        k: int = 4,
        use_fulltext: bool = True,
        use_rerank: bool = True,
        rerank_threshold: int = 3
    ) -> RetrievalResult:
        import time
        start_time = time.time()

        # 并行执行向量检索和全文搜索
        vector_result = self._retrieve_vector(query, user_id, k * 2)
        fulltext_result = self._retrieve_fulltext(query, user_id, k * 2)

        vector_r, fulltext_r = await asyncio.gather(
            vector_result,
            fulltext_result
        )

        # RRF 融合
        fused = self._rrf_fusion(
            vector_r.documents,
            vector_r.scores,
            fulltext_r.documents,
            fulltext_r.scores,
            k=k * 2
        )

        # Rerank（带触发阈值）
        if use_rerank and fused.documents and len(fused.documents) > rerank_threshold:
            reranked = await self.reranker.rerank(query, fused.documents, top_k=k)
            retrieval_time_ms = (time.time() - start_time) * 1000
            return RetrievalResult(
                documents=reranked.documents,
                scores=reranked.scores,
                sources=["rrf_reranked"] * len(reranked.documents),
                metadata={"rerank_triggered": True, "retrieval_time_ms": retrieval_time_ms}
            )
        else:
            retrieval_time_ms = (time.time() - start_time) * 1000
            return RetrievalResult(
                documents=fused.documents[:k],
                scores=fused.scores[:k],
                sources=["rrf_fused"] * len(fused.documents[:k]),
                metadata={"rerank_triggered": False, "retrieval_time_ms": retrieval_time_ms}
            )

    async def _retrieve_vector(
        self,
        query: str,
        user_id: str,
        k: int
    ) -> RetrievalResult:
        vector_store = await pgvector_singleton.get_vector_store()
        docs = await vector_store.asimilarity_search_with_score(
            query=query,
            k=k,
            filter={"user_id": user_id, "doc_type": "chunk"}
        )

        documents = [doc for doc, _ in docs]
        scores = [score for _, score in docs]

        return RetrievalResult(
            documents=documents,
            scores=scores,
            sources=["vector"] * len(documents)
        )

    async def _retrieve_fulltext(
        self,
        query: str,
        user_id: str,
        k: int
    ) -> RetrievalResult:
        result = await fulltext_search_service.search(query, user_id, k)
        return RetrievalResult(
            documents=result.documents,
            scores=result.scores,
            sources=["fulltext"] * len(result.documents)
        )

    def _rrf_fusion(
        self,
        docs1: List[Document],
        scores1: List[float],
        docs2: List[Document],
        scores2: List[float],
        k: int,
        rank_k: int = 60
    ) -> RetrievalResult:
        doc_scores = {}

        for i, doc in enumerate(docs1):
            doc_id = id(doc)
            rrf_score = 1.0 / (rank_k + i + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score

        for i, doc in enumerate(docs2):
            doc_id = id(doc)
            rrf_score = 1.0 / (rank_k + i + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score

        sorted_docs = sorted(
            [(doc, score) for doc, score in doc_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )

        all_docs = docs1 + docs2
        doc_map = {id(doc): doc for doc in all_docs}

        final_docs = []
        final_scores = []

        for doc_id, score in sorted_docs[:k]:
            if doc_id in doc_map:
                final_docs.append(doc_map[doc_id])
                final_scores.append(score)

        return RetrievalResult(
            documents=final_docs,
            scores=final_scores,
            sources=["rrf_fused"] * len(final_docs)
        )


retrieval_orchestrator = RetrievalOrchestrator()