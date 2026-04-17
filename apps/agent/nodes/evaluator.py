from typing import Any

from langchain_core.messages import ToolMessage

from apps.agent.llm.llm_factory import get_llm
from apps.agent.state import GraphState, ReflectionState


def _extract_tool_results(messages: list[Any]) -> str:
    """从消息历史中提取工具调用返回的结果"""
    tool_results = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_results.append(f"[{msg.name}] {msg.content}")
    return "\n".join(tool_results) if tool_results else "无"


def evaluate_node(state: GraphState) -> dict[str, Any]:
    reflection_count = state["reflection_count"]
    retrieval_data = "\n".join([d["document_text"] for d in state["rag_docs"]]) if state["rag_docs"] else "无"
    memory = state.get("memory_context") or "无"
    enhanced = state.get("enhanced_input") or "无"
    tool_results = _extract_tool_results(state.get("messages", []))

    evaluate_prompt = f"""你是回答质量评估器。综合用户问题、改写后的问题、记忆上下文、检索数据和工具返回结果，判断回答是否合格。

    ## 输入
    <user_input>{state["original_input"]}</user_input>
    <enhanced_input>{enhanced}</enhanced_input>
    <memory_context>{memory}</memory_context>
    <retrieval_data>{retrieval_data}</retrieval_data>
    <tool_results>{tool_results}</tool_results>

    ## 待评估回答
    <answer>{state["draft_answer"]}</answer>

    ## 评估流程（逐步执行）

    Step 1 - 还原完整问题：
    结合 <user_input>、<enhanced_input> 和 <memory_context>，理解用户的真实意图。<enhanced_input> 是经过指代消解和查询改写后的问题，比原始输入更精确地表达了用户意图，优先以它作为评估的核心问题。若 <enhanced_input> 为"无"，则基于 <user_input> 和 <memory_context> 还原。列出用户的核心问题和所有关键子问题。

    Step 2 - 构建事实基准：
    从 <memory_context>、<retrieval_data> 和 <tool_results> 中提取与用户问题直接相关的事实信息，作为评估 <answer> 的参考基准。标记每条信息的来源（记忆/检索/工具）。
    注意：<tool_results> 包含 wiki_tool（维基百科）和 tavily_search_tool（网络搜索）的返回结果，是回答的合法信息来源。

    Step 3 - 逐维度评估（任一不通过则整体不合格）：

      3.1 相关性：<answer> 是否针对 Step 1 还原后的完整问题？是否答非所问或偏离主题？

      3.2 事实准确性：<answer> 中的事实性陈述是否与 Step 2 的事实基准一致？是否存在与记忆、检索数据或工具返回结果矛盾的内容？是否编造了所有参考信息中均不存在的事实？

      3.3 完整性：Step 1 中列出的关键子问题是否都被 <answer> 覆盖？记忆、检索和工具返回中的重要相关信息是否被合理利用？

      3.4 逻辑一致性：<answer> 内部是否前后矛盾？推理是否合理？

    Step 4 - 输出结论：
    若 4 个维度全部通过 → passed: true。
    若任一不通过 → passed: false，feedback 中指明不合格维度、具体问题、改进方向。

    ## 特殊情况
    - 若 <memory_context>、<retrieval_data> 和 <tool_results> 均为"无"：跳过 3.2 事实准确性检查，仅评估相关性、完整性和逻辑一致性。
    - 若 <answer> 明确告知用户信息不足无法回答，且所有参考信息确实不足以支撑回答：视为合格。
    - 若用户问题涉及记忆中的历史对话内容，但 <answer> 未利用记忆信息导致回答不完整或不准确：判定完整性或准确性不通过。

    ## 输出格式
    严格输出 JSON，不附加任何额外文字。不要输出中间推理过程。

    {{
      "passed": true,
      "feedback": ""
    }}

    或

    {{
      "passed": false,
      "feedback": "【不合格维度】具体问题描述。【改进方向】如何修正。"
    }}
    """
    llm_with_schema = get_llm().with_structured_output(ReflectionState, method="json_mode")
    response = llm_with_schema.invoke(evaluate_prompt)
    return {"reflection": response, "reflection_count": reflection_count + 1}
