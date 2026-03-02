# LangGraph 主图

import logging
from typing import Literal

from ..config import settings
from langgraph.checkpoint.redis import RedisSaver
from langgraph.store.postgres import PostgresStore
from .node import generate_query_or_respond, rewrite_question, generate_answer, _calculate_query_similarity
from .state import AgentState, GradeDocuments
from .retrieval_node import retrieval_node, retrieval_decision_node, retrieval_condition
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from ..tools import get_tools
from ..prompt.prompt import GRADE_PROMPT

logger = logging.getLogger(__name__)


def grade_documents_node(state: AgentState) -> dict:
    """文档评分节点 - 评估检索到的文档相关性"""
    MAX_RETRIES = 3
    loop_step = state.get("loop_step", 0)

    if loop_step >= MAX_RETRIES:
        logger.warning(f"超过最大重试次数 ({MAX_RETRIES})，直接生成答案")
        return {"grade_score": "yes"}

    # 检查重复查询
    query_history = state.get("query_history", [])
    question = state["messages"][0].content
    current_query_normalized = question.lower().strip()

    for prev_query in query_history[-3:]:
        if _calculate_query_similarity(current_query_normalized, prev_query.lower().strip()) > 0.9:
            logger.warning("检测到重复查询，停止重写")
            return {"grade_score": "yes"}

    retrieved_docs = state.get("retrieved_documents", [])

    if retrieved_docs:
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        prompt = GRADE_PROMPT.format(question=question, context=context)

        from ..llm.llm_factory import get_llm
        response = (
            get_llm()
            .with_structured_output(GradeDocuments)
            .invoke([{"role": "user", "content": prompt}])
        )

        logger.info(f"文档评分: {response.binary_score}")
        return {"grade_score": response.binary_score}

    return {"grade_score": "no"}


def grade_documents_with_loop_check(state: AgentState) -> Literal["generate_answer", "rewrite_question"]:
    """文档评分条件边（带循环检查）"""
    MAX_RETRIES = 3
    loop_step = state.get("loop_step", 0)

    if loop_step >= MAX_RETRIES:
        return "generate_answer"

    # 检查重复查询
    query_history = state.get("query_history", [])
    question = state["messages"][0].content
    current_query_normalized = question.lower().strip()

    for prev_query in query_history[-3:]:
        if _calculate_query_similarity(current_query_normalized, prev_query.lower().strip()) > 0.9:
            logger.warning("检测到重复查询，停止重写")
            return "generate_answer"

    # 从状态中获取评分结果
    grade_score = state.get("grade_score", "no")
    return "generate_answer" if grade_score == "yes" else "rewrite_question"


def get_graph():
    with (RedisSaver.from_conn_string(settings.REDIS_URL) as checkpointer,
          PostgresStore.from_conn_string(settings.POSTGRESQL_URL) as store):

        workflow = StateGraph(AgentState)

        # 节点定义
        workflow.add_node("retrieval_decision", retrieval_decision_node)
        workflow.add_node("retrieval_node", retrieval_node)
        workflow.add_node("generate_query_or_respond", generate_query_or_respond)
        workflow.add_node("tool_node", ToolNode(get_tools()))
        workflow.add_node("grade_documents", grade_documents_node)
        workflow.add_node("rewrite_question", rewrite_question)
        workflow.add_node("generate_answer", generate_answer)

        # 边定义
        workflow.add_edge(START, "retrieval_decision")
        workflow.add_conditional_edges(
            "retrieval_decision",
            retrieval_condition,
            {
                "retrieval_node": "retrieval_node",
                "generate_query_or_respond": "generate_query_or_respond"
            }
        )
        workflow.add_edge("retrieval_node", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            grade_documents_with_loop_check,
            {
                "generate_answer": "generate_answer",
                "rewrite_question": "rewrite_question"
            }
        )
        workflow.add_conditional_edges(
            "generate_query_or_respond",
            tools_condition,
            {
                "tools": "tool_node",
                END: END,
            },
        )
        workflow.add_edge("tool_node", "grade_documents")
        workflow.add_edge("rewrite_question", "retrieval_node")
        workflow.add_edge("generate_answer", END)

        return workflow.compile(checkpointer=checkpointer, store=store)