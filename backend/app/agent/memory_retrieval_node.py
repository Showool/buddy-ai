import logging
from langchain_core.runnables import RunnableConfig

from .state import AgentState

logger = logging.getLogger(__name__)


def memory_retrieval_node(
    state: AgentState,
    config: RunnableConfig,
) -> dict:
    """记忆检索节点 - 使用 runtime.store"""
    messages = state.get("messages", [])
    if not messages:
        return {"user_memories": []}

    query = messages[-1].content
    user_id = config["configurable"].get("user_id")

    try:
        from ..memory.memory_service import memory_service
        memories = memory_service.retrieve_memory(user_id, query, limit=3)
        logger.info(f"检索到 {len(memories)} 条记忆")
        return {"user_memories": memories}
    except Exception as e:
        logger.error(f"记忆检索失败: {e}")
        return {"user_memories": []}