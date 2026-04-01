import logging

from langchain.tools import tool
from langchain_tavily import TavilySearch

logger = logging.getLogger(__name__)


# 创建Tavily搜索工具
@tool
def tavily_search(query: str):
    """
    使用Tavily搜索引擎在网络上搜索信息。

    Args:
        query (str): 搜索查询字符串

    Returns:
        tuple: 返回搜索结果字符串和原始搜索结果
    """
    # 初始化Tavily搜索工具
    search = TavilySearch(max_results=3)

    # 执行搜索
    search_results = search.invoke({"query": query})

    logger.debug(
        f"Tavily搜索结果数量：{len(search_results) if isinstance(search_results, list) else 1}"
    )
    logger.info(
        f"Tavily搜索完成: query='{query}', 结果数={len(search_results) if isinstance(search_results, list) else 1}"
    )

    return search_results
