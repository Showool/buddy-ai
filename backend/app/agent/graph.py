# LangGraph 主图 - 并行架构优化版本

import logging
from typing import Literal

from ..retriever.embeddings_model import get_embeddings_model


from ..config import settings
from langgraph.checkpoint.redis import RedisSaver
from langgraph.store.postgres import PostgresStore
from .node import generate_response, rewrite_question, grade_documents, grade_routing_condition
from .state import AgentState, GradeDocuments
from .retrieval_node import retrieval_node, retrieval_decision_node, retrieval_condition
from .routing_node import routing_node, routing_condition
from .memory_node import memory_retrieval_node
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from ..tools import save_conversation_memory, tavily_search

logger = logging.getLogger(__name__)




def get_graph():


    """构建新的并行架构图"""
    with (RedisSaver.from_conn_string(settings.REDIS_URL) as checkpointer,
          PostgresStore.from_conn_string(settings.POSTGRESQL_URL, index={"embed": get_embeddings_model(), "dims": settings.EMBEDDING_DIMENSIONS}) as store):
        
        store.setup()

        workflow = StateGraph(AgentState)

        # 节点定义
        workflow.add_node("routing", routing_node)
        workflow.add_node("memory_retrieval", memory_retrieval_node)
        workflow.add_node("retrieval_node", retrieval_node)
        workflow.add_node("grade_documents", grade_documents)
        workflow.add_node("rewrite_question", rewrite_question)
        workflow.add_node("generate_response", generate_response)
        workflow.add_node("tool_node", ToolNode([tavily_search, save_conversation_memory]))

        # 边定义
        workflow.add_edge(START, "routing")

        # 路由 → 并行/单一路径
        workflow.add_conditional_edges(
            "routing",
            routing_condition,
            {
                "parallel_both": "memory_retrieval",  # 先记忆检索，再并行
                "memory_only": "memory_retrieval",
                "rag_only": "retrieval_node",
                "direct_answer": "generate_response"
            }
        )

        # 记忆检索 → 生成响应（或跳转到 RAG）
        workflow.add_conditional_edges(
            "memory_retrieval",
            lambda state: "retrieval_node" if state.get("retrieval_needed", {}).get("rag", False) else "generate_response",
            {
                "retrieval_node": "retrieval_node",
                "generate_response": "generate_response"
            }
        )

        workflow.add_edge("retrieval_node", "grade_documents")

        # 评分 → 答案 OR 重写
        workflow.add_conditional_edges(
            "grade_documents",
            grade_routing_condition,
            {
                "generate_response": "generate_response",
                "rewrite_question": "rewrite_question"
            }
        )

        workflow.add_edge("rewrite_question", "retrieval_node")

        # 生成响应 → 工具 OR 结束
        workflow.add_conditional_edges(
            "generate_response",
            tools_condition,
            {"tools": "tool_node", END: END}
        )

        workflow.add_edge("tool_node", END)

        return workflow.compile(checkpointer=checkpointer, store=store)