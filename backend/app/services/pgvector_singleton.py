"""
PGVector 单例服务 - 委托给 pgvector_store 的单例
"""

import logging
from typing import Optional

from langchain_postgres.vectorstores import PGVector as LangchainPGVector

logger = logging.getLogger(__name__)


class PGVectorSingleton:
    """
    PGVector 单例类 - 已弃用，请使用 app.retriever.pgvector_store.get_pgvector_store()
    """

    _instance: Optional["PGVectorSingleton"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_vector_store(self) -> LangchainPGVector:
        """
        获取 PGVector 实例（委托给 pgvector_store 单例）

        已弃用：直接使用 get_pgvector_store() 代替
        """
        logger.warning(
            "PGVectorSingleton.get_vector_store() 已弃用，请使用 get_pgvector_store()"
        )
        from app.retriever.pgvector_store import get_pgvector_store

        return get_pgvector_store()


pgvector_singleton = PGVectorSingleton()
