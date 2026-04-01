import logging
from langchain_core.messages import HumanMessage
from .state import AgentState
from ..prompt.prompt import (
    REWRITE_KEYWORD_EXTRACTION_PROMPT,
    REWRITE_SIMPLIFICATION_PROMPT,
)
from ..llm.llm_factory import get_llm

logger = logging.getLogger(__name__)


def rewrite_question(state: AgentState) -> dict:
    """改进的重写问题节点 - 基于文档检索结果的智能策略"""
    question = state.get("question", "")
    loop_step = state.get("loop_step", 0)

    MAX_RETRIES = 3
    if loop_step >= MAX_RETRIES:
        logger.warning(f"超过最大重试次数 ({MAX_RETRIES})，停止重写")
        return {"routing_decision": "generate_response"}

    # === 基于文档检索结果判断策略 ===
    doc_count = _get_document_count(state.get("parallel_results", []))

    # === 智能策略选择 ===
    strategy = _select_rewrite_strategy(doc_count)

    # 如果策略为 None，表示不重写，直接生成响应
    if strategy is None:
        logger.info(f"检索到 {doc_count} 篇文档，不需要重写")
        return {"routing_decision": "generate_response"}

    # === 生成重写问题 ===
    rewritten_query = _rewrite_with_strategy(question, strategy)

    # === 验证重写结果 ===
    similarity = _calculate_query_similarity(question, rewritten_query)
    if similarity > 0.85:
        logger.info(f"重写结果与原问题过于相似 (相似度: {similarity:.2f})，停止重写")
        return {"routing_decision": "generate_response"}

    logger.info(
        f"重写问题: '{question}' -> '{rewritten_query}', 策略: {strategy}, 文档数: {doc_count}, 次数: {loop_step}"
    )

    return {
        "messages": [HumanMessage(content=rewritten_query)],
        "loop_step": loop_step + 1,
        "question": rewritten_query,
        "routing_decision": None,
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


def _get_document_count(parallel_results: list) -> int:
    """从并行结果中获取文档数量（仅分析文档检索结果，忽略记忆）"""
    for result in parallel_results:
        if result.get("source") == "documents":
            return len(result.get("data", []))
    return 0


def _select_rewrite_strategy(doc_count: int) -> str:
    """基于文档检索结果智能选择重写策略

    策略选择逻辑：
    | 文档数量 | 策略 |
    |----------|------|
    | 0篇      | 关键词提取（重写） |
    | 1-3篇    | 不重写，直接生成响应 |
    | 大于3篇  | 简化表达（重写） |

    返回策略名称，或 None 表示不重写
    """
    if doc_count == 0:
        return "keyword_extraction"
    elif 1 <= doc_count <= 3:
        return None  # 不重写，直接生成响应
    else:
        return "simplification"


def _rewrite_with_strategy(question: str, strategy: str) -> str:
    """根据策略重写问题"""
    # 策略到Prompt的映射
    strategy_prompt_map = {
        "keyword_extraction": REWRITE_KEYWORD_EXTRACTION_PROMPT,
        "simplification": REWRITE_SIMPLIFICATION_PROMPT,
    }

    prompt_template = strategy_prompt_map.get(strategy)
    if not prompt_template:
        return question  # 如果没有匹配的prompt，返回原问题
    prompt = prompt_template.format(question=question)

    response = get_llm().invoke([{"role": "user", "content": prompt}])
    return response.content.strip()
