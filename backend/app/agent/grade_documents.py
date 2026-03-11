import logging
from .state import AgentState, GradeDocuments
from ..prompt.prompt import GRADE_PROMPT
from ..llm.llm_factory import get_llm
from typing import List

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def grade_documents(state: AgentState) -> dict:
    """文档相关性评分"""
    question = state.get("question", "")
    parallel_results = state.get("parallel_results", [])

    # 获取文档结果
    docs: List[Document] = []
    for result in parallel_results:
        if result.get("source") == "documents":
            docs = result.get("data", [])
            break

    loop_step = state.get("loop_step", 0)
    if loop_step >= 3:
        return {"routing_decision": "generate_response"}

    if not docs:
        logger.info("没有检索到文档，跳过评分")
        return {"routing_decision": "rewrite_question"}

    # 构建上下文
    context = "\n\n".join([d.page_content for d in docs])
    prompt = GRADE_PROMPT.format(question=question, context=context)

    response: GradeDocuments = get_llm().with_structured_output(GradeDocuments).invoke(
        [{"role": "user", "content": prompt}]
    )

    score = response.binary_score
    if score == "yes":
        logger.info("文档相关，生成响应")
        return {"routing_decision": "generate_response"}
    else:
        logger.info(f"文档不相关，重写问题: {question}, 次数: {loop_step}")
        return {"routing_decision": "rewrite_question"}


def grade_routing_condition(state: AgentState) -> str:
    """基于评分的路由决策"""
    return state.get("routing_decision", "") or "generate_response"