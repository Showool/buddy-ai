"""
Qwen Rerank 服务
"""
import logging
from typing import List, Optional
from dataclasses import dataclass

from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    documents: List[Document]
    scores: List[float]


class QwenRerankService:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY

    async def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: Optional[int] = None
    ) -> RerankResult:
        if not documents:
            return RerankResult(documents=[], scores=[])

        try:
            from dashscope import TextReRank

            texts = [doc.page_content for doc in documents]
            rerank_result = TextReRank.call(
                api_key=self.api_key,
                model="gte-rerank",
                query=query,
                documents=texts,
                top_n=top_k or len(documents)
            )

            if rerank_result.status_code == 200:
                results = rerank_result.output['results']
                reranked_docs = [documents[r['index']] for r in results]
                reranked_scores = [r['relevance_score'] for r in results]

                return RerankResult(
                    documents=reranked_docs,
                    scores=reranked_scores
                )
        except Exception as e:
            logger.error(f"Rerank 失败: {e}")

        return RerankResult(
            documents=documents[:top_k] if top_k else documents,
            scores=[1.0] * len(documents)
        )


qwen_rerank_service = QwenRerankService()