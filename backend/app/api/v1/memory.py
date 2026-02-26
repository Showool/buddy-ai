"""
记忆管理 API
"""

import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Query

from app.models.memory import Memory, MemoriesResponse, SaveMemoryRequest


router = APIRouter()

# 临时存储记忆（生产环境应使用数据库）
_memories: dict[str, Memory] = {}


@router.get("/memory", response_model=MemoriesResponse)
async def get_memories(
    user_id: str = Query(..., description="用户ID"),
    query: Optional[str] = Query(None, description="搜索查询")
):
    """获取用户的记忆列表"""
    memories = [
        m for m in _memories.values()
        if m.user_id == user_id
    ]

    # 如果有查询，过滤记忆
    if query:
        memories = [m for m in memories if query.lower() in m.content.lower()]

    # 按创建时间倒序
    memories.sort(key=lambda x: x.created_at, reverse=True)

    return MemoriesResponse(
        memories=memories,
        total=len(memories)
    )


@router.post("/memory")
async def save_memory(request: SaveMemoryRequest):
    """保存记忆"""
    memory_id = str(uuid.uuid4())
    now = datetime.utcnow()

    memory = Memory(
        id=memory_id,
        user_id=request.user_id,
        content=request.content,
        created_at=now
    )

    _memories[memory_id] = memory

    return {"status": "success", "memory_id": memory_id, "message": "记忆已保存"}


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: str):
    """删除记忆"""
    if memory_id not in _memories:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="记忆不存在"
        )

    del _memories[memory_id]
    return {"status": "success", "message": "记忆已删除"}