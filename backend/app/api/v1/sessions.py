"""
会话管理 API
"""

import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Query

from app.models.session import Session, SessionsResponse, CreateSessionResponse


router = APIRouter()

# 临时存储会话（生产环境应使用数据库）
_sessions: dict[str, Session] = {}


@router.get("/sessions", response_model=SessionsResponse)
async def get_sessions(user_id: str = Query(..., description="用户ID")):
    """获取用户的会话列表"""
    sessions = [
        s for s in _sessions.values()
        if s.user_id == user_id
    ]

    # 按更新时间倒序
    sessions.sort(key=lambda x: x.updated_at, reverse=True)

    return SessionsResponse(
        sessions=sessions,
        total=len(sessions)
    )


@router.get("/sessions/{thread_id}", response_model=Session)
async def get_session(thread_id: str):
    """获取指定会话"""
    if thread_id not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    return _sessions[thread_id]


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(user_id: str = Query(..., description="用户ID")):
    """创建新会话"""
    thread_id = str(uuid.uuid4())
    now = datetime.utcnow()

    session = Session(
        thread_id=thread_id,
        user_id=user_id,
        title=None,
        created_at=now,
        updated_at=now,
        message_count=0
    )

    _sessions[thread_id] = session

    return CreateSessionResponse(session=session)


@router.delete("/sessions/{thread_id}")
async def delete_session(thread_id: str):
    """删除会话"""
    if thread_id not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    del _sessions[thread_id]
    return {"status": "success", "message": "会话已删除"}


@router.patch("/sessions/{thread_id}/title")
async def update_session_title(thread_id: str, title: str = Query(..., description="会话标题")):
    """更新会话标题"""
    if thread_id not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    _sessions[thread_id].title = title
    _sessions[thread_id].updated_at = datetime.utcnow()

    return {"status": "success", "message": "标题已更新"}