"""
Mem0 记忆模块 - 使用 Milvus 向量库存储
"""

import logging
from typing import Optional

from mem0 import Memory

from apps.config import settings

logger = logging.getLogger(__name__)

_memory_instance: Optional[Memory] = None


def get_memory() -> Memory:
    """获取 mem0 Memory 单例实例"""
    global _memory_instance
    if _memory_instance is None:
        config = {
            "vector_store": {
                "provider": "milvus",
                "config": {
                    "collection_name": settings.MILVUS_MEM0_COLLECTION_NAME,
                    "embedding_model_dims": settings.EMBEDDING_DIMENSIONS,
                    "url": settings.MILVUS_URL,
                    "token": settings.MILVUS_TOKEN or None,
                    "db_name": settings.MILVUS_DB_NAME,
                },
            }
        }
        _memory_instance = Memory.from_config(config)
        logger.info("Mem0 Memory 实例已创建 (Milvus: %s)", settings.MILVUS_URL)
    return _memory_instance
