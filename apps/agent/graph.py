from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.redis import RedisSaver
from langgraph.prebuilt import ToolNode

from apps.agent.condition import assign_workers, generate_response_router, route_condition
from apps.agent.nodes import generate_response, router, retrieve_memories, save_memories, query_transform, query_transform_HyDE, hybrid_search, text_match, plan_step, synthesis_step_results, work_step, evaluate_node
from apps.agent.state import GraphState
from apps.agent.tools import get_tools
from apps.config import settings

# 模块级单例，由 lifespan 初始化
_compiled_graph = None


def build_workflow():
    """构建 workflow 图结构（纯图定义，不涉及 checkpointer）"""
    workflow = StateGraph(GraphState)

    # 节点定义
    workflow.add_node("retrieve_memories", retrieve_memories)
    workflow.add_node("router", router)
    workflow.add_node("query_transform", query_transform)
    workflow.add_node("query_transform_HyDE", query_transform_HyDE)
    workflow.add_node("hybrid_search", hybrid_search)
    workflow.add_node("text_match", text_match)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("planner", plan_step)
    workflow.add_node("work_step", work_step)
    workflow.add_node("synthesis_step_results", synthesis_step_results)
    workflow.add_node("evaluate_node", evaluate_node)
    workflow.add_node("tool_node", ToolNode(get_tools))
    workflow.add_node("save_memories", save_memories)

    # 边定义: 记忆检索 → 路由 → ... → 记忆存储
    workflow.add_edge(START, "retrieve_memories")
    workflow.add_edge("retrieve_memories", "router")
    workflow.add_conditional_edges("router", route_condition, {
        "query_transform": "query_transform",
        "query_transform_HyDE": "query_transform_HyDE",
        "planner": "planner",
    })

    workflow.add_conditional_edges(
      "planner", assign_workers, ["work_step"]
    )
    workflow.add_edge("work_step", "synthesis_step_results")
    workflow.add_edge("query_transform", "generate_response")
    workflow.add_edge("query_transform_HyDE", "hybrid_search")
    workflow.add_edge("query_transform_HyDE", "text_match")
    workflow.add_edge("hybrid_search", "generate_response")
    workflow.add_edge("text_match", "generate_response")

    # generate_response 统一出边：工具调用 → 评估 → 保存记忆
    workflow.add_conditional_edges(
        "generate_response",
        generate_response_router,
        {"tool_node": "tool_node", "evaluate_node": "evaluate_node", "save_memories": "save_memories"}
    )
    workflow.add_edge("tool_node", "generate_response")
    workflow.add_edge("evaluate_node", "generate_response")
    workflow.add_edge("synthesis_step_results", "save_memories")
    workflow.add_edge("save_memories", END)

    return workflow


def init_graph(checkpointer):
    """编译 graph 并缓存为单例"""
    global _compiled_graph
    _compiled_graph = build_workflow().compile(checkpointer=checkpointer)


def get_graph():
    """获取已编译的 graph 单例"""
    if _compiled_graph is None:
        raise RuntimeError("Graph 未初始化，请先在 lifespan 中调用 init_graph()")
    return _compiled_graph
