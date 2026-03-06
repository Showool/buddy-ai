from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from langchain_core.documents import Document
from langgraph.graph import MessagesState


class RetrievalMetadata(BaseModel):
    """检索元数据"""
    query: str
    rewritten_query: Optional[str] = None
    vector_count: int = 0
    fulltext_count: int = 0
    reranked_count: int = 0
    retrieval_time_ms: float = 0
    sources: List[str] = Field(default_factory=list)


class AgentState(MessagesState):
    """增强的 Agent 状态"""
    loop_step: int = 0
    query_history: List[str] = Field(default_factory=list)
    retrieved_documents: List[Document] = Field(default_factory=list)
    retrieval_metadata: Optional[RetrievalMetadata] = None
    should_retrieve: bool = False
    user_memories: List[Dict] = Field(default_factory=list)
    retrieval_needed: Dict[str, bool] = Field(default_factory=dict)
    routing_decision: Optional[str] = None
    question: str = Field(description="当前问题")


class GradeDocuments(BaseModel):
    """文档相关性评分"""
    binary_score: str = Field(
        description="相关性评分：'yes' 表示相关，'no' 表示无关"
    )