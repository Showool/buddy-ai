"""
Mem0 记忆模块 - 使用 Milvus 向量库存储
"""

import logging
from mem0 import Memory
from apps.config import settings

logger = logging.getLogger(__name__)

class MemoryManager:

    def __init__(self):
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
            },
            "llm": {
                "provider": settings.LLM_PROVIDER,
                "config": {
                    "model": settings.LLM_MODEL,
                    "temperature": 0,
                    "max_tokens": 2000,
                    "api_key": settings.OPENAI_API_KEY,
                }
            },
            "embedder": {
                "provider": settings.EMBEDDING_PROVIDER,
                "config": {
                    "model": settings.EMBEDDING_MODEL,
                    "embedding_dims": settings.EMBEDDING_DIMENSIONS,
                    "api_key": settings.OPENAI_API_KEY,
                }
            }
        }
        self.memory_client = Memory.from_config(config)
        logger.info("Mem0 Memory 实例已创建 (Milvus: %s)", settings.MILVUS_URL)


memoryClient = MemoryManager().memory_client

