"""
统一检索工具 - 整合所有检索能力

替代原有的三个检索工具：
- retrieve_context
- retriever_tool
- hybrid_retrieve_context
"""
from typing import Optional
from langchain.tools import tool

from app.services.retrieval_orchestrator import retrieval_orchestrator
import logging

logger = logging.getLogger(__name__)

RETRIEVAL_K = 6
RETRIEVAL_SCORE_THRESHOLD = 0.5


@tool
def search_knowledge_base(
    query: str,
    user_id: Optional[str] = None,
    max_results: int = RETRIEVAL_K
) -> str:
    """
    从知识库中检索相关信息，用于回答用户问题。

    功能特点：
    - 混合检索：结合向量搜索和全文搜索
    - 智能重排：使用LLM对结果进行重排序
    - 用户隔离：自动过滤用户文档

    Args:
        query: 搜索查询，描述你想要找的信息
        user_id: 用户ID，系统会自动传入
        max_results: 返回的最大结果数量（默认6）

    使用场景：
    - 用户问文档中的内容
    - 用户问产品说明、使用方法
    - 需要引用文档来源时

    不使用场景：
    - 查天气、新闻等实时信息
    - 纯闲聊
    """
    try:
        result = retrieval_orchestrator.retrieve(
            query=query,
            user_id=user_id,
            k=max_results,
            use_fulltext=True,
            use_rerank=True,
            rerank_threshold=2
        )

        if not result.documents:
            return "未在知识库中找到相关信息。"

        # 格式化结果
        formatted_parts = []
        for doc, score in zip(result.documents, result.scores):
            # 过滤低分结果
            if score > RETRIEVAL_SCORE_THRESHOLD:
                filename = doc.metadata.get('filename', '未知文档')
                content = doc.page_content[:500]  # 限制长度
                formatted_parts.append(
                    f"【{filename}】(相关度: {1-score:.2f})\n{content}"
                )

        if not formatted_parts:
            return "检索到的文档相关性较低，建议重述问题。"

        return "\n\n".join(formatted_parts)

    except Exception as e:
        logger.error(f"检索失败: {e}")
        return f"检索时出错: {str(e)}"


__all__ = ["search_knowledge_base"]