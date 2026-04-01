import logging
from langchain_core.runnables import RunnableConfig
from .state import AgentState
from ..llm.llm_factory import get_llm
from ..tools.web_search_tool import tavily_search
from ..tools.user_tool import save_conversation_memory
from ..prompt.prompt import (
    RESPONSE_WITH_CONTEXT_PROMPT,
    RESPONSE_WITHOUT_CONTEXT_PROMPT,
    format_context_parts,
)

logger = logging.getLogger(__name__)


def generate_response(state: AgentState, config: RunnableConfig) -> dict:
    """响应节点 - 从并行结果中提取检索信息"""
    user_id = config["configurable"]["user_id"]
    question = state.get("question", "")

    # 从并行结果提取数据
    parallel_results = state.get("parallel_results", [])
    retrieved_docs = []
    user_memories = []

    for result in parallel_results:
        if result.get("source") == "documents":
            retrieved_docs = result.get("data", [])
        elif result.get("source") == "memory":
            user_memories = result.get("data", [])

    logger.info(
        f"用户问题: {question}, 文档: {len(retrieved_docs)}, 记忆: {len(user_memories)}"
    )

    has_context = bool(retrieved_docs or user_memories)

    if has_context:
        context_parts = format_context_parts(retrieved_docs, user_memories)
        system_msg = RESPONSE_WITH_CONTEXT_PROMPT.format(
            user_id=user_id, context_parts=context_parts, question=question
        )
    else:
        system_msg = RESPONSE_WITHOUT_CONTEXT_PROMPT.format(
            user_id=user_id, question=question
        )

    response = (
        get_llm()
        .bind_tools([tavily_search, save_conversation_memory])
        .invoke([{"role": "system", "content": system_msg}])
    )

    return {"messages": [response]}
