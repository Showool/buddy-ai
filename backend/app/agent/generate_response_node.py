from langchain_core.runnables import RunnableConfig

from .state import AgentState
from ..llm.llm_factory import get_llm
from ..tools.web_search_tool import tavily_search
from ..tools.user_tool import save_conversation_memory

logger = __import__('logging').getLogger(__name__)


def generate_response(state: AgentState, config: RunnableConfig) -> dict:
    """统一响应节点 - 始终绑定工具"""
    user_id = config["configurable"]["user_id"]
    question = state["question"]
    print(f"用户问题: {question}")

    retrieved_docs = state.get("retrieved_documents", [])
    user_memories = state.get("user_memories", [])
    has_context = bool(retrieved_docs or user_memories)

    context_parts = []
    if user_memories:
        memory_context = "\n".join([f"- {m['data']}" for m in user_memories])
        context_parts.append(f"【用户记忆】\n{memory_context}")
    if retrieved_docs:
        doc_context = "\n\n".join([d.page_content for d in retrieved_docs])
        context_parts.append(f"【知识库】\n{doc_context}")

    if has_context:
        system_msg = f"""你是一个智能助手，用户ID: {user_id}

        【已检索到以下上下文信息】
        {chr(10).join(context_parts)}

        规则：
        1. 优先使用上述上下文回答
        2. 如需补充信息，使用 tavily_search
        3. 如果用户输入个人信息、偏好、历史对话、日程、约定等，需调用 save_conversation_memory
        4. 已检索到以下上下文信息，不需要保存记忆

        用户输入内容：{question}
        """
    else:
        system_msg = f"""你是一个智能助手，用户ID: {user_id}

        【没有检索到相关上下文】

        规则：
        1. 使用工具获取信息：tavily_search
        2. 如果用户输入个人信息、偏好、历史对话、日程、约定等，需调用 save_conversation_memory
        3. 已检索到以下上下文信息，不需要保存记忆

        用户输入内容：{question}
        """

    response = get_llm().bind_tools([tavily_search, save_conversation_memory]).invoke([
        {"role": "system", "content": system_msg}
    ])

    return {"messages": [response]}

