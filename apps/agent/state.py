from typing import Annotated, Literal, NotRequired, TypedDict
import operator
from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

"""" Route Schema """
class RouteSchema(BaseModel):
    route_decision: Literal['answer_directly', 'knowledge_base_search', 'plan_and_execute'] = Field(..., description="Classification of user input information")
    route_reason: str = Field(..., description="Reason for classification")

""" Query transform Schema """
class QueryTransformSchema(BaseModel):
    transform_flag: bool = Field(..., description="Transform flag")
    result: str = Field(..., description="Transform result")

""" Plan Schema """
class PlanStepSchema(BaseModel):
    step_number: int = Field(..., description="Step number")
    description: str = Field(..., description="Step description")

class PlanSchema(BaseModel):
    steps: list[PlanStepSchema] = Field(..., description="Plan steps")


""" Reflection Agent State """
class ReflectionState(BaseModel):
    passed: bool = Field(..., description="If the evaluation is passed, the value is True; otherwise, it is False.")
    feedback: str = Field(description="Feedback on the results")
    

""" 合并检索到的文档 """
def merge_rag_docs(existing: list[dict] | None, new: list[dict] | None) -> list[dict]:
    if existing is None: return new or []
    if new is None: return existing
    seen = {d.get("id") for d in existing}
    return existing + [d for d in (new or []) if d.get("id") not in seen]


""" GraphState """
class GraphState(MessagesState):
    memory_context: NotRequired[str | None]
    route_decision: Literal["answer_directly", "knowledge_base_search", "plan_and_execute"]
    route_reason: NotRequired[str | None]
    """ 用户原始输入 """
    original_input: Annotated[str, "Original input"]
    """ 增强后的输入(Query Transform) """
    enhanced_input: NotRequired[str | None]
    rag_docs: Annotated[list[dict], merge_rag_docs]
    plan: NotRequired[PlanSchema | None]
    step_results: Annotated[list[str] | None, operator.add]
    reflection_count: Annotated[int, "Number of reflections"] = 0
    reflection: NotRequired[ReflectionState | None]
    draft_answer: NotRequired[str | None]
    final_answer: NotRequired[str | None]