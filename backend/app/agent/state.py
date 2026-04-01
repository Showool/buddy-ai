import operator
from typing import List, Dict, Optional, Annotated

from pydantic import BaseModel, Field
from langgraph.graph import MessagesState


class GradeDocuments(BaseModel):
    """文档相关性评分"""

    binary_score: str = Field(description="相关性评分：'yes' 表示相关，'no' 表示无关")


class AgentState(MessagesState):
    """简化的 Agent 状态"""

    # 并行检索结果（使用 operator.add 自动合并）
    parallel_results: Annotated[List[Dict], operator.add] = Field(default_factory=list)

    # 循环控制（用于重写逻辑）
    loop_step: int = 0
    routing_decision: Optional[str] = None

    # 分类结果（用于并行路由）
    classifications: List[Dict] = Field(default_factory=list)

    # 当前问题
    question: str = Field(description="当前问题", default="")
