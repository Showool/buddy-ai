"""
PGVector 单例服务 - 同步版本
"""
import logging
from typing import Optional

from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector as LangchainPGVector

from app.config import settings
from app.retriever.embeddings_model import get_embeddings_model

logger = logging.getLogger(__name__)


class PGVectorSingleton:
    _instance: Optional['PGVectorSingleton'] = None
    _vector_store: Optional[LangchainPGVector] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_vector_store(self) -> LangchainPGVector:
        if self._vector_store is None:
            self._vector_store = PGVector(
                collection_name=settings.PGVECTOR_COLLECTION_NAME,
                connection=settings.POSTGRESQL_URL,
                embeddings=get_embeddings_model(),
                use_jsonb=True
            )
            logger.info("PGVector 实例创建成功（同步）")

        return self._vector_store


pgvector_singleton = PGVectorSingleton()