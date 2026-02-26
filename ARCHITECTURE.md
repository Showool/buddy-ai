# Buddy-AI 前后端分离架构设计

## 项目结构

```
buddy-ai/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 应用入口
│   │   ├── config.py           # 配置管理
│   │   ├── dependencies.py     # 依赖注入
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chat.py     # 聊天 WebSocket API
│   │   │   │   ├── files.py    # 文件上传 API
│   │   │   │   ├── sessions.py # 会话管理 API
│   │   │   │   ├── memory.py   # 记忆管理 API
│   │   │   │   └── __init__.py
│   │   ├── agent/              # LangGraph Agent
│   │   │   ├── __init__.py
│   │   │   ├── graph.py
│   │   │   ├── node.py
│   │   │   └── state.py
│   │   ├── tools/              # 工具
│   │   │   ├── __init__.py
│   │   │   ├── system_tool.py
│   │   │   ├── user_tool.py
│   │   │   └── web_search_tool.py
│   │   ├── memory/             # 记忆
│   │   │   ├── __init__.py
│   │   │   └── memory_factory.py
│   │   ├── retriever/          # 检索
│   │   │   ├── __init__.py
│   │   │   ├── get_retriever.py
│   │   │   ├── get_db.py
│   │   │   ├── vector_store.py
│   │   │   ├── vectorize_files.py
│   │   │   └── embeddings_model.py
│   │   ├── llm/                # LLM
│   │   │   ├── __init__.py
│   │   │   └── llm_factory.py
│   │   ├── prompt/             # 提示词
│   │   │   ├── __init__.py
│   │   │   └── prompt.py
│   │   ├── models/             # Pydantic 模型
│   │   │   ├── __init__.py
│   │   │   ├── chat.py
│   │   │   ├── session.py
│   │   │   ├── memory.py
│   │   │   └── file.py
│   │   ├── schemas/            # 响应 Schema
│   │   │   ├── __init__.py
│   │   │   ├── chat.py
│   │   │   └── common.py
│   │   └── middleware/         # 中间件
│   │       ├── __init__.py
│   │       └── middleware.py
│   ├── requirements.txt
│   └── .env
├── frontend/                   # Vue3 前端
│   ├── src/
│   │   ├── main.ts             # 应用入口
│   │   ├── App.vue
│   │   ├── components/
│   │   │   ├── ChatMessage.vue         # 聊天消息组件
│   │   │   ├── ChatInput.vue           # 输入框组件
│   │   │   ├── FileUpload.vue          # 文件上传组件
│   │   │   ├── DebugPanel.vue          # 调试面板组件
│   │   │   ├── SessionList.vue         # 会话列表
│   │   │   ├── Sidebar.vue             # 侧边栏
│   │   │   └── LoadingSpinner.vue      # 加载动画
│   │   ├── views/
│   │   │   ├── ChatView.vue            # 聊天主视图
│   │   │   └── SettingsView.vue        # 设置视图
│   │   ├── api/
│   │   │   ├── chat.ts                 # WebSocket 客户端
│   │   │   ├── files.ts                # 文件 API
│   │   │   ├── sessions.ts             # 会话 API
│   │   │   └── memory.ts               # 记忆 API
│   │   ├── stores/
│   │   │   ├── chat.ts                 # 聊天状态 (Pinia)
│   │   │   ├── session.ts              # 会话状态 (Pinia)
│   │   │   ├── user.ts                 # 用户状态 (Pinia)
│   │   │   └── file.ts                 # 文件状态 (Pinia)
│   │   ├── types/
│   │   │   ├── chat.ts
│   │   │   ├── session.ts
│   │   │   └── index.ts
│   │   ├── router/
│   │   │   └── index.ts                # 路由配置
│   │   ├── composables/
│   │   │   ├── useWebSocket.ts         # WebSocket Hook
│   │   │   └── useChat.ts              # 聊天逻辑 Hook
│   │   ├── utils/
│   │   │   ├── markdown.ts             # Markdown 渲染
│   │   │   └── format.ts               # 格式化工具
│   │   └── assets/
│   │       └── styles/
│   │           └── main.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── .env.development
├── shared/                      # 共享类型定义
│   ├── types.ts
│   └── constants.ts
├── docker-compose.yml           # Docker 编排
└── README.md
```

## 后端 API 设计

### 1. WebSocket 聊天接口

**端点**: `ws://localhost:8000/ws/chat/{user_id}`

**消息格式**:

客户端 → 服务端:
```json
{
  "type": "user_message",
  "content": "用户的问题",
  "thread_id": "会话ID（可选，新会话则不传）"
}
```

服务端 → 客户端 (流式):
```json
{
  "type": "agent_step",
  "node": "generate_query_or_respond",
  "message_type": "AIMessage",
  "content": "中间过程消息",
  "tool_calls": [
    {
      "name": "retrieve_context",
      "args": {"query": "..."}
    }
  ]
}
```

最终回复:
```json
{
  "type": "agent_complete",
  "final_answer": "最终答案",
  "thread_id": "会话ID"
}
```

错误:
```json
{
  "type": "error",
  "message": "错误信息"
}
```

### 2. REST API 接口

#### 文件上传
```
POST /api/v1/files/upload
Content-Type: multipart/form-data

请求:
- file: 文件 (PDF/DOCX/TXT/MD/CSV, ≤5MB)

响应:
{
  "id": "file_id",
  "filename": "文件名",
  "size": 文件大小,
  "status": "uploaded",
  "vectorized": false
}
```

#### 向量化
```
POST /api/v1/files/{file_id}/vectorize

响应:
{
  "status": "success",
  "chunk_count": 10
}
```

#### 会话管理
```
GET /api/v1/sessions?user_id={user_id}

响应:
{
  "sessions": [
    {
      "thread_id": "uuid",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "title": "会话标题（首条消息）"
    }
  ]
}

DELETE /api/v1/sessions/{thread_id}

响应:
{
  "status": "success"
}
```

#### 记忆管理
```
GET /api/v1/memory?user_id={user_id}&query={query}

响应:
{
  "memories": [
    {
      "id": "memory_id",
      "content": "记忆内容",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}

POST /api/v1/memory

请求:
{
  "user_id": "user_id",
  "content": "记忆内容"
}
```

## Pydantic 模型定义

### Chat Models
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    USER_MESSAGE = "user_message"
    AGENT_STEP = "agent_step"
    AGENT_COMPLETE = "agent_complete"
    ERROR = "error"

class ToolCall(BaseModel):
    name: str
    args: dict

class AgentStepMessage(BaseModel):
    type: MessageType = MessageType.AGENT_STEP
    node: str
    message_type: str
    content: str
    tool_calls: Optional[List[ToolCall]] = None

class AgentCompleteMessage(BaseModel):
    type: MessageType = MessageType.AGENT_COMPLETE
    final_answer: str
    thread_id: str

class ErrorMessage(BaseModel):
    type: MessageType = MessageType.ERROR
    message: str
```

### File Models
```python
class FileUploadResponse(BaseModel):
    id: str
    filename: str
    size: int
    status: str
    vectorized: bool

class VectorizeResponse(BaseModel):
    status: str
    chunk_count: int
```

### Session Models
```python
class Session(BaseModel):
    thread_id: str
    created_at: datetime
    updated_at: datetime
    title: Optional[str] = None

class SessionsResponse(BaseModel):
    sessions: List[Session]
```

### Memory Models
```python
class Memory(BaseModel):
    id: str
    content: str
    created_at: datetime

class MemoriesResponse(BaseModel):
    memories: List[Memory]

class SaveMemoryRequest(BaseModel):
    user_id: str
    content: str
```

## 前端状态管理 (Pinia)

### Chat Store
```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const isStreaming = ref(false)
  const debugInfo = ref<DebugInfo[]>([])
  const currentThreadId = ref<string | null>(null)

  function addMessage(message: Message) {
    messages.value.push(message)
  }

  function updateLastMessage(content: string) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content = content
    }
  }

  function clearMessages() {
    messages.value = []
    debugInfo.value = []
  }

  function addDebugInfo(info: DebugInfo) {
    debugInfo.value.push(info)
  }

  return {
    messages,
    isStreaming,
    debugInfo,
    currentThreadId,
    addMessage,
    updateLastMessage,
    clearMessages,
    addDebugInfo
  }
})
```

### Session Store
```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Session[]>([])
  const currentSession = ref<Session | null>(null)
  const userId = ref<string>('1')

  async function fetchSessions() {
    // 调用 API 获取会话列表
  }

  function setCurrentSession(session: Session) {
    currentSession.value = session
  }

  function createNewThread() {
    const newSession = {
      thread_id: generateUUID(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      title: null
    }
    sessions.value.unshift(newSession)
    setCurrentSession(newSession)
    return newSession.thread_id
  }

  return {
    sessions,
    currentSession,
    userId,
    fetchSessions,
    setCurrentSession,
    createNewThread
  }
})
```

## WebSocket Client (Composable)

```typescript
import { ref, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'

export function useWebSocket(userId: string) {
  const chatStore = useChatStore()
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)

  function connect() {
    ws.value = new WebSocket(`ws://localhost:8000/ws/chat/${userId}`)

    ws.value.onopen = () => {
      isConnected.value = true
    }

    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'agent_step':
          chatStore.addDebugInfo(data)
          if (data.message_type === 'AIMessage' && !data.tool_calls) {
            // 更新流式响应
            chatStore.updateLastMessage(data.content)
          }
          break
        case 'agent_complete':
          chatStore.addMessage({
            role: 'assistant',
            content: data.final_answer
          })
          chatStore.currentThreadId = data.thread_id
          break
        case 'error':
          console.error(data.message)
          break
      }
    }

    ws.value.onclose = () => {
      isConnected.value = false
    }
  }

  function sendMessage(content: string, threadId?: string) {
    if (!ws.value) return

    ws.value.send(JSON.stringify({
      type: 'user_message',
      content,
      thread_id: threadId
    }))
  }

  function disconnect() {
    ws.value?.close()
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    connect,
    sendMessage,
    disconnect
  }
}
```

## 数据流设计

### 聊天流程

```
用户输入消息
    ↓
前端 WebSocket 发送
    ↓
后端接收消息
    ↓
调用 LangGraph Agent
    ↓
Agent 执行各节点
    ↓ (流式返回每个步骤)
前端实时显示调试信息
    ↓
Agent 完成
    ↓
返回最终答案
    ↓
前端显示最终答案
```

### 文件上传流程

```
用户选择文件
    ↓
前端发送 POST 请求
    ↓
后端保存文件
    ↓
前端显示向量化按钮
    ↓
用户点击向量化
    ↓
前端发送向量化请求
    ↓
后端处理文件 → 向量化 → 存入 Chroma
    ↓
返回成功响应
```

## 部署配置

### Docker Compose

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - POSTGRESQL_URL=postgresql://user:pass@postgres:5432/buddyai
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY}
    depends_on:
      - redis
      - postgres

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=buddyai
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 环境配置

### 后端 .env
```
DASHSCOPE_API_KEY=your_dashscope_key
TAVILY_API_KEY=your_tavily_key
REDIS_URL=redis://localhost:6379/0
POSTGRESQL_URL=postgresql://user:pass@localhost:5432/buddyai
CHROMA_PERSIST_DIR=./chroma_db
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=5242880
```

### 前端 .env.development
```
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## 迁移计划

1. **阶段一**: 创建新的项目结构，复制现有代码到对应模块
2. **阶段二**: 实现 FastAPI 基础框架和 WebSocket 聊天接口
3. **阶段三**: 实现 REST API（文件上传、会话管理、记忆管理）
4. **阶段四**: 开发 Vue3 前端基础框架和组件
5. **阶段五**: 集成前后端，联调 WebSocket
6. **阶段六**: 测试和优化