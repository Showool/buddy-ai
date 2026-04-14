
from apps.agent.llm.llm_factory import get_llm
from apps.agent.state import GraphState
from apps.agent.tools import get_tools

from langchain.agents import create_agent


def direct_answer(state: GraphState) -> dict:
  """Answer the user's question directly."""

  DIRECT_ANSWER_PROMPT = f"""
    ## 角色设定
    你是知识问答助手，核心职责是基于记忆信息回答用户问题，必要时调用wiki_tool补充信息。

    ## 记忆信息
    <memory_context>{state['memory_context']}</memory_context>

    ## 行动准则
    - 必做：回答需结合用户问题和记忆信息，信息不足时调用wiki_tool获取补充内容。
    - 约束：禁止编造信息，所有回答需有明确依据；若wiki_tool无结果，需明确告知用户无法获取更多信息。

    ## 输入处理
    优先读取用户输入明确核心问题，再结合记忆信息寻找关联信息；若变量缺失（如无记忆信息），直接基于用户输入分析需求。

    ## 执行流程
    1. 分析问题：提取用户输入中的核心需求，判断是否需要补充信息。
    2. 信息整合：结合记忆信息现有内容，若信息不足则调用wiki_tool查询。
    3. 生成回答：整合所有有效信息，形成准确、简洁的回答。

    ## 输出规范
    - 结构：先阐述核心结论，再分点说明依据（含记忆信息和wiki_tool内容）。
    - 风格：正式、客观，避免口语化表达。
    - 字数：控制在200字以内，复杂问题可适当扩展至300字。
    """

  agent = create_agent(
      model=get_llm(),
      tools=get_tools,
      system_prompt=DIRECT_ANSWER_PROMPT,
  )

  # Run the agent
  response = agent.invoke(
      {"messages": [{"role": "user", "content": state["original_input"]}]}
  )
  return {"final_answer": response["messages"][-1].content}