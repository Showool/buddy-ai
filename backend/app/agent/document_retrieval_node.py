import logging
from langchain_core.runnables import RunnableConfig
from .state import AgentState
from ..services.hybrid_retrieval import hybrid_retrieval, RetrievalItem
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def document_retrieval_node(state: AgentState, config: RunnableConfig) -> dict:
    """文档检索节点 - 使用混合检索（向量+全文搜索+RRF融合）"""
    query = state.get("question", "") or ""
    user_id = config["configurable"].get("user_id")

    logger.info(f"文档检索: query={query[:50]}..., user_id={user_id}")

    try:
        # 调用混合检索服务
        results: list[RetrievalItem] = hybrid_retrieval.retrieve(
            query=query,
            user_id=user_id,
            top_k=4,
            min_similarity=0.5,
        )

        # 检查是否可以直接返回（高相似度跳过LLM）
        direct_content = hybrid_retrieval.should_direct_return(results)

        # 转换为兼容格式
        documents = [
            Document(page_content=item.content, metadata=item.metadata, similarity=item.similarity)
            for item in results
        ]

        logger.info(f"文档检索完成: 返回 {len(documents)} 个结果")

        # 如果可以直接返回，标记为需要跳过LLM
        if direct_content:
            return {
                "parallel_results": [{"source": "documents", "data": documents}],
                "retrieval_strategy": "direct_return",
                "direct_return": True,
            }

        return {
            "parallel_results": [{"source": "documents", "data": documents}],
            "retrieval_strategy": "hybrid",
        }

    except Exception as e:
        logger.error(f"文档检索失败: {e}")
        return {"parallel_results": [{"source": "documents", "data": []}]}
