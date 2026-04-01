"""用户记忆工具 - LangGraph Runtime Store 集成"""

from langchain.tools import tool

from ..memory.memory_service import memory_service


# 保存对话记忆工具
@tool
def save_conversation_memory(question: str, answer: str, user_id: str) -> str:
    """保存对话内容到用户长期记忆

    Args:
        question: 用户的问题
        answer: AI的回答
        user_id: 用户ID

    Returns:
        保存结果信息
    """

    return memory_service.save_memory(user_id, question, answer)
