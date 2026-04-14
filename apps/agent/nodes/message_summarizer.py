"""
Messages 摘要压缩工具
保留最近 N 条消息，超出部分用 LLM 生成摘要替换为 SystemMessage。
"""
import logging
from langchain_core.messages import SystemMessage, ToolMessage

logger = logging.getLogger(__name__)

KEEP_RECENT = 5  # 保留最近 N 条消息


def summarize_messages(messages: list, llm, keep_recent: int = KEEP_RECENT) -> list:
    """
    对 messages 进行摘要压缩。
    - 总条数 <= keep_recent 时直接返回原始 messages
    - 否则：旧消息用 LLM 摘要 → SystemMessage，拼接最近 keep_recent 条
    """
    if len(messages) <= keep_recent:
        return messages

    split_index = _find_safe_split_index(messages, keep_recent)
    if split_index <= 0:
        return messages

    old_messages = messages[:split_index]
    recent_messages = messages[split_index:]

    try:
        summary = _generate_summary(old_messages, llm)
        summary_msg = SystemMessage(content=f"以下是之前对话的摘要:\n{summary}")
        return [summary_msg] + recent_messages
    except Exception as e:
        logger.warning("消息摘要生成失败，使用原始 messages: %s", e)
        return messages


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
