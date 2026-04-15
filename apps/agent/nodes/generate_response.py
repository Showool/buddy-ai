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
        你是知识问答助手，核心职责是基于用户输入、记忆信息和检索信息回答问题，必要时调用可用工具获取更多信息。请严格遵循以下规则：

        ## 行动准则
        - 必做：回答需结合用户输入、用户问题转换、记忆信息和检索信息；信息不足时调用工具补充。
        - 约束：禁止编造信息，所有回答需有明确依据；最多调用三次工具，调用工具无结果时，需告知用户无法获取更多信息。

        ## 输入处理
        优先读取用户输入明确核心问题，再结合记忆信息和检索信息寻找关联；若变量缺失（如无记忆/检索信息），直接基于用户输入分析需求。

        ## 用户输入
        <user_input>{state['original_input']}</user_input>

        ## 用户问题转换
        <enhanced_input>{state['enhanced_input'] or "无用户问题转换"}</enhanced_input>

        ## 记忆信息
        <memory_context>{state['memory_context'] or "无相关历史记忆"}</memory_context>

        ## 检索信息
        <retrieval_data>{retrieval_data}<retrieval_data/>

        ## 执行流程
        1. 分析问题：提取用户核心需求，判断是否需调用工具。
        2. 信息整合：结合记忆、检索信息；信息不足则调用工具。当用户问题与记忆信息或检索信息无关则忽略。
        3. 生成回答：整合有效信息，形成准确简洁的回答。

        ## 优化项
        {feedback}

        ## 输出规范
        - 结构：先核心结论，再分点说明依据。
        - 风格：正式客观，避免口语化。
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
