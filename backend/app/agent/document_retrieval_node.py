import logging
from langchain_core.runnables import RunnableConfig
from .state import AgentState
from ..services.retrieval_orchestrator import retrieval_orchestrator

logger = logging.getLogger(__name__)


def document_retrieval_node(state: AgentState, config: RunnableConfig) -> dict:
    """文档检索节点"""
    query = state.get("question", "") or ""
    user_id = config["configurable"].get("user_id")

    logger.info(f"文档检索: query={query[:50]}..., user_id={user_id}")

    try:
        result = retrieval_orchestrator.retrieve(query=query, user_id=user_id, k=4)

        return {
            "parallel_results": [{"source": "documents", "data": result.documents}],
            "retrieval_strategy": result.strategy,
        }

    except Exception as e:
        logger.error(f"文档检索失败: {e}")
        return {"parallel_results": [{"source": "documents", "data": []}]}
