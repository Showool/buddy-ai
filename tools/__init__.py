from .system_tool import clear_conversation, update_user_name, retrieve_context, retriever_tool
from .user_tool import get_weather_for_location, get_user_location, get_user_info, save_user_info, retrieve_memory, \
    save_memory
from .web_search_tool import tavily_search


def get_tools():
    """
    获取所有可用的工具列表
    """
    return [
        clear_conversation,
        update_user_name,
        get_weather_for_location,
        # get_user_location,
        # get_user_info,
        # save_user_info,
        retrieve_context,
        tavily_search,
        retriever_tool,
        retrieve_memory,
        save_memory
    ]


__all__ = [
    "clear_conversation",
    "update_user_name", 
    "get_weather_for_location",
    # "get_user_location",
    # "get_user_info",
    # "save_user_info",
    "get_tools",
    "retrieve_context",
    "tavily_search",
    "retriever_tool",
    "retrieve_memory",
    "save_memory"
]