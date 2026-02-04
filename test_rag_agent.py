import io
import json
import os
import uuid

from langchain.tools import tool
from langchain_core.messages import convert_to_messages
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.redis import RedisSaver
from langgraph.store.base import BaseStore
from langgraph.store.postgres import PostgresStore

from llm.llm_factory import get_llm
from retriever.get_retriever import get_retriever


@tool
def retrieve_blog_posts(query: str) -> str:
    """搜索并返回关于手机的信息."""
    docs = get_retriever().invoke(query)
    return "\n\n".join([doc.page_content for doc in docs])


retriever_tool = retrieve_blog_posts

from langgraph.graph import MessagesState

response_model = get_llm()


def generate_query_or_respond(state: MessagesState):
    """调用模型，根据当前状态生成响应。针对问题，它会选择使用检索工具取回，或者简单地回应用户.
    """
    response = (
        response_model
        .bind_tools([retriever_tool]).invoke(state["messages"])
    )
    return {"messages": [response]}


from pydantic import BaseModel, Field
from typing import Literal

# GRADE_PROMPT = (
#     "You are a grader assessing relevance of a retrieved document to a user question. \n "
#     "Here is the retrieved document: \n\n {context} \n\n"
#     "Here is the user question: {question} \n"
#     "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n"
#     "Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."
# )

GRADE_PROMPT = """
您是一名评估员，负责评估检索出的文档与用户问题相关性的程度。
以下是检索出的文档：
{context}
如果文档中包含与用户问题相关的关键词或语义内容，则将其评为相关。
请给出二元评分 'yes' 或 'no' 来表示文档是否与问题相关。
"""


class GradeDocuments(BaseModel):
    """使用二元评分来检查相关性文件."""

    binary_score: str = Field(
        description="相关性评分：如果相关，则为 'yes'，如果无关，则为 'no'"
    )


grader_model = get_llm()


def grade_documents(
        state: MessagesState,
) -> Literal["generate_answer", "rewrite_question"]:
    """确定检索到的文件是否与问题相关."""
    question = state["messages"][0].content
    context = state["messages"][-1].content

    prompt = GRADE_PROMPT.format(question=question, context=context)
    response = (
        grader_model
        .with_structured_output(GradeDocuments).invoke(
            [{"role": "user", "content": prompt}]
        )
    )
    score = response.binary_score
    return "generate_answer"
    # if score == "yes":
    #     return "generate_answer"
    # else:
    #     return "rewrite_question"


from langchain.messages import HumanMessage

# REWRITE_PROMPT = (
#     "Look at the input and try to reason about the underlying semantic intent / meaning.\n"
#     "Here is the initial question:"
#     "\n ------- \n"
#     "{question}"
#     "\n ------- \n"
#     "Formulate an improved question:"
# )

REWRITE_PROMPT = """
观察输入，尝试推理其语义意图的含义.
以下是初始问题：
 -------
{question}
 -------
提出一个改进的问题:
"""


def rewrite_question(state: MessagesState):
    """重写原用户问题."""
    messages = state["messages"]
    question = messages[0].content
    prompt = REWRITE_PROMPT.format(question=question)
    response = response_model.invoke([{"role": "user", "content": prompt}])
    return {"messages": [HumanMessage(content=response.content)]}


GENERATE_PROMPT = """
您是负责回答问题任务的助手。请使用所检索到的相关背景信息来回答问题。如果不知道答案，请直接说不知道。请最多用三句话来回答，并保持答案简洁明了。
问题：
{question}
背景信息：
{context}
"""


def generate_answer(state: MessagesState):
    """生成答案."""
    question = state["messages"][0].content
    context = state["messages"][-1].content
    prompt = GENERATE_PROMPT.format(question=question, context=context)
    response = response_model.invoke([{"role": "user", "content": prompt}])
    return {"messages": [response]}


from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

with (RedisSaver.from_conn_string(os.getenv("REDIS_URL")) as checkpointer,
    PostgresStore.from_conn_string(os.getenv("POSTGRESQL_URL")) as store):
    # checkpointer.setup()
    store.setup()


    def call_model(
            state: MessagesState,
            config: RunnableConfig,
            *,
            store: BaseStore,
    ):
        user_id = config["configurable"]["user_id"]
        namespace = ("memories", user_id)
        memories = store.search(namespace, query=str(state["messages"][-1].content))
        info = "\n".join([d.value["data"] for d in memories])
        system_msg = f"你是一个有用的助手，与用户对话。 用户信息: {info}"
        print(f'system_msg: {system_msg}')

        # Store new memories if the user asks the model to remember
        last_message = state["messages"][-1]
        print(f'call_model last_message: {last_message}')
        if "记住" in last_message.content.lower():
            print(f'call_model remember: {last_message.content.lower()}')
            memory = "用户姓名是Jason"
            store.put(namespace, str(uuid.uuid4()), {"data": memory})

        response = get_llm().invoke(
            [{"role": "system", "content": system_msg}] + state["messages"]
        )
        return {"messages": response}

    workflow = StateGraph(MessagesState)
    workflow.add_node(call_model)
    workflow.add_edge(START, "call_model")
    # Define the nodes we will cycle between
    workflow.add_node(generate_query_or_respond)
    workflow.add_edge(START, "generate_query_or_respond")
    workflow.add_node("retrieve", ToolNode([retriever_tool]))
    workflow.add_node(rewrite_question)
    workflow.add_node(generate_answer)



    # Decide whether to retrieve
    workflow.add_conditional_edges(
        "generate_query_or_respond",
        # Assess LLM decision (call `retriever_tool` tool or respond to the user)
        tools_condition,
        {
            # Translate the condition outputs to nodes in our graph
            "tools": "retrieve",
            END: END,
        },
    )

    # Edges taken after the `action` node is called.
    workflow.add_conditional_edges(
        "retrieve",
        # Assess agent decision
        grade_documents,
    )
    workflow.add_edge("generate_answer", END)
    workflow.add_edge("rewrite_question", "generate_query_or_respond")

    # Compile
    graph = workflow.compile(checkpointer=checkpointer, store=store)

    config = {"configurable": {"thread_id": "1", "user_id": "1"}}

    while True:
        question = input("User: ")
        if question == "quit":
            break

        for chunk in graph.stream(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": question,
                        }
                    ]
                },
                config,
                stream_mode="values",
        ):
            if "messages" in chunk:
                chunk["messages"][-1].pretty_print()
            elif "__interrupt__" in chunk:
                action = chunk["__interrupt__"][0]
                print("INTERRUPTED:")
                for request in action.value:
                    print(json.dumps(request, indent=2))
            else:
                pass





# import matplotlib
# matplotlib.use("TkAgg")  # 或 QtAgg

# import matplotlib.pyplot as plt
# from PIL import Image
#
# img = Image.open(io.BytesIO(graph.get_graph().draw_mermaid_png()))
# plt.imshow(img)
# plt.axis('off')  # 不显示坐标轴
# plt.show()