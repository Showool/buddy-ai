
from apps.agent.llm.llm_factory import get_llm
from apps.agent.state import GraphState, RouteSchema


def router(state: GraphState) -> dict:
    """Route the agent to the appropriate node."""
    messages = state.get("messages", [])
    if not messages:
        return {"route_decision": "answer_directly", "original_input": ""}

    query = messages[-1].content
    llm_with_schema = get_llm().with_structured_output(RouteSchema, method="json_mode")
    ROUTER_PROMPT = f"""
        # 角色设定
        你是智能需求分类助手，核心职责是精准识别用户输入的需求类型，为后续服务路径匹配提供决策依据。

        # 用户输入
        <user_input>{query}</user_input>

        # 核心规则
        ## 必做事项
        1. 当用户输入包含明确知识获取诉求（如“什么是...”“如何理解...”“XX的定义是”）时，判定为knowledge_base_search。
        2. 当用户输入涉及多步骤操作、资源调度或复杂问题解决（如“帮我完成XX任务”“规划XX流程”“执行XX操作”）时，判定为plan_and_execute。
        3. 所有未触发上述条件的需求，默认归类为answer_directly。

        ## 约束条件
        1. 禁止主观扩展用户需求范围，严格依据输入文本判定。
        2. 若需求同时符合多个类别特征，优先匹配优先级更高的类别（plan_and_execute  knowledge_base_search  answer_directly）。
        3. 对于模糊需求（如仅包含关键词无明确意图），默认归类为answer_directly。

        # 输入处理
        读取用户输入，按以下优先级处理：
        1. 优先识别是否包含复杂任务执行关键词（如“帮我”“规划”“执行”“完成”）。
        2. 其次识别是否包含知识获取关键词（如“什么是”“如何”“定义”“解释”）。
        3. 若未识别到上述关键词，直接判定为默认类别。

        # 执行流程
        1. 需求解析：分析用户输入中的核心诉求，提取关键动作词与意图指向。
        2. 类别匹配：根据核心规则判断需求所属类别，记录匹配依据。
        3. 结果输出：生成包含类别标签与判定理由的结构化结果。

        # 输出规范
        1. 结构框架：采用JSON格式，包含“route_decision”（类别标签）和“route_reason”（判定理由）两个字段。
        2. 标签使用：类别标签严格限定为answer_directly、knowledge_base_search、plan_and_execute三者之一。
        3. 语言风格：判定理由需简洁明了，直接引用用户输入中的关键信息。
        4. 字数限制：整体输出不超过100字。

        示例输出：
        {{
            "route_decision": "knowledge_base_search",
            "route_reason": "用户询问'什么是人工智能'，属于知识获取需求"
        }}

        """
    route_result: RouteSchema = llm_with_schema.invoke(ROUTER_PROMPT)
    return {
        "route_decision": route_result.route_decision,
        "route_reason": route_result.route_reason,
        "original_input": query,
        "enhanced_input": None,
        "query_transform_type": None,
        "rag_docs": [],
        "plan": None,
        "reflection_count": 0,  # 初始化评估计数
        "reflection": None,  # 清除之前的评估状态
        "draft_answer": None,
        "final_answer": None,
    }
