from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from .state import GradeDocuments, AgentState
from ..llm.llm_factory import get_llm
from ..prompt.prompt import REWRITE_PROMPT, GRADE_PROMPT
from ..tools.web_search_tool import tavily_search
from ..tools.user_tool import save_conversation_memory

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


def generate_response(state: AgentState, config: RunnableConfig) -> dict:
    """统一响应节点 - 始终绑定工具"""
    user_id = config["configurable"]["user_id"]
    question = state["question"]
    print(f"用户问题: {question}")

    retrieved_docs = state.get("retrieved_documents", [])
    user_memories = state.get("user_memories", [])
    has_context = bool(retrieved_docs or user_memories)

    context_parts = []
    if user_memories:
        memory_context = "\n".join([f"- {m['data']}" for m in user_memories])
        context_parts.append(f"【用户记忆】\n{memory_context}")
    if retrieved_docs:
        doc_context = "\n\n".join([d.page_content for d in retrieved_docs])
        context_parts.append(f"【知识库】\n{doc_context}")

    if has_context:
        system_msg = f"""你是一个智能助手，用户ID: {user_id}

        【已检索到以下上下文信息】
        {chr(10).join(context_parts)}

        规则：
        1. 优先使用上述上下文回答
        2. 如需补充信息，使用 tavily_search
        3. 如果用户输入个人信息、偏好、历史对话、日程、约定等，需调用 save_conversation_memory
        4. 已检索到以下上下文信息，不需要保存记忆

        用户输入内容：{question}
        """
    else:
        system_msg = f"""你是一个智能助手，用户ID: {user_id}

        【没有检索到相关上下文】

        规则：
        1. 使用工具获取信息：tavily_search
        2. 如果用户输入个人信息、偏好、历史对话、日程、约定等，需调用 save_conversation_memory
        3. 已检索到以下上下文信息，不需要保存记忆

        用户输入内容：{question}
        """

    response = get_llm().bind_tools([tavily_search, save_conversation_memory]).invoke([
        {"role": "system", "content": system_msg}
    ])

    return {"messages": [response]}


def rewrite_question(state: AgentState) -> dict:
    """重写问题（防止死循环）"""
    messages = state["messages"]
    question = messages[0].content
    loop_step = state.get("loop_step", 0)
    query_history = state.get("query_history", [])

    MAX_RETRIES = 3
    if loop_step >= MAX_RETRIES:
        logger.warning(f"超过最大重试次数 ({MAX_RETRIES})，停止重写")
        return {
            "messages": [HumanMessage(content=question)],
            "loop_step": loop_step + 1,
            "routing_decision": "generate_response"
        }

    # 检测重复查询
    current_query_normalized = question.lower().strip()
    for prev_query in query_history[-3:]:
        if _calculate_query_similarity(current_query_normalized, prev_query.lower().strip()) > 0.9:
            logger.warning("检测到重复查询，停止重写")
            return {
                "messages": [HumanMessage(content=question)],
                "loop_step": loop_step + 1,
                "routing_decision": "generate_response"
            }

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
        "query_history": query_history + [question],
        "routing_decision": None
    }


def grade_documents(state: AgentState) -> dict:
    """确定检索到的文件是否与问题相关，返回状态更新."""
    question = state["messages"][0].content
    context = state["messages"][-1].content

    loop_step = state.get("loop_step", 0)
    if loop_step >= 3:
        return {"routing_decision": "generate_response"}

    prompt = GRADE_PROMPT.format(question=question, context=context)
    response = (
        get_llm()
        .with_structured_output(GradeDocuments).invoke(
            [{"role": "user", "content": prompt}]
        )
    )
    score = response.binary_score
    if score == "yes":
        print(f"Documents are relevant, generating response")
        return {"routing_decision": "generate_response"}
    else:
        print(f"Rewriting question: {question}, times: {loop_step}")
        return {"routing_decision": "rewrite_question"}


def grade_routing_condition(state: AgentState) -> str:
    """基于 grade_documents 的路由决策来决定下一步."""
    return state.get("routing_decision", "generate_response")