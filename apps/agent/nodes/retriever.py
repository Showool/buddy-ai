import logging
from typing import Any

import jieba
from langchain_core.runnables import RunnableConfig

from apps.agent.llm.llm_factory import get_llm
from apps.agent.rag import milvus_vector
from apps.agent.state import GraphState

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "的",
    "是",
    "在",
    "了",
    "什么",
    "如何",
    "怎么",
    "吗",
    "呢",
    "有",
    "和",
    "与",
    "对",
    "把",
    "被",
    "从",
    "到",
    "为",
    "这",
    "那",
    "就",
    "也",
    "都",
    "而",
    "及",
    "着",
    "或",
    "一个",
    "没有",
    "不是",
    "可以",
    "我",
    "你",
    "他",
    "她",
    "它",
    "们",
    "请",
    "能",
    "会",
    "要",
    "让",
    "给",
    "用",
    "很",
    "最",
    "更",
    "还",
    "但",
    "却",
    "只",
    "已",
    "已经",
}


def extract_keywords(text: str) -> str:
    """基于 jieba 分词 + 停用词过滤提取关键词"""
    words = [w for w in jieba.cut(text) if len(w) > 1 and w not in STOP_WORDS]
    return " ".join(words)


def query_transform_HyDE(state: GraphState) -> dict[str, Any]:  # noqa: N802
    """指代消解 + HyDE 查询转换"""
    memory = state.get("memory_context") or "无"
    user_input = state["original_input"]

    query_transform_prompt = f"""你是检索优化专家。你的任务分两步执行：

    ## 输入
    <user_input>{user_input}</user_input>
    <memory_context>{memory}</memory_context>

    ## Step 1：指代消解
    检查 <user_input> 中是否包含代词（它、这个、那个、他、她、上次、之前等）或省略了主语/宾语。
    - 若存在指代或省略：结合 <memory_context> 还原指代对象，生成一个无需上下文即可理解的独立问题。
    - 若不存在指代：直接使用原始问题。

    ## Step 2：假设性文档生成（HyDE）
    基于 Step 1 得到的独立问题，生成一段能完美回答该问题的假设性文档片段。要求：
    - 直接针对问题核心，像一篇专业文档中的段落。
    - 语言简洁，避免冗余铺垫。
    - 字数控制在100字以内。

    ## 输出
    只输出 Step 2 生成的假设性文档片段，不要输出其他任何内容。
    """

    llm = get_llm()
    response = llm.invoke(query_transform_prompt)
    return {
        "enhanced_input": response.content,
    }


def hybrid_search(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    """混合搜索"""
    original_input = state["original_input"]
    user_id: str = config["configurable"].get("user_id", "")
    data = milvus_vector.hybrid_search(original_input, user_id)
    # 假设性文档嵌入 (HyDE)
    enhanced = state.get("enhanced_input")
    if enhanced:
        hyde_data = milvus_vector.vector_search(enhanced, user_id)
        data.extend(hyde_data)
    logger.info(f"混合搜索: {len(data)} 条数据")
    return {"rag_docs": data}


def text_match(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    """文本匹配"""
    original_input = state["original_input"]
    user_id: str = config["configurable"].get("user_id", "")
    keyword = extract_keywords(original_input)
    if not keyword:
        return {"rag_docs": []}
    data = milvus_vector.text_match(original_input, keyword, user_id)
    logger.info("文本匹配: %d 条数据", len(data))
    return {"rag_docs": data}
