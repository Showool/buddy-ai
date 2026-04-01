import logging
from typing import List
from langgraph.types import Send
from .state import AgentState
from ..memory.memory_schema import RetrievalDecision
from ..llm.llm_factory import get_llm
from ..prompt.prompt import ROUTING_DECISION_PROMPT

logger = logging.getLogger(__name__)


def parallel_routing_node(state: AgentState, config) -> dict:
    """决策节点 - 判断需要并行检索哪些来源"""
    messages = state.get("messages", [])
    if not messages:
        return {"classifications": [], "question": ""}

    query = messages[-1].content
    prompt = ROUTING_DECISION_PROMPT.format(query=query)

    llm = get_llm().with_structured_output(RetrievalDecision)
    decision: RetrievalDecision = llm.invoke([{"role": "user", "content": prompt}])

    # 转换为并行路由格式
    classifications = []
    if decision.need_memory:
        classifications.append({"source": "memory_retrieval", "query": query})
    if decision.need_rag:
        classifications.append({"source": "document_retrieval", "query": query})

    return {"classifications": classifications, "question": query}


def parallel_route_condition(state: AgentState) -> List[Send]:
    """返回 Send 对象列表实现并行 fan-out"""
    classifications = state.get("classifications", [])
    if not classifications:
        # 没有需要检索的，直接生成响应
        return [Send("generate_response", {"question": state.get("question", "")})]

    return [Send(c["source"], {"question": c["query"]}) for c in classifications]
