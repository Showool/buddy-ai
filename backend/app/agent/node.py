from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from .state import GradeDocuments, AgentState
from ..llm.llm_factory import get_llm
from ..prompt.prompt import REWRITE_PROMPT, GENERATE_PROMPT, GRADE_PROMPT
from ..tools import get_tools

logger = __import__('logging').getLogger(__name__)


def _calculate_query_similarity(q1: str, q2: str) -> float:
    """简单计算查询相似度"""
    if q1 == q2:
        return 1.0

    words1 = set(q1.split())
    words2 = set(q2.split())

    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union) if union else 0.0


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
- retrieve_memory(query, user_id): 根据查询词检索用户的历史记忆，user_id参数为 "{user_id}"
- save_conversation_memory(question, answer, user_id): 保存对话到长期记忆，user_id参数为 "{user_id}"
- tavily_search: 网络搜索获取实时信息（新闻、动态等）

对话流程：
1. 分析用户问题，判断是否需要查询记忆
2. 如需查询，先调用 retrieve_memory 获取历史信息
3. 结合记忆和网络搜索回答问题
4. 发现重要新信息时，在回答后调用 save_conversation_memory 保存

注意：
1. 不要过度使用 save_conversation_memory，只在真正需要长期保存的信息时调用
2. 所有需要 user_id 参数的工具都应该使用当前用户ID: {user_id}"""

    # 将记忆工具和检索工具一起绑定到模型
    # 为工具添加默认参数（包括user_id）

    response = (
        get_llm()
        .bind_tools(get_tools()).invoke([{"role": "system", "content": system_msg}] + state["messages"])
    )
    return {"messages": [response]}


def rewrite_question(state: AgentState):
    """重写问题（防止死循环）"""
    messages = state["messages"]
    question = messages[0].content
    loop_step = state.get("loop_step", 0)
    query_history = state.get("query_history", [])

    MAX_RETRIES = 3
    if loop_step >= MAX_RETRIES:
        logger.warning(f"超过最大重试次数 ({MAX_RETRIES})，停止重写")
        return {"messages": [HumanMessage(content=question)], "loop_step": loop_step + 1}

    # 检测重复查询
    current_query_normalized = question.lower().strip()
    for prev_query in query_history[-3:]:
        if _calculate_query_similarity(current_query_normalized, prev_query.lower().strip()) > 0.9:
            logger.warning("检测到重复查询，停止重写")
            return {"messages": [HumanMessage(content=question)], "loop_step": loop_step + 1}

    # 策略判断
    last_message = messages[-1]
    strategy = "优化检索"

    if hasattr(last_message, "tool_call_id") or last_message.type == "tool":
        content = last_message.content
        if "没有找到" in content or len(content) < 50:
            strategy = "联网搜索"
        elif loop_step >= 1:
            strategy = "简化表达"

    # 生成重写问题
    prompt = REWRITE_PROMPT.format(question=question, strategy=strategy)
    response = get_llm().invoke([{"role": "user", "content": prompt}])

    rewritten_query = response.content.strip()

    # 验证重写结果
    similarity = _calculate_query_similarity(current_query_normalized, rewritten_query.lower().strip())
    if similarity > 0.85:
        rewritten_query = question

    logger.info(f"重写问题: '{question}' -> '{rewritten_query}', 次数: {loop_step}")

    return {
        "messages": [HumanMessage(content=rewritten_query)],
        "loop_step": loop_step + 1,
        "query_history": query_history + [question]
    }


def generate_answer(state: AgentState):
    """生成答案 - 使用检索到的上下文"""
    question = state["messages"][0].content

    # 从状态中获取检索结果
    retrieved_docs = state.get("retrieved_documents", [])
    metadata = state.get("retrieval_metadata")

    if retrieved_docs:
        context = "\n\n".join([
            f"[来源: {doc.metadata.get('filename', 'unknown')}] {doc.page_content}"
            for doc in retrieved_docs
        ])
        logger.info(f"生成答案: 使用 {len(retrieved_docs)} 个检索文档")
    else:
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