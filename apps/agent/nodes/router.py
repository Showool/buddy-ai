from typing import Any

from apps.agent.llm.llm_factory import get_llm
from apps.agent.state import GraphState, RouteSchema


def router(state: GraphState) -> dict[str, Any]:
    """Route the agent to the appropriate node."""
    messages = state.get("messages", [])
    if not messages:
        return {"route_decision": "answer_directly", "original_input": ""}

    query = messages[-1].content
    llm_with_schema = get_llm().with_structured_output(RouteSchema, method="json_mode")
    router_prompt = f"""你是意图分类器。判断用户输入属于以下哪个类别，输出 JSON。

    <user_input>{query}</user_input>

    ## 类别定义（按意图本质判断，不要仅依赖表面关键词）

    plan_and_execute：用户的真实意图需要拆解为多个有依赖关系的子步骤才能完成。
    特征：任务涉及规划、流程编排、多阶段执行、资源协调。
    典型场景：制定方案、项目规划、多步骤任务执行、流程设计。
    注意："帮我解释XX"虽含"帮我"，但本质是知识查询，不属于此类。

    knowledge_base_search：用户想获取特定领域的知识、概念、原理或事实信息。
    特征：问题有明确的知识性答案，需要检索专业资料才能准确回答。
    典型场景：概念解释、原理阐述、技术细节查询、专业知识问答。

    answer_directly：简单对话、闲聊、打招呼、观点讨论、或基于常识即可回答的问题。
    特征：无需检索知识库，也无需多步骤规划。
    典型场景：日常问候、简单计算、常识问答、情感表达、意图模糊的输入。

    ## 判断流程
    1. 提取用户的核心意图——他想"知道什么"还是"完成什么"还是"聊什么"。
    2. 若意图是"完成一个需要多步骤协作的任务" → plan_and_execute。
    3. 若意图是"获取特定知识或专业信息" → knowledge_base_search。
    4. 其余情况 → answer_directly。

    ## 边界case处理
    - 意图模糊或仅含孤立关键词 → answer_directly。
    - 同时含知识查询和任务执行特征 → 以核心意图为准：若最终目的是获取知识则 knowledge_base_search，若最终目的是完成任务则 plan_and_execute。

    ## 输出格式
    严格输出 JSON，不附加任何额外文字。route_reason 需简洁引用用户输入中的关键信息说明判断依据，不超过50字。

    {{
    "route_decision": "类别标签",
    "route_reason": "判定理由"
    }}
    """
    route_result: RouteSchema = llm_with_schema.invoke(router_prompt)
    return {
        "route_decision": route_result.route_decision,
        "route_reason": route_result.route_reason,
        "original_input": query,
        "enhanced_input": None,
        "rag_docs": [],
        "plan": None,
        "reflection_count": 0,
        "reflection": None,
        "draft_answer": None,
        "final_answer": None,
    }
