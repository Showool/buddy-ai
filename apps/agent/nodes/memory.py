"""
Mem0 记忆中间件 - 在 LangGraph 节点执行前后自动管理记忆

使用方式：
    在 graph 编译后，通过 with_config 注入 user_id，
    中间件会自动在对话前检索相关记忆、对话后存储新记忆。
"""

import logging
from langchain_core.runnables import RunnableConfig
from apps.agent.memory import get_memory
from apps.agent.state import GraphState

logger = logging.getLogger(__name__)


def retrieve_memories(state: GraphState, config: RunnableConfig) -> dict:
    """
    检索记忆节点 - 在生成回复前调用

    从 mem0 中搜索与当前用户输入相关的历史记忆，
    拼接为 memory_context 注入到 state 中。
    """
    user_id = config["configurable"].get("user_id")
    query = state.get("original_input", "")

    if not user_id or not query:
        logger.debug("缺少 user_id 或 original_input，跳过记忆检索")
        return {"memory_context": None}

    try:
        mem = get_memory()
        results = mem.search(query, user_id=user_id, limit=3, threshold=0.7)

        # mem0 返回格式: list[dict] 或 {"results": [...]}
        memories = results if isinstance(results, list) else results.get("results", [])

        if not memories:
            logger.debug("未找到相关记忆: user_id=%s", user_id)
            return {"memory_context": None}

        # 拼接记忆上下文
        lines = [f"- {m.get('memory', '')}" for m in memories if m.get("memory")]
        context = "以下是与用户历史对话相关的记忆:\n" + "\n".join(lines)

        logger.info("检索到 %d 条相关记忆: user_id=%s", len(lines), user_id)
        return {"memory_context": context}

    except Exception as e:
        logger.warning("记忆检索失败: %s", e)
        return {"memory_context": None}


def save_memories(state: GraphState, config: RunnableConfig) -> dict:
    """
    存储记忆节点 - 在生成回复后调用

    将本轮用户输入和 AI 回复存入 mem0。
    """
    user_id = config["configurable"].get("user_id")
    original_input = state.get("original_input", "")
    final_answer = state.get("final_answer", "")

    if not user_id or not original_input or not final_answer:
        return {}

    try:
        mem = get_memory()

        # 语义去重：检查是否已存在高度相似的记忆
        existing = mem.search(original_input, user_id=user_id, limit=1, threshold=0.95)
        duplicates = existing if isinstance(existing, list) else existing.get("results", [])
        if duplicates:
            logger.info("已存在相似记忆，跳过存储: user_id=%s", user_id)
            return {}

        interaction = [
            {
                "role": "user",
                "content": original_input
            },
            {
                "role": "assistant",
                "content": final_answer
            }
        ]
        mem.add(interaction, user_id=user_id)
        logger.info("记忆已存储: user_id=%s", user_id)

    except Exception as e:
        logger.warning("记忆存储失败: %s", e)

    return {}
