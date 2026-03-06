"""Memory schema for PostgresStore"""
from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class MemoryCategory(str, Enum):
    """Memory classification categories"""
    PROFILE = "profile"           # Personal info (name, age, occupation)
    PREFERENCE = "preference"     # Preferences, likes, dislikes, habits
    SCHEDULE = "schedule"         # Appointments, plans, commitments
    FACT = "fact"                 # Factual records, events, completed items
    RELATIONSHIP = "relationship" # Family, friends, colleagues
    OTHER = "other"               # Other


class MemoryData(BaseModel):
    """Memory data structure stored in PostgresStore"""
    data: str = Field(description="Memory content summary (no original question)")
    category: MemoryCategory = Field(description="Memory category")
    tags: List[str] = Field(default_factory=list, description="Free-form tags")
    timestamp: str = Field(description="Creation timestamp in ISO format")


class ConversationAnalysis(BaseModel):
    """LLM analysis result for conversation memory"""
    category: MemoryCategory
    tags: List[str]
    summary: str
    should_save: bool


class RetrievalDecision(BaseModel):
    """检索决策模型"""
    need_memory: bool = Field(description="是否需要检索记忆")
    need_rag: bool = Field(description="是否需要检索知识库（RAG）")
    reason: str = Field(description="决策原因")