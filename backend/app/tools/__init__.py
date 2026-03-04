from .retrieval_tool import search_knowledge_base
from .user_tool import retrieve_memory, save_conversation_memory
from .web_search_tool import tavily_search


def get_tools():
    """
    获取所有可用的工具列表
    """
    return [
        # 检索工具（唯一入口）
        search_knowledge_base,

        # 记忆管理
        retrieve_memory,
        save_conversation_memory,

        # 实时信息
        tavily_search,
    ]


__all__ = [
    "search_knowledge_base",
    "retrieve_memory",
    "save_conversation_memory",
    "tavily_search",
    "get_tools",
]