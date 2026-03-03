from langgraph.types import Command
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langchain.tools import tool, ToolRuntime
from typing import Optional

from ..retriever.get_retriever import get_retriever, get_retriever_with_user_filter
from ..retriever.vector_store import get_vector_store, get_vector_retriever


# 通过删除所有消息来更新对话记录
@tool
def clear_conversation() -> Command:
    """Clear the conversation history."""

    return Command(
        update={
            "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)],
        }
    )


# 更新代理状态中的 user_name
@tool
def update_user_name(
        new_name: str,
        runtime: ToolRuntime
) -> Command:
    """Update the user's name."""
    return Command(update={"user_name": new_name})


# Construct a tool for retrieving context
@tool(response_format="content_and_artifact")
def retrieve_context(query: str, user_id: Optional[str] = None):
    """检索信息来帮助回答查询，会根据用户ID过滤文档。

    Args:
        query: 搜索查询
        user_id: 用户ID，用于过滤文档（可选）
    """
    if user_id:
        # 使用带用户过滤的检索器
        retrieved_docs = get_vector_retriever(k=2, user_id=user_id).invoke(query)
    else:
        # 使用普通检索器
        retrieved_docs = get_vector_store().similarity_search(query, k=2)

    print(f"检索到的文件数： {len(retrieved_docs)} ")
    serialized = "\n\n".join(
        f"Source: {doc.metadata}\nContent: {doc.page_content}"
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs


@tool
def retriever_tool(query: str, user_id: Optional[str] = None) -> str:
    """
    搜索并返回关于文档的信息。

    会根据提供的 user_id 过滤只检索该用户的文档。

    Args:
        query: 搜索查询
        user_id: 用户ID，用于过滤文档（可选）
    """
    if user_id:
        # 使用带用户过滤的检索器
        docs = get_retriever_with_user_filter(user_id).invoke(query)
    else:
        # 使用普通检索器（检索所有用户的文档）
        docs = get_retriever().invoke(query)
    return "\n\n".join([doc.page_content for doc in docs])


@tool
async def hybrid_retrieve_context(
    query: str,
    user_id: Optional[str] = None,
    k: int = 4,
    use_fulltext: bool = True,
    use_rerank: bool = True
) -> str:
    """
    使用混合检索方式获取知识库内容

    混合检索结合了向量搜索和全文搜索，并使用重排序提升结果质量。

    Args:
        query: 查询文本
        user_id: 用户ID（可选，用于过滤）
        k: 返回结果数量
        use_fulltext: 是否使用全文搜索
        use_rerank: 是否使用重排序

    Returns:
        str: 检索结果文本
    """
    from app.services.retrieval_orchestrator import retrieval_orchestrator

    result = await retrieval_orchestrator.retrieve(
        query=query,
        user_id=user_id,
        k=k,
        use_fulltext=use_fulltext,
        use_rerank=use_rerank
    )

    # 格式化结果
    formatted = []
    for doc, score in zip(result.documents, result.scores):
        formatted.append(
            f"[相关度: {score:.2f}]\n"
            f"来源: {doc.metadata.get('filename', '未知')}\n"
            f"内容: {doc.page_content}"
        )

    return "\n\n".join(formatted)