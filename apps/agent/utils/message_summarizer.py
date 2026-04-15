"""
Messages 摘要压缩工具
保留最近 N 条消息，超出部分用 LLM 生成摘要，
通过 RemoveMessage 删除旧消息并插入摘要 SystemMessage 回写 state。
"""
import logging
from langchain_core.messages import SystemMessage, ToolMessage, RemoveMessage

logger = logging.getLogger(__name__)

KEEP_RECENT = 5  # 保留最近 N 条消息


def summarize_and_prune_messages(messages: list, llm, keep_recent: int = KEEP_RECENT) -> list | None:
    """
    对 messages 进行摘要压缩，返回需要回写 state 的 messages 更新列表。
    - 总条数 <= keep_recent 时返回 None（无需更新）
    - 否则：返回 [RemoveMessage(...), ..., SystemMessage(摘要)]
    """
    if len(messages) <= keep_recent:
        return None

    split_index = _find_safe_split_index(messages, keep_recent)
    if split_index <= 0:
        return None

    old_messages = messages[:split_index]

    try:
        summary = _generate_summary(old_messages, llm)
    except Exception as e:
        logger.warning("消息摘要生成失败，跳过压缩: %s", e)
        return None

    # 构建 state 更新：删除旧消息 + 插入摘要
    updates = []
    for msg in old_messages:
        updates.append(RemoveMessage(id=msg.id))
    updates.append(SystemMessage(content=f"以下是之前对话的摘要:\n{summary}"))

    return updates


def _find_safe_split_index(messages: list, keep_recent: int) -> int:
    """
    找到安全的切割点，确保不会把 AIMessage(tool_calls) 和对应的 ToolMessage 拆开。
    """
    index = len(messages) - keep_recent

    # 如果切割点处是 ToolMessage，向前移动直到找到非 Tool 消息
    while index > 0 and isinstance(messages[index], ToolMessage):
        index -= 1

    return max(index, 0)


def _generate_summary(messages: list, llm) -> str:
    """用 LLM 对旧消息生成摘要"""
    parts = []
    for msg in messages:
        if msg.content:
            role = getattr(msg, "type", "unknown")
            parts.append(f"{role}: {msg.content}")

    conversation = "\n".join(parts)

    summary_prompt = (
        "请对以下对话历史生成简洁摘要，保留关键信息和上下文：\n\n"
        f"{conversation}\n\n"
        "摘要要求：\n"
        "- 保留用户的核心问题和意图\n"
        "- 保留重要的工具调用结果\n"
        "- 保留关键的回答结论\n"
        "- 控制在 200 字以内"
    )

    result = llm.invoke(summary_prompt)
    return result.content
