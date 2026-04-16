from langchain_core.messages import SystemMessage

from apps.agent.llm.llm_factory import get_llm
from apps.agent.state import GraphState
from apps.agent.tools import get_tools
from apps.agent.utils.message_summarizer import summarize_and_prune_messages


def generate_response(state: GraphState) -> dict:
    """统一响应节点 - ReAct 模式"""
    if (state["reflection"] and state["reflection"].passed) or state["reflection_count"] >= 3:
        return {"final_answer": state["draft_answer"]}

    retrieval_data = "/n".join([d["document_text"] for d in state["rag_docs"]]) if state["rag_docs"] else ""
    feedback = state["reflection"].feedback if state["reflection"] else ""

    GENERATE_RESPONSE_PROMPT = f"""
    你是知识问答助手。基于提供的上下文信息回答用户问题，必要时调用工具补充信息。

    ## 上下文信息
    <user_input>{state['original_input']}</user_input>
    <enhanced_input>{state['enhanced_input'] or "无"}</enhanced_input>
    <memory_context>{state['memory_context'] or "无"}</memory_context>
    <retrieval_data>{retrieval_data or "无"}</retrieval_data>
    <feedback>{feedback or "无"}</feedback>

    ## 思维链（Chain-of-Thought）——你必须在内部严格按以下步骤逐步推理，再输出最终回答：

    Step 1 - 理解问题：
      从 <user_input> 提取用户的核心问题是什么？有哪些关键实体、约束条件？
      <enhanced_input> 是否提供了更精确的问题表述？

    Step 2 - 证据检索：
      逐一审查 <memory_context> 和 <retrieval_data>，标记与核心问题直接相关的信息片段。
      对每条信息判断：与问题相关(R)/无关(I)/部分相关(P)。仅采纳 R 和 P 类信息。

    Step 3 - 充分性判断：
      基于 Step 2 收集的证据，能否完整回答用户问题？
      - 若证据充分 → 进入 Step 5。
      - 若证据不足 → 进入 Step 4，明确缺失的具体信息点。

    Step 4 - 工具调用（仅在证据不足时执行）：
      根据缺失信息选择合适工具：
      - 需要实时搜索或事实查询 → 调用 tavily_search_tool。
      - 需要百科知识或概念解释 → 调用 wiki_tool。
      约束：最多调用 3 次工具。调用后回到 Step 2 重新评估证据。

    Step 5 - 组织回答：
      仅基于 Step 2 中标记为 R/P 的证据和工具返回结果生成回答。
      对每个论点标注其来源（记忆/检索/工具结果）。
      若某部分无法找到依据，明确告知用户"该信息暂无可靠来源"，禁止猜测或编造。

    ## 严格约束
    - 禁止编造：回答中的每个事实性陈述都必须能追溯到上下文信息或工具返回结果。
    - 无证据则承认：当信息不足且工具也无法补充时，直接告知用户，不要强行回答。
    - 区分确定与推测：确定性结论用陈述句，推理性结论需加"根据现有信息推断"等限定词。

    ## 输出规范
    - 直接输出最终回答，不要输出思维链的中间推理过程。
    - 结构：先给出核心结论，再分点说明依据。
    - 风格：正式客观，简洁准确。
    - 字数：200字以内，复杂问题可扩展至300字。
    """

    llm = get_llm()
    llm_with_tools = llm.bind_tools(tools=get_tools)

    # 每次调用 LLM 前，判断是否需要摘要压缩并回写 state
    messages = state.get("messages", [])
    prune_updates = summarize_and_prune_messages(messages, llm)

    # 如果做了摘要压缩，用压缩后的 messages 调用 LLM
    if prune_updates is not None:
        # 从 prune_updates 中提取非 RemoveMessage 的消息作为上下文
        from langchain_core.messages import RemoveMessage
        compressed_messages = [m for m in prune_updates if not isinstance(m, RemoveMessage)]
        # 加上保留的最近消息（未被删除的部分）
        removed_ids = {m.id for m in prune_updates if isinstance(m, RemoveMessage)}
        recent_messages = [m for m in messages if m.id not in removed_ids]
        llm_messages = compressed_messages + recent_messages
    else:
        prune_updates = []
        llm_messages = messages

    response = llm_with_tools.invoke(
        [SystemMessage(content=GENERATE_RESPONSE_PROMPT)] + llm_messages
    )

    if not response.tool_calls:
        return {"messages": prune_updates, "draft_answer": response.content}

    # 有工具调用时，把摘要更新和 LLM response 一起写入 messages
    return {"messages": prune_updates + [response]}
