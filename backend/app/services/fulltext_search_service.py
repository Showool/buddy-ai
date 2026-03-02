"""
PostgreSQL 全文搜索服务
"""
import logging
from typing import List
from dataclasses import dataclass

import asyncpg
from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class FulltextResult:
    documents: List[Document]
    scores: List[float]


class FulltextSearchService:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                settings.POSTGRESQL_URL,
                min_size=2,
                max_size=10
            )
        return self._pool

    async def search(
        self,
        query: str,
        user_id: str,
        k: int = 5
    ) -> FulltextResult:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            sql = """
                SELECT
                    e.document,
                    e.cmetadata,
                    ts_rank(e.search_vector, plainto_tsquery('simple', $1)) as score
                FROM langchain_pg_embedding e
                WHERE e.search_vector IS NOT NULL
                  AND (e.cmetadata->>'user_id') = $2
                ORDER BY score DESC
                LIMIT $3
            """

            rows = await conn.fetch(sql, query, user_id, k)

            documents = []
            scores = []

            for row in rows:
                documents.append(Document(
                    page_content=row['document'],
                    metadata=row['cmetadata']
                ))
                scores.append(float(row['score']))

            return FulltextResult(documents=documents, scores=scores)


fulltext_search_service = FulltextSearchService()