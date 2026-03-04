from typing import Any
from langchain.tools import tool

from langgraph.store.postgres import PostgresStore
import os
from ..llm.llm_factory import get_llm
import uuid

from ..prompt.prompt import SUMMARIZE_MEMORY_PROMPT


# Memory retrieval tool
@tool
def retrieve_memory(query: str, user_id: str) -> str:
    """Retrieve user memories based on query using provided user_id."""
    print(f"Retrieving memories for user {user_id}: {query}")

    # 连接到存储
    with PostgresStore.from_conn_string(os.getenv("POSTGRESQL_URL")) as store:
        namespace = ("memories", user_id)

        # Search for memories using the query
        memories = store.search(namespace, query=query)

        if memories:
            info_list = [d.value["data"] for d in memories]
            formatted_info = "\n【用户信息】" + "\n【用户信息】".join(info_list)
            return formatted_info
        else:
            return "未找到相关的记忆信息。"


# 判断是否需要保存对话记忆的提示词
SHOULD_SAVE_CONVERSATION_PROMPT = """分析以下对话内容，判断是否需要保存到用户长期记忆。

用户ID: {user_id}
用户问题: {question}
AI回答: {answer}

判断标准：
- 用户提到的个人信息（姓名、年龄、职业等）
- 用户的偏好、喜好、习惯
- 重要事件、约定、承诺
- 其他值得长期记住的信息

如果需要保存，返回 "YES" 并简要说明原因；如果不需要，返回 "NO"。
"""


def should_save_conversation_memory(question: str, answer: str, user_id: str) -> tuple[bool, str]:
    """判断对话内容是否需要保存到记忆"""
    prompt = SHOULD_SAVE_CONVERSATION_PROMPT.format(
        user_id=user_id,
        question=question,
        answer=answer
    )
    response = get_llm().invoke([{"role": "user", "content": prompt}])
    content = response.content.strip().upper()

    if "YES" in content:
        reason = content.replace("YES", "").strip()
        return True, reason if reason else "用户提供了重要信息"
    return False, ""


# 保存对话记忆工具
@tool
def save_conversation_memory(question: str, answer: str, user_id: str) -> str:
    """保存对话内容到用户长期记忆。工具会自动判断是否需要保存，并总结重要信息。

    Args:
        question: 用户的问题
        answer: AI的回答
        user_id: 用户ID

    Returns:
        保存结果信息
    """
    # 判断是否需要保存
    should_save, reason = should_save_conversation_memory(question, answer, user_id)

    if not should_save:
        return "对话内容无需保存到长期记忆。"

    # 使用LLM总结需要记住的内容
    prompt = SUMMARIZE_MEMORY_PROMPT.format(user_message=f"用户问题: {question}\nAI回答: {answer}")
    response = get_llm().invoke([{"role": "user", "content": prompt}])
    memory_summary = response.content

    # 连接到存储并保存记忆
    with PostgresStore.from_conn_string(os.getenv("POSTGRESQL_URL")) as store:
        namespace = ("memories", user_id)
        store.put(namespace, str(uuid.uuid4()), {"data": memory_summary})

    return f"已保存记忆: {memory_summary}"