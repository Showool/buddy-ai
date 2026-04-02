"""
全文搜索服务 - 使用 jieba 分词 + websearch_to_tsquery + 连接池
"""

import logging
from dataclasses import dataclass

from app.config import settings
from app.services.db_pool import get_conn, return_conn

logger = logging.getLogger(__name__)


@dataclass
class FulltextResult:
    """全文搜索结果"""

    doc_id: str
    content: str
    metadata: dict
    score: float


class FulltextSearch:
    """全文搜索 - 直接查询 LangChain 表，使用连接池"""

    def __init__(self, collection_name: str = None):
        self.collection_name = collection_name or settings.PGVECTOR_COLLECTION_NAME

    def search(self, query: str, user_id: str, top_k: int = 4) -> list[FulltextResult]:
        """
        全文搜索 - 使用 websearch_to_tsquery

        Args:
            query: 查询文本
            user_id: 用户ID
            top_k: 返回数量

        Returns:
            全文搜索结果列表
        """
        from app.services.db_pool import to_query as _to_query

        conn = get_conn()
        cursor = conn.cursor()

        try:
            # 使用 jieba 分词 (从 db_pool 导入)
            query_ts = _to_query(query)

            sql = """
                SELECT
                    e.id as doc_id,
                    e.document as content,
                    e.cmetadata as metadata,
                    ts_rank_cd(e.search_vector, websearch_to_tsquery('simple', %s), 32) as score
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

            cursor.execute(sql, (query_ts, self.collection_name, user_id, top_k))

            results = []
            for row in cursor.fetchall():
                results.append(
                    FulltextResult(
                        doc_id=str(row["doc_id"]),
                        content=row["content"],
                        metadata=row["metadata"] or {},
                        score=float(row["score"]),
                    )
                )

            logger.info(
                f"全文检索: query='{query[:30]}...', 返回 {len(results)} 个结果"
            )
            return results

        finally:
            cursor.close()
            return_conn(conn)


# 全局实例
fulltext_search = FulltextSearch()
