
from apps.agent.llm.llm_factory import get_llm
from apps.agent.state import GraphState, ReflectionState


def evaluate_node(state: GraphState) -> dict:
  reflection_count = state["reflection_count"]
  retrieval_data = "/n".join([d["document_text"] for d in state["rag_docs"]])
  EVALUATE_PROMPT = f"""
    ## 角色设定
    你是知识问答评估专家，核心职责是基于用户输入，记忆信息和检索信息，评估回答内容是否合格。

    ## 用户输入
    <user_input>{state['original_input']}</user_input>

    ## 记忆信息
    <memory_context>{state['memory_context']}</memory_context>

    ## 检索信息
    <retrieval_data>{retrieval_data}<retrieval_data/>

    ## 回答内容
    <answer_context>{state['draft_answer']}</answer_context>

    ## 行动准则
    - 必做：综合分析用户输入，记忆信息和检索信息，评估回答内容的准确性。
    - 约束：禁止编造信息，所有回答需有明确依据。

    ## 输入处理
    优先读取用户输入明确核心问题，再结合记忆信息和检索信息；若变量缺失（如无记忆信息），直接基于用户输入分析需求。

    ## 执行流程
    1. 分析问题：综合分析用户输入，记忆信息和检索信息。
    2. 评估回答：评估回答内容的准确性。
    3. 生成评估结果和反馈：整合所有有效信息，生成评估结果和反馈。

    ## 输出规范
    - 结构：采用JSON格式。
    - 约束: passed是bool，合格是True，不合格是False，若不合格则填充feedback字段值，值是反馈内容和改进点。
    - 语言风格：反馈内容和改进点需简洁明了，直接引用用户输入中的关键信息。
    - 字数：控制在200字以内，复杂问题可适当扩展至300字。

    示例输出：
    {{
      "passed": False,
      "feedback": "回答内容不专业，需使用专业术语"
    }}
    """
  llm_with_schema = get_llm().with_structured_output(ReflectionState, method="json_mode")
  response = llm_with_schema.invoke(EVALUATE_PROMPT)
  return {
    "reflection": response,
    "reflection_count": reflection_count + 1
  }