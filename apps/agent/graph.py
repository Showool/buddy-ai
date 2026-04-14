
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.redis import RedisSaver
from langgraph.prebuilt import ToolNode

from apps.agent.condition import assign_workers, generate_response_router, route_condition
from apps.agent.nodes import generate_response, router, retrieve_memories, save_memories, query_transform, hybrid_search, text_match, plan_step, synthesis_step_results, work_step, evaluate_node
from apps.agent.state import GraphState
from apps.agent.tools import get_tools
from apps.config import settings


def get_graph():
    """构建带记忆中间件的架构图"""
    with RedisSaver.from_conn_string(settings.REDIS_URL) as checkpointer:

        checkpointer.setup()

        workflow = StateGraph(GraphState)

        # 节点定义
        workflow.add_node("retrieve_memories", retrieve_memories)
        workflow.add_node("router", router)
        workflow.add_node("query_transform", query_transform)
        workflow.add_node("hybrid_search", hybrid_search)
        workflow.add_node("text_match", text_match)
        workflow.add_node("generate_response", generate_response)
        workflow.add_node("planner", plan_step)
        workflow.add_node("work_step", work_step)
        workflow.add_node("synthesis_step_results", synthesis_step_results)
        workflow.add_node("evaluate_node", evaluate_node)

        
        workflow.add_node("tool_node", ToolNode(get_tools))

        # 边定义: 记忆检索 → 路由 → ... → 记忆存储
        workflow.add_edge(START, "retrieve_memories")
        workflow.add_edge("retrieve_memories", "router")
        workflow.add_conditional_edges("router", route_condition, {
            "query_transform": "query_transform",
            "planner": "planner",
            "direct_answer": "generate_response"
        })

        workflow.add_conditional_edges(
          "planner", assign_workers, ["work_step"]
        )
        workflow.add_edge("work_step", "synthesis_step_results")
        workflow.add_edge("synthesis_step_results", END)

        workflow.add_edge("query_transform", "hybrid_search")
        workflow.add_edge("query_transform", "text_match")
        workflow.add_edge("hybrid_search", "generate_response")
        workflow.add_edge("text_match", "generate_response")

        # generate_response 统一出边：工具调用 → 评估 → 结束
        workflow.add_conditional_edges(
            "generate_response",
            generate_response_router,
            {"tool_node": "tool_node", "evaluate_node": "evaluate_node", END: END}
        )
        workflow.add_edge("tool_node", "generate_response")
        workflow.add_edge("evaluate_node", "generate_response")

        return workflow.compile(checkpointer=checkpointer)
    

