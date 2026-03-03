"""
PGVector 单例服务 - 连接池优化
"""
import logging
from typing import Optional

import asyncpg
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector as LangchainPGVector

from app.config import settings
from app.retriever.embeddings_model import get_embeddings_model

logger = logging.getLogger(__name__)


class PGVectorSingleton:
    _instance: Optional['PGVectorSingleton'] = None
    _vector_store: Optional[LangchainPGVector] = None
    _pool: Optional[asyncpg.Pool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_vector_store(self) -> LangchainPGVector:
        if self._vector_store is None:
            self._pool = await asyncpg.create_pool(
                settings.POSTGRESQL_URL,
                min_size=2,
                max_size=10
            )

            self._vector_store = PGVector(
                collection_name=settings.PGVECTOR_COLLECTION_NAME,  # 从配置获取统一 collection
                connection=self._pool,
                embeddings=get_embeddings_model(),
                use_jsonb=True
            )
            logger.info("PGVector 实例创建成功（带连接池）")

        return self._vector_store

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._vector_store = None


pgvector_singleton = PGVectorSingleton()