from typing import Any
from langchain.tools import tool, ToolRuntime

from agent.agent_context import Context


@tool
def get_weather_for_location(city: str, runtime: ToolRuntime) -> str:
    """Get weather for a given city."""
    writer = runtime.stream_writer

    # 在工具执行时流式自定义更新
    writer(f"Looking up data for city: {city}")
    writer(f"Acquired data for city: {city}")

    return f"{city}的天气总是晴朗的!"


@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """Retrieve user information based on user ID."""
    user_id = runtime.context.user_id
    return "深圳" if user_id == "1" else "中国"


# Access memory
@tool
def get_user_info(runtime: ToolRuntime[Context]) -> str:
    """Look up user info."""
    user_id = runtime.context.user_id
    store = runtime.store
    user_info = store.get(("users",), user_id)
    return str(user_info.value) if user_info else "未知用户"


# Update memory
@tool
def save_user_info(user_info: dict[str, Any], runtime: ToolRuntime[Context]) -> str:
    """Save user info."""
    user_id = runtime.context.user_id
    store = runtime.store
    store.put(("users",), user_id, user_info)
    return "保存用户信息成功。"
