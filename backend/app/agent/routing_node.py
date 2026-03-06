from typing import Literal
from langchain_core.runnables import RunnableConfig

from .state import AgentState
from ..llm.llm_factory import get_llm
from ..memory.memory_schema import RetrievalDecision


def routing_node(state: AgentState, config: RunnableConfig) -> dict:
    """智能路由节点 - 判断需要检索记忆和/或RAG"""
    messages = state.get("messages", [])
    if not messages:
        return {"retrieval_needed": {"memory": False, "rag": False}, "question": ""}

    query = messages[-1].content

    prompt = f"""分析用户输入的内容，判断是否需要检索记忆和/或知识库（RAG），当用户陈述事实时不需要检索记忆和/或知识库（RAG）。

用户输入的内容: {query}

返回JSON：{{
    "need_memory": true/false,
    "need_rag": true/false,
    "reason": "决策原因"
}}

判断标准：
- need_memory: 判断用户输入内容是查询信息，且查询涉及个人信息、偏好、历史对话、日程、约定
- need_rag: 判断用户输入内容是查询信息，且查询涉及产品功能、使用方法、文档说明、技术细节
"""

    llm = get_llm().with_structured_output(RetrievalDecision)
    decision = llm.invoke([{"role": "user", "content": prompt}])

    return {
        "retrieval_needed": {"memory": decision.need_memory, "rag": decision.need_rag},
        "question": query
    }


def routing_condition(state: AgentState) -> str:
    """路由条件"""
    needed = state.get("retrieval_needed", {})
    need_memory = needed.get("memory", False)
    need_rag = needed.get("rag", False)

    if need_memory and need_rag:
        return "parallel_both"
    elif need_memory:
        return "memory_only"
    elif need_rag:
        return "rag_only"
    return "direct_answer"