"""
检索节点 - LangGraph 节点级检索集成
"""
import logging
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from .state import AgentState
from ..services.retrieval_orchestrator import retrieval_orchestrator

logger = logging.getLogger(__name__)


def retrieval_node(
    state: AgentState,
    config: RunnableConfig,
    *,
    store: BaseStore
) -> dict:
    """检索节点 - 执行混合检索"""
    import asyncio

    messages = state.get("messages", [])
    if not messages:
        return {"retrieved_documents": [], "retrieval_metadata": None}

    query = messages[-1].content
    user_id = config["configurable"].get("user_id")

    logger.info(f"检索节点: query={query[:50]}..., user_id={user_id}")

    try:
        # 在同步上下文中运行异步检索
        result = asyncio.run(retrieval_orchestrator.retrieve(
            query=query,
            user_id=user_id,
            k=4
        ))

        return {
            "retrieved_documents": result.documents,
            "retrieval_metadata": {
                "query": query,
                "strategy": result.strategy
            }
        }

    except Exception as e:
        logger.error(f"检索失败: {e}")
        return {"retrieved_documents": [], "retrieval_metadata": None}


def retrieval_decision_node(
    state: AgentState,
    config: RunnableConfig,
    *,
    store: BaseStore
) -> dict:
    """检索决策节点 - 简单判断是否需要检索"""
    messages = state.get("messages", [])
    if not messages:
        return {"should_retrieve": False}

    query = messages[-1].content

    # 简单规则：包含"文档"、"文件"、"上传"等关键词时检索
    should_retrieve = any(
        keyword in query for keyword in ["文档", "文件", "上传", "资料", "知识库"]
    )

    logger.info(f"检索决策: should_retrieve={should_retrieve}")

    return {"should_retrieve": should_retrieve}


def retrieval_condition(state: AgentState) -> Literal["retrieval_node", "generate_query_or_respond"]:
    """检索条件函数"""
    return "retrieval_node" if state.get("should_retrieve") else "generate_query_or_respond"