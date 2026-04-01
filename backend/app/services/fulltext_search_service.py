"""
PostgreSQL 全文搜索服务 - 同步版本
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class FulltextResult:
    documents: List[Document]
    scores: List[float]


class FulltextSearchService:
    def __init__(self):
        self._connection: Optional[psycopg2.extensions.connection] = None

    def _get_connection(self) -> psycopg2.extensions.connection:
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(
                settings.POSTGRESQL_URL, cursor_factory=RealDictCursor
            )
        return self._connection

    def search(self, query: str, user_id: str, k: int = 5) -> FulltextResult:
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            sql = """
                SELECT
                    e.document,
                    e.cmetadata,
                    ts_rank(e.search_vector, plainto_tsquery('simple', %s)) as score
                FROM langchain_pg_embedding e
                WHERE e.search_vector IS NOT NULL
                  AND e.collection_id = (
                      SELECT uuid FROM langchain_pg_collection
                      WHERE name = %s
                  )
                  AND (e.cmetadata->>'user_id') = %s
                  AND (e.cmetadata->>'doc_type') = 'chunk'
                ORDER BY score DESC
                LIMIT %s
            """

            cursor.execute(sql, (query, settings.PGVECTOR_COLLECTION_NAME, user_id, k))
            rows = cursor.fetchall()

            documents = []
            scores = []

            for row in rows:
                documents.append(
                    Document(page_content=row["document"], metadata=row["cmetadata"])
                )
                scores.append(float(row["score"]))

            if documents:
                logger.info(f"全文搜索成功: 返回 {len(documents)} 个文档")
            else:
                logger.warning(
                    f"全文搜索未找到结果: query='{query}', user_id={user_id}"
                )

            return FulltextResult(documents=documents, scores=scores)
        finally:
            cursor.close()


fulltext_search_service = FulltextSearchService()
