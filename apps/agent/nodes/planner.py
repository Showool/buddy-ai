
from apps.agent.llm.llm_factory import get_llm
from apps.agent.state import GraphState, PlanSchema, PlanStepSchema


def plan_step(state: GraphState) -> dict:
    """根据用户输入生成计划步骤节点"""
    memory = state.get('memory_context') or '无'

    PLANNER_PROMPT = f"""
      ## 角色
      你是子任务拆分专家。根据用户问题和记忆上下文，将复杂问题拆解为多个可独立执行的子任务。

      ## 输入
      <user_input>{state['original_input']}</user_input>
      <memory_context>{memory}</memory_context>

      ## 拆分规则
      1. 问题分析：识别用户输入中包含的所有子问题、子目标，结合记忆上下文补充背景信息。
      2. 子任务划分：每个子任务对应一个独立可执行的工作单元，子任务之间保持逻辑递进或并列关系。
      3. description 字段要求——每个子任务的 description 必须包含以下三部分：
        - 【执行目标】：该子任务要达成的具体结果（如"输出XX分析报告""生成XX方案"）。
        - 【执行流程】：完成该目标的具体操作步骤，用"→"连接（如"收集XX数据 → 分析XX指标 → 得出XX结论"）。
        - 【信息来源】：直接引用<user_input>和<memory_context>标签内的原始文本内容，禁止出现"user_input""memory_context"等标签名称本身。
      4. 若记忆上下文为"无"，仅基于用户输入拆分；若用户输入信息不足以明确目标，首个子任务设为"澄清并补全用户核心需求"。
      5. 子任务数量：2-5个，禁止冗余拆分，每个子任务必须对最终结果有实质贡献。

      ## 严格禁止
      - description 中禁止出现"user_input""memory_context"等标签名或变量名，必须直接使用标签内的实际内容。

      ## 输出格式
      严格输出 JSON，不附加任何解释文字。

      {{
        "steps": [
          {{
            "step_number": 1,
            "description": "【执行目标】明确Q4推广的核心KPI和预算约束。【执行流程】提取'制定Q4推广计划，预算50万'中的推广目标 → 匹配'Q3各渠道ROI：信息流1.8、KOL2.3'数据 → 确定可量化的KPI指标。【信息来源】'制定Q4推广计划，预算50万'；'Q3各渠道ROI：信息流1.8、KOL2.3'。"
          }},
          {{
            "step_number": 2,
            "description": "【执行目标】输出分渠道的推广资源分配方案。【执行流程】按Q3 ROI排序各渠道 → 结合'目标用户为18-25岁学生'筛选高匹配渠道 → 按预算比例分配资源。【信息来源】'目标用户为18-25岁学生'；'学生群体在短视频渠道转化率最高'。"
          }}
        ]
      }}
      """

    llm_with_schema = get_llm().with_structured_output(PlanSchema)
    result: PlanSchema = llm_with_schema.invoke(PLANNER_PROMPT)
    return {"plan": result}


def work_step(state: PlanStepSchema) -> dict:
   """根据计划步骤生成结果"""
   description = state.description
   response = get_llm().invoke(description)
   return {"step_results": [response.content]}



def synthesis_step_results(state: GraphState) -> dict:
  """合并步骤结果"""
  return {
    "final_answer": "".join(state.get("step_results", []))
  }
