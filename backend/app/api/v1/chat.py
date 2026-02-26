"""
WebSocket 聊天 API - 优化版
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Query
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.config import settings
from app.models.chat import (
    UserMessageRequest,
    AgentStepMessage,
    AgentCompleteMessage,
    ErrorMessage,
    MessageType,
    ToolCall,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.graphs: dict[str, any] = {}  # 缓存每个用户的graph实例
        self.connection_count = 0

    async def connect(self, user_id: str, websocket: WebSocket) -> bool:
        """接受连接"""
        if self.connection_count >= settings.WS_MAX_CONNECTIONS:
            logger.warning(f"连接数已达上限，拒绝用户 {user_id} 的连接")
            return False

        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.connection_count += 1
        logger.info(f"✅ 用户 {user_id} 已连接 (当前连接数: {self.connection_count})")
        return True

    def disconnect(self, user_id: str):
        """断开连接"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            self.connection_count -= 1

            # 清理缓存
            if user_id in self.graphs:
                del self.graphs[user_id]

            logger.info(f"❌ 用户 {user_id} 已断开 (当前连接数: {self.connection_count})")

    async def send_message(self, user_id: str, message: dict):
        """发送消息到指定用户"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"发送消息到用户 {user_id} 失败: {e}")
                self.disconnect(user_id)
        else:
            logger.warning(f"用户 {user_id} 未连接，无法发送消息")

    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        disconnected = []
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"广播消息到用户 {user_id} 失败: {e}")
                disconnected.append(user_id)

        # 清理断开的连接
        for user_id in disconnected:
            self.disconnect(user_id)

    def get_or_create_graph(self, user_id: str):
        """获取或创建用户的graph实例"""
        if user_id not in self.graphs:
            try:
                from app.agent.graph import get_graph
                self.graphs[user_id] = get_graph()
                logger.info(f"为用户 {user_id} 创建了新的 graph 实例")
            except Exception as e:
                logger.error(f"创建 graph 实例失败: {e}", exc_info=True)
                raise
        return self.graphs[user_id]

    def get_stats(self) -> dict:
        """获取连接统计信息"""
        return {
            "active_connections": self.connection_count,
            "max_connections": settings.WS_MAX_CONNECTIONS,
            "connected_users": list(self.active_connections.keys()),
        }


manager = ConnectionManager()


def get_message_type(message) -> str:
    """获取 LangChain 消息类型名称"""
    msg_type = getattr(message, 'type', None)
    if msg_type:
        type_map = {
            'human': 'HumanMessage',
            'ai': 'AIMessage',
            'tool': 'ToolMessage'
        }
        return type_map.get(msg_type, f'{msg_type.capitalize()}Message')

    role = getattr(message, 'role', None)
    if role:
        role_map = {
            'user': 'HumanMessage',
            'assistant': 'AIMessage',
            'tool': 'ToolMessage'
        }
        return role_map.get(role, f'{role.capitalize()}Message')

    return 'UnknownMessage'


def convert_tool_calls(tool_calls) -> list:
    """转换工具调用格式"""
    if not tool_calls:
        return None

    result = []
    for call in tool_calls:
        result.append(ToolCall(
            name=call.get("name", "unknown"),
            args=call.get("args", {})
        ))
    return result


@router.websocket("/ws/chat/{user_id}")
async def chat_websocket(
    websocket: WebSocket,
    user_id: str,
    thread_id: Optional[str] = Query(None, description="可选的会话ID")
):
    """WebSocket 聊天接口"""
    # 尝试连接
    if not await manager.connect(user_id, websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 发送连接成功消息
    await websocket.send_json({
        "type": "connected",
        "user_id": user_id,
        "message": "WebSocket 连接成功"
    })

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            message_type = data.get("type")
            content = data.get("content", "")

            # 如果提供了 thread_id 则使用，否则生成新的
            current_thread_id = thread_id or data.get("thread_id") or str(uuid.uuid4())

            if message_type == "user_message":
                logger.info(f"用户 {user_id} 发送消息: {content[:50]}...")
                # 处理用户消息
                await handle_user_message(user_id, content, current_thread_id, websocket)
            elif message_type == "ping":
                # 心跳响应
                await websocket.send_json({"type": "pong"})
            else:
                # 发送错误
                error_msg = ErrorMessage(
                    type=MessageType.ERROR,
                    message=f"未知的消息类型: {message_type}"
                )
                await websocket.send_json(error_msg.model_dump())
                logger.warning(f"未知的消息类型: {message_type}")

    except WebSocketDisconnect as e:
        logger.info(f"用户 {user_id} WebSocket 断开连接: {e.code}")
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"用户 {user_id} WebSocket 错误: {e}", exc_info=True)
        try:
            error_msg = ErrorMessage(
                type=MessageType.ERROR,
                message=str(e) if settings.DEBUG else "服务错误"
            )
            await websocket.send_json(error_msg.model_dump())
        except Exception:
            pass
        manager.disconnect(user_id)


async def handle_user_message(
    user_id: str,
    content: str,
    thread_id: str,
    websocket: WebSocket
):
    """处理用户消息 - 使用 LangGraph Agent"""
    try:
        # 获取或创建graph
        graph = manager.get_or_create_graph(user_id)

        # 配置
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id
            }
        }

        # 使用 graph.stream() 获取执行流
        assistant_messages = []

        for chunk in graph.stream(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": content,
                    }
                ]
            },
            config,
            stream_mode="values",
        ):
            if "messages" in chunk:
                last_message = chunk["messages"][-1]
                message_type = get_message_type(last_message)

                # 收集所有的assistant消息
                if message_type == "AIMessage":
                    tool_calls = convert_tool_calls(
                        getattr(last_message, 'tool_calls', None)
                    )
                    assistant_messages.append({
                        "content": last_message.content,
                        "tool_calls": tool_calls
                    })

                # 发送步骤消息
                step_msg = AgentStepMessage(
                    type=MessageType.AGENT_STEP,
                    node="agent_step",
                    message_type=message_type,
                    content=str(last_message),
                    tool_calls=convert_tool_calls(getattr(last_message, 'tool_calls', None))
                )
                await websocket.send_json(step_msg.model_dump())

        # 使用最后一条没有 tool_calls 的 AI 消息作为最终回答
        final_answer = ""
        for msg in reversed(assistant_messages):
            if not msg.get('tool_calls'):
                if msg.get('content') and msg['content'].strip():
                    final_answer = msg['content']
                    break

        # 发送完成消息
        complete_msg = AgentCompleteMessage(
            type=MessageType.AGENT_COMPLETE,
            final_answer=final_answer or "抱歉，我没有找到合适的答案。",
            thread_id=thread_id
        )
        await websocket.send_json(complete_msg.model_dump())

        logger.info(f"用户 {user_id} 消息处理完成")

    except Exception as e:
        logger.error(f"处理用户 {user_id} 消息失败: {e}", exc_info=True)
        error_msg = ErrorMessage(
            type=MessageType.ERROR,
            message=str(e) if settings.DEBUG else "处理消息时发生错误"
        )
        await websocket.send_json(error_msg.model_dump())


@router.get("/ws/stats")
async def websocket_stats():
    """获取 WebSocket 连接统计"""
    return manager.get_stats()