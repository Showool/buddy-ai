from .state import GradeDocuments, AgentState
from ..prompt.prompt import GRADE_PROMPT
from ..llm.llm_factory import get_llm

def grade_documents(state: AgentState) -> dict:
    """确定检索到的文件是否与问题相关，返回状态更新."""
    question = state["messages"][0].content
    context = state["messages"][-1].content

    loop_step = state.get("loop_step", 0)
    if loop_step >= 3:
        return {"routing_decision": "generate_response"}

    prompt = GRADE_PROMPT.format(question=question, context=context)
    response = (
        get_llm()
        .with_structured_output(GradeDocuments).invoke(
            [{"role": "user", "content": prompt}]
        )
    )
    score = response.binary_score
    if score == "yes":
        print(f"Documents are relevant, generating response")
        return {"routing_decision": "generate_response"}
    else:
        print(f"Rewriting question: {question}, times: {loop_step}")
        return {"routing_decision": "rewrite_question"}


def grade_routing_condition(state: AgentState) -> str:
    """基于 grade_documents 的路由决策来决定下一步."""
    return state.get("routing_decision", "generate_response")