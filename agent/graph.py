# LangGraph 主图

import os
from langgraph.checkpoint.redis import RedisSaver
from langgraph.store.postgres import PostgresStore
from agent.node import generate_query_or_respond, rewrite_question, generate_answer, grade_documents
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from tools import get_tools


def get_graph():
    with (RedisSaver.from_conn_string(os.getenv("REDIS_URL")) as checkpointer,
          PostgresStore.from_conn_string(os.getenv("POSTGRESQL_URL")) as store):
        # checkpointer.setup()
        # store.setup()

        workflow = StateGraph(MessagesState)
        # Define the nodes we will cycle between
        workflow.add_node(generate_query_or_respond)
        workflow.add_edge(START, "generate_query_or_respond")
        
        # 获取所有工具，包括带存储功能的记忆工具
        
        # 创建包含所有工具的工具节点
        workflow.add_node("tool_node", ToolNode(get_tools()))
        workflow.add_node(rewrite_question)
        workflow.add_node(generate_answer)

        # Decide whether to use tools
        workflow.add_conditional_edges(
            "generate_query_or_respond",
            # Assess LLM decision (call any of the tools or respond to the user)
            tools_condition,
            {
                # Translate the condition outputs to nodes in our graph
                "tools": "tool_node",
                END: END,
            },
        )

        # Edges taken after the `tool_node` is called.
        workflow.add_conditional_edges(
            "tool_node",
            # Assess agent decision
            grade_documents,
        )
        workflow.add_edge("generate_answer", END)
        workflow.add_edge("rewrite_question", "generate_query_or_respond")

        # Compile
        return workflow.compile(checkpointer=checkpointer, store=store)
