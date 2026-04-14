
from apps.agent.llm.llm_factory import get_llm
from apps.agent.state import GraphState, PlanSchema, PlanState, PlanStep


def plan_step(state: GraphState) -> dict:
    """根据用户输入生成计划步骤节点"""
    PLANNER_PROMPT = f"""
      ## 角色设定
      你是复杂问题规划专家，核心职责是基于用户输入和记忆信息生成精准、可落地的执行计划并拆分步骤。

      ## 用户输入
      <user_input>{state['original_input']}</user_input>

      ## 记忆信息
      <memory_context>{state['memory_context']}</memory_context>

      ## 行动准则
      - 必做：生成的计划需严格结合用户输入和记忆信息，每一步骤均需有明确依据（优先引用用户输入原文，次之用记忆信息）。
      - 禁止：严禁编造未提及的信息，禁止偏离用户核心需求设计步骤。

      ## 输入处理规则
      1. 优先级：先完整解析<user_input>中的核心问题（如需求目标、约束条件），再匹配<memory_context>中的关联信息（如历史任务要求、参考数据）。
      2. 缺失处理：若<memory_context>为“无”或无关联信息，直接基于<user_input>分析需求；若<user_input>核心信息缺失（如未明确任务目标），需在计划中加入“补充用户核心信息”的前置步骤。

      ## 执行流程（分阶段拆解）
      1. 需求锚定：提取<user_input>中的核心需求（如“制定项目推进计划”“解决数据异常问题”），明确任务边界（如时间范围、涉及对象）。
      2. 信息关联：匹配<memory_context>中的相关信息（如历史项目节点、异常数据记录），补充至需求分析中。
      3. 步骤生成：将任务拆解为线性可执行步骤，每一步需明确“动作+依据+目标”（如“依据用户输入的‘项目 deadline 为10月30日’，梳理现有任务节点”）。
      4. 校验调整：检查步骤是否覆盖核心需求、是否符合行动准则，确保无冗余或遗漏。

      ## 输出规范
      - 格式：严格采用JSON格式，无额外嵌套或注释。
      - 结构要求：
        1. 根节点含唯一数组“steps”。
        2. 数组元素为对象，必含字段：
          - "step_number"：从1开始的连续整数（如1、2、3...）。
          - "description"：步骤描述，需包含“动作+依据+目标”（依据需引用<user_input>或<memory_context>的关键信息，如“依据用户输入的‘需优化用户留存率’，分析近30日留存数据（来源：memory_context中的用户行为数据），定位流失高峰节点”）。
      - 语言：简洁精准，避免模糊表述（禁用“大概”“可能”等词）。
      - 字数：常规任务控制在200字以内，复杂任务（步骤≥5个）可扩展至300字以内。

      示例输出：
      {
        "steps": [
          {
            "step_number": 1,
            "description": "依据user_input中的‘需制定Q4产品推广计划’，梳理memory_context中的Q3推广数据，明确现有渠道ROI"
          },
          {
            "step_number": 2,
            "description": "结合user_input的‘目标用户为18-25岁学生’，筛选memory_context中的学生用户行为偏好，确定推广内容方向"
          }
        ]
      }

      """

    llm_with_schema = get_llm().with_structured_output(PlanSchema)
    result:PlanSchema = llm_with_schema.invoke(PLANNER_PROMPT)
    plan_step = PlanState(current_step_number=1)
    plan_step.steps = [PlanStep(step_number=step.step_number, description=step.description, status="pending", result="") for _, step in enumerate(result.steps)]
    return {"plan": plan_step}


def work_step(state: PlanStep) -> dict:
   """根据计划步骤生成结果"""
   description = state["description"]
   response = get_llm().invoke(description)
   return {"result": response.content}



def synthesis_step_results(state: GraphState) -> dict:
  """合并步骤结果"""
  steps = state["plan"]["steps"]
  return {
    "final_answer": "".join([step.result for step in steps])
  }