from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from .state import GradeDocuments, AgentState
from ..llm.llm_factory import get_llm
from ..prompt.prompt import REWRITE_PROMPT, GENERATE_PROMPT, GRADE_PROMPT
from ..tools import get_tools


def generate_query_or_respond(state: AgentState,
                              config: RunnableConfig,
                              *,
                              store: BaseStore, ):
    """调用模型，根据当前状态生成响应。针对问题，它会选择使用检索工具取回，或者简单地回应用户。"""
    # 获取用户ID
    user_id = config["configurable"]["user_id"]

    # 构建系统消息，包含用户ID信息和记忆管理指导
    system_msg = f"""你是一个智能助手，具有长期记忆功能。用户ID是: {user_id}

记忆管理规则：
1. 当用户问题涉及个人信息、偏好、历史对话等，优先使用 retrieve_memory 工具查询用户记忆
2. 查询记忆时使用 user_id 参数（当前用户ID: {user_id}）
3. 在回答用户问题后，如果对话包含重要信息（如个人信息、偏好、约定等），使用 save_conversation_memory 工具保存到长期记忆
4. save_conversation_memory 需要传入用户的问题和你的回答作为参数

工具说明：
- retrieve_memory(query, user_id): 根据查询词检索用户的历史记忆
- save_conversation_memory(question, answer, user_id): 保存对话到长期记忆
- retrieve_context: 从知识库检索相关信息
- tavily_search: 网络搜索获取实时信息
- get_weather_for_location: 获取天气信息

对话流程：
1. 分析用户问题，判断是否需要查询记忆
2. 如需查询，先调用 retrieve_memory 获取历史信息
3. 结合记忆、知识库和网络搜索回答问题
4. 发现重要新信息时，在回答后调用 save_conversation_memory 保存

注意：不要过度使用 save_conversation_memory，只在真正需要长期保存的信息时调用。"""

    # 将记忆工具和检索工具一起绑定到模型
    # 为工具添加默认参数（包括user_id）

    response = (
        get_llm()
        .bind_tools(get_tools()).invoke([{"role": "system", "content": system_msg}] + state["messages"])
    )
    return {"messages": [response]}


def rewrite_question(state: AgentState):
    """重写原用户问题."""
    messages = state["messages"]
    question = messages[0].content
    
    # 获取最后一条消息（通常是 ToolMessage）
    last_message = messages[-1]
    
    # 默认策略
    strategy = "优化检索"
    
    # 检查是否是工具调用结果
    if hasattr(last_message, "tool_call_id") or last_message.type == "tool":
        # 简单判断：如果内容包含"没有找到"或内容很短，认为无效，切换到联网搜索
        # 如果内容较长但还是被 grade_documents 拒绝了，则尝试优化检索词
        content = last_message.content
        if "没有找到" in content or len(content) < 50:
             strategy = "联网搜索"
        else:
             strategy = "优化检索"
    
    prompt = REWRITE_PROMPT.format(question=question, strategy=strategy)
    response = get_llm().invoke([{"role": "user", "content": prompt}])
    loop_step = state.get("loop_step", 0)
    return {"messages": [HumanMessage(content=response.content)], "loop_step": loop_step + 1}


def generate_answer(state: AgentState):
    """生成答案."""
    question = state["messages"][0].content
    context = state["messages"][-1].content
    prompt = GENERATE_PROMPT.format(question=question, context=context)
    response = get_llm().invoke([{"role": "user", "content": prompt}])
    return {"messages": [response]}



def grade_documents(
        state: AgentState,
) -> Literal["generate_answer", "rewrite_question"]:
    """确定检索到的文件是否与问题相关."""
    question = state["messages"][0].content
    context = state["messages"][-1].content

    loop_step = state.get("loop_step", 0)
    if loop_step >= 3:
        return "generate_answer"

    prompt = GRADE_PROMPT.format(question=question, context=context)
    response = (
        get_llm()
        .with_structured_output(GradeDocuments).invoke(
            [{"role": "user", "content": prompt}]
        )
    )
    score = response.binary_score
    if score == "yes":
        return "generate_answer"
    else:
        print(f"Rewriting question: {question}, times: {loop_step}")
        return "rewrite_question"