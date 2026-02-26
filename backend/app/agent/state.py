from pydantic import BaseModel, Field
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    loop_step: int


class GradeDocuments(BaseModel):
    """使用二元评分来检查相关性文件."""

    binary_score: str = Field(
        description="相关性评分：如果相关，则为 'yes'，如果无关，则为 'no'"
    )