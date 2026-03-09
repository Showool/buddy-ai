
from langchain_core.messages import HumanMessage
from .state import AgentState
from ..prompt.prompt import REWRITE_PROMPT
from ..llm.llm_factory import get_llm

logger = __import__('logging').getLogger(__name__)

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
