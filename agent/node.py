from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import MessagesState
from langgraph.store.base import BaseStore

from agent.state import GradeDocuments
from llm.llm_factory import get_llm
from prompt.prompt import REWRITE_PROMPT, GENERATE_PROMPT, GRADE_PROMPT
from tools import get_tools


def generate_query_or_respond(state: MessagesState,
                              config: RunnableConfig,
                              *,
                              store: BaseStore, ):
    """调用模型，根据当前状态生成响应。针对问题，它会选择使用检索工具取回，或者简单地回应用户。"""
    # 获取用户ID
    user_id = config["configurable"]["user_id"]

    # 构建系统消息，包含用户ID信息
    system_msg = f"你是一个有用的助手，与用户对话。你可以使用工具来检索或保存用户记忆。用户ID是: {user_id}"

    # 将记忆工具和检索工具一起绑定到模型
    # 为工具添加默认参数（包括user_id）

    response = (
        get_llm()
        .bind_tools(get_tools()).invoke([{"role": "system", "content": system_msg}] + state["messages"])
    )
    return {"messages": [response]}


def rewrite_question(state: MessagesState):
    """重写原用户问题."""
    messages = state["messages"]
    question = messages[0].content
    prompt = REWRITE_PROMPT.format(question=question)
    response = get_llm().invoke([{"role": "user", "content": prompt}])
    return {"messages": [HumanMessage(content=response.content)]}


def generate_answer(state: MessagesState):
    """生成答案."""
    question = state["messages"][0].content
    context = state["messages"][-1].content
    prompt = GENERATE_PROMPT.format(question=question, context=context)
    response = get_llm().invoke([{"role": "user", "content": prompt}])
    return {"messages": [response]}



def grade_documents(
        state: MessagesState,
) -> Literal["generate_answer", "rewrite_question"]:
    """确定检索到的文件是否与问题相关."""
    question = state["messages"][0].content
    context = state["messages"][-1].content

    prompt = GRADE_PROMPT.format(question=question, context=context)
    response = (
        get_llm()
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