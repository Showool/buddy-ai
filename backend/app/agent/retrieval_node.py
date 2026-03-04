"""
检索节点 - LangGraph 节点级检索集成（同步版本）
"""
import logging
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from pydantic import BaseModel, Field

from .state import AgentState
from ..services.retrieval_orchestrator import retrieval_orchestrator

logger = logging.getLogger(__name__)


class RetrievalDecision(BaseModel):
    should_retrieve: bool = Field(description="是否需要从知识库检索信息")
    reason: str = Field(description="判断理由")


QUICK_SKIP_KEYWORDS = ["天气", "新闻", "汇率", "股价", "实时", "今日", "昨天"]


def retrieval_node(
    state: AgentState,
    config: RunnableConfig,
    *,
    store: BaseStore
) -> dict:
    """检索节点 - 执行混合检索"""
    messages = state.get("messages", [])
    if not messages:
        return {"retrieved_documents": [], "retrieval_metadata": None}

    query = messages[-1].content
    user_id = config["configurable"].get("user_id")

    logger.info(f"检索节点: query={query[:50]}..., user_id={user_id}")

    try:
        result = retrieval_orchestrator.retrieve(
            query=query,
            user_id=user_id,
            k=4
        )

        return {
            "retrieved_documents": result.documents,
            "retrieved_metadata": {
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
    """检索决策节点 - LLM智能判断 + 快速规则过滤"""
    messages = state.get("messages", [])
    if not messages:
        return {"should_retrieve": False}

    query = messages[-1].content

    # 快速过滤：包含实时信息关键词，直接跳过检索
    if any(kw in query for kw in QUICK_SKIP_KEYWORDS):
        logger.info(f"快速过滤: 查询包含实时信息关键词，跳过检索")
        return {"should_retrieve": False}

    # 使用LLM判断是否需要检索
    try:
        from ..llm.llm_factory import get_llm
        from ..prompt.prompt import RETRIEVAL_DECISION_PROMPT

        llm = get_llm().with_structured_output(RetrievalDecision)
        result = llm.invoke(RETRIEVAL_DECISION_PROMPT.format(query=query))

        logger.info(f"LLM检索决策: should_retrieve={result.should_retrieve}, reason={result.reason}")
        return {"should_retrieve": result.should_retrieve}

    except Exception as e:
        logger.error(f"检索决策失败，默认不检索: {e}")
        return {"should_retrieve": False}


def retrieval_condition(state: AgentState) -> Literal["retrieval_node", "generate_response"]:
    """检索条件函数"""
    return "retrieval_node" if state.get("should_retrieve") else "generate_response"