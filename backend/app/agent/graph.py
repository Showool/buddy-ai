import logging
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from ..retriever.embeddings_model import get_embeddings_model
from ..config import settings
from langgraph.checkpoint.redis import RedisSaver
from langgraph.store.postgres import PostgresStore

from .state import AgentState
from .parallel_routing_node import parallel_routing_node, parallel_route_condition
from .memory_retrieval_node import memory_retrieval_node
from .document_retrieval_node import document_retrieval_node
from .grade_documents import grade_documents, grade_routing_condition
from .rewrite_question_node import rewrite_question
from .generate_response_node import generate_response

from ..tools import tavily_search, save_conversation_memory

logger = logging.getLogger(__name__)


def get_graph():
    """构建并行架构图"""
    with (
        RedisSaver.from_conn_string(settings.REDIS_URL) as checkpointer,
        PostgresStore.from_conn_string(
            settings.POSTGRESQL_URL,
            index={
                "embed": get_embeddings_model(),
                "dims": settings.EMBEDDING_DIMENSIONS,
            },
        ) as store,
    ):

        store.setup()

        workflow = StateGraph(AgentState)

        # 节点定义
        workflow.add_node("route", parallel_routing_node)
        workflow.add_node("memory_retrieval", memory_retrieval_node)
        workflow.add_node("document_retrieval", document_retrieval_node)
        workflow.add_node("grade_documents", grade_documents)
        workflow.add_node("rewrite_question", rewrite_question)
        workflow.add_node("generate_response", generate_response)
        workflow.add_node(
            "tool_node", ToolNode([tavily_search, save_conversation_memory])
        )

        # 边定义
        workflow.add_edge(START, "route")

        # 并行路由 → fan-out
        workflow.add_conditional_edges(
            "route",
            parallel_route_condition,
            ["memory_retrieval", "document_retrieval", "generate_response"],
        )

        # 并行节点 → fan-in
        workflow.add_edge("document_retrieval", "grade_documents")
        workflow.add_edge("memory_retrieval", "generate_response")

        # 评分 → 生成响应 OR 重写
        workflow.add_conditional_edges(
            "grade_documents",
            grade_routing_condition,
            {
                "generate_response": "generate_response",
                "rewrite_question": "rewrite_question",
            },
        )

        workflow.add_edge("rewrite_question", "document_retrieval")

        # 生成响应 → 工具 OR 结束
        workflow.add_conditional_edges(
            "generate_response", tools_condition, {"tools": "tool_node", END: END}
        )

        workflow.add_edge("tool_node", END)

        return workflow.compile(checkpointer=checkpointer, store=store)
