from typing import Any

from apps.agent.llm.llm_factory import get_llm
from apps.agent.state import GraphState, QueryTransformSchema


def query_transform(state: GraphState) -> dict[str, Any]:
    """查询转换"""
    memory = state.get("memory_context") or "无"
    user_input = state["original_input"]

    query_transform_prompt = f"""你是查询改写器。根据用户的原始问题和记忆上下文，将问题改写为更适合检索的独立查询。

    ## 记忆上下文
    <memory_context>{memory}</memory_context>

    ## 用户原始问题
    <user_input>{user_input}</user_input>

    ## 改写规则（按优先级依次判断）

    ### 规则1：指代消解（最高优先级）
    若原始问题中包含代词（它、这个、那个、他、她、上次、之前、刚才等）或省略了主语/宾语，必须结合 <memory_context> 还原指代对象，将问题改写为无需上下文即可理解的独立问题。
      示例：
      - 记忆："用户之前询问了Python的GIL机制"
      - 原始问题："它会影响多线程性能吗？"
      - 改写后："Python的GIL机制会影响多线程性能吗？"

    ### 规则2：退步提示（Step-Back Prompting）
    若问题细节繁多或过于具体（含大量时间、地点、型号等限定词），退后一步生成更概括的问题，保留核心意图，去除不影响检索的冗余细节。
      示例：
      - 原始问题："2023年3月15日在北京朝阳区某商场买的XX品牌A123笔记本，用3天屏幕闪烁怎么维权？"
      - 改写后："购买笔记本电脑短期内出现屏幕质量问题如何维权？"

    ### 规则3：查询扩展
    若问题过于简短或关键词有限，改写为更清晰具体、利于检索的叙述。
      示例：
      - 原始问题："电脑蓝屏"
      - 改写后："电脑出现蓝屏故障的常见原因和解决方法"

    ### 规则4：无需改写
    若问题已经具体、清晰、无指代、适合检索，不做改写。

    ## 输出格式
    严格输出 JSON，不附加任何额外文字。

    - transform_flag：布尔值，true 表示已改写，false 表示未改写。
    - result：改写后的问题（未改写时为原始问题原文）。改写后字数≤100字。
    """

    llm_with_schema = get_llm().with_structured_output(QueryTransformSchema, method="json_mode")
    response: QueryTransformSchema = llm_with_schema.invoke(query_transform_prompt)
    if response.transform_flag:
        return {
            "enhanced_input": response.result,
        }
    else:
        return {}
