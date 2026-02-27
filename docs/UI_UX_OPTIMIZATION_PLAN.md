# Buddy-AI UI/UX 优化技术方案

## 一、项目架构分析

### 1.1 现有架构概述

**后端架构 (FastAPI + LangGraph)**
- WebSocket 聊天接口 (`/api/v1/ws/chat/{user_id}`)
- REST API: 文件上传 (`/files`)、会话管理 (`/sessions`)、记忆管理 (`/memory`)
- LangGraph Agent 流程: `generate_query_or_respond` -> `tool_node` -> `grade_documents` -> `rewrite_question`/`generate_answer`

**前端架构 (Vue3 + TypeScript + Pinia)**
- 状态管理: `chat.ts`, `session.ts`, `user.ts`
- 组件: `ChatMessage`, `ChatInput`, `Sidebar`, `DebugPanel`, `FileUpload`
- Composables: `useWebSocket`
- 路由: 单页面应用，只有 `ChatView`

### 1.2 当前问题识别

**UI/UX 问题:**
1. 消息气泡样式单一，缺乏视觉层次
2. 对话框未居中，消息对齐方式不符合主流聊天应用习惯
3. 侧边栏固定宽度，无法收缩，占用屏幕空间
4. 输入框发送按钮显示文字而非图标
5. 文件上传功能独立于聊天输入框

**状态管理问题:**
1. `chatStore` 缺少 `debugPanelVisible` 属性引用
2. 会话历史消息未从后端加载
3. WebSocket 连接状态未持久化

**API 问题:**
1. 缺少文件列表获取接口 (`/api/v1/files`)
2. 缺少会话历史消息获取接口
3. 缺少消息重新生成接口

---

## 二、组件结构优化方案

### 2.1 新组件架构图

```
frontend/src/
├── components/
│   ├── chat/                      # 聊天相关组件
│   │   ├── ChatContainer.vue      # 聊天容器（布局）
│   │   ├── MessageList.vue        # 消息列表
│   │   ├── MessageBubble.vue      # 消息气泡（优化后）
│   │   ├── MessageAvatar.vue      # 消息头像
│   │   ├── MessageContent.vue     # 消息内容（Markdown渲染）
│   │   ├── MessageActions.vue     # 消息操作（复制、重新生成）
│   │   └── TypingIndicator.vue    # 输入指示器
│   ├── input/                     # 输入相关组件
│   │   ├── ChatInputContainer.vue # 输入容器
│   │   ├── MessageTextarea.vue    # 消息输入框
│   │   ├── AttachmentButton.vue   # 附件按钮
│   │   ├── SendButton.vue         # 发送按钮（图标化）
│   │   ├── AttachmentPreview.vue  # 附件预览
│   │   └── QuickActions.vue       # 快捷操作栏
│   ├── layout/                    # 布局组件
│   │   ├── Sidebar.vue            # 侧边栏（可收缩）
│   │   ├── SidebarHeader.vue      # 侧边栏头部
│   │   ├── SessionList.vue        # 会话列表
│   │   ├── SessionItem.vue        # 会话项
│   │   ├── ToggleButton.vue       # 侧边栏切换按钮
│   │   ├── HeaderBar.vue          # 顶部栏
│   │   └── MainArea.vue           # 主内容区
│   ├── panels/                    # 面板组件
│   │   ├── DebugPanel.vue         # 调试面板
│   │   ├── FileUploadPanel.vue    # 文件上传面板
│   │   ├── KnowledgeBasePanel.vue # 知识库管理面板
│   │   └── SettingsPanel.vue      # 设置面板
│   ├── ui/                        # 通用UI组件
│   │   ├── Button.vue             # 按钮组件
│   │   ├── Icon.vue               # 图标组件
│   │   ├── Modal.vue              # 模态框
│   │   ├── Dropdown.vue           # 下拉菜单
│   │   ├── Tooltip.vue            # 提示框
│   │   └── Loading.vue            # 加载状态
│   └── common/                    # 通用组件
│       └── EmptyState.vue         # 空状态
```

### 2.2 组件职责划分

**ChatContainer.vue**
- 整体聊天区域布局
- 消息滚动区域
- 输入区域定位
- 连接状态显示

**MessageBubble.vue**
- 消息气泡样式（用户/AI不同样式）
- 左右对齐
- 背景色差异化
- 圆角方向处理

**Sidebar.vue**
- 侧边栏收缩/展开动画
- 响应式宽度（260px / 60px）
- 过渡效果

**ChatInputContainer.vue**
- 集成输入框和附件按钮
- 统一样式管理
- 快捷操作栏

---

## 三、前端组件详细设计

### 3.1 MessageBubble.vue 优化

```vue
<template>
  <div
    class="message-bubble"
    :class="[
      `message-${message.role}`,
      { 'message-typing': isTyping }
    ]"
  >
    <div class="bubble-content">
      <MessageAvatar v-if="message.role === 'assistant'" :role="message.role" />

      <div class="bubble-wrapper">
        <div class="bubble-sender" v-if="showSender">
          {{ message.role === 'user' ? userName : assistantName }}
        </div>

        <div class="bubble-inner">
          <MessageContent :content="message.content" :isTyping="isTyping" />

          <MessageActions
            v-if="message.role === 'assistant' && !isTyping"
            :message="message"
            @copy="handleCopy"
            @regenerate="handleRegenerate"
          />
        </div>

        <div class="bubble-time">{{ formatTime(message.timestamp) }}</div>
      </div>

      <MessageAvatar v-if="message.role === 'user'" :role="message.role" />
    </div>
  </div>
</template>

<style scoped>
.message-bubble {
  width: 100%;
  margin: 8px 0;
}

.bubble-content {
  display: flex;
  gap: 12px;
  max-width: 85%;
  margin: 0 auto;
}

.message-user .bubble-content {
  flex-direction: row-reverse;
  margin-left: auto;
  margin-right: 0;
}

.message-assistant .bubble-content {
  margin-left: 0;
  margin-right: auto;
}

.bubble-wrapper {
  flex: 1;
  min-width: 0;
}

.bubble-inner {
  position: relative;
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.message-user .bubble-inner {
  background: #1890ff;
  color: #fff;
  border-radius: 12px 12px 0 12px;
}

.message-assistant .bubble-inner {
  background: #f5f5f5;
  color: #1a1a1a;
  border-radius: 12px 12px 12px 0;
}

/* 侧边栏收缩时的样式调整 */
.sidebar-collapsed .message-user .bubble-content,
.sidebar-collapsed .message-assistant .bubble-content {
  max-width: 90%;
}
</style>
```

### 3.2 Sidebar.vue 可收缩设计

```vue
<template>
  <div
    class="sidebar"
    :class="{ 'is-collapsed': isCollapsed }"
    :style="{ width: isCollapsed ? '64px' : '280px' }"
  >
    <SidebarHeader :collapsed="isCollapsed" />

    <div class="sidebar-content">
      <SessionList
        :sessions="sessions"
        :collapsed="isCollapsed"
        @select="handleSelectSession"
        @delete="handleDeleteSession"
      />

      <div class="sidebar-actions" v-if="!isCollapsed">
        <button @click="showKnowledgePanel = true" class="action-btn">
          <Icon name="folder" />
          <span>知识库</span>
        </button>
        <button @click="showSettingsPanel = true" class="action-btn">
          <Icon name="settings" />
          <span>设置</span>
        </button>
      </div>
    </div>

    <button
      class="toggle-btn"
      @click="toggleCollapse"
      :title="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
    >
      <Icon :name="isCollapsed ? 'chevron-right' : 'chevron-left'" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useLocalStorage } from '@/composables/useLocalStorage'

const isCollapsed = useLocalStorage('sidebar-collapsed', false)

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fafafa;
  border-right: 1px solid #e5e5e5;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  flex-shrink: 0;
}

.toggle-btn {
  position: absolute;
  right: -12px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.sidebar.is-collapsed .toggle-btn {
  right: -12px;
}
</style>
```

### 3.3 SendButton.vue 图标化

```vue
<template>
  <button
    class="send-button"
    :class="[
      { 'is-disabled': disabled || isStreaming },
      { 'is-loading': isStreaming }
    ]"
    :disabled="disabled || isStreaming"
    @click="$emit('click')"
  >
    <Icon v-if="!isStreaming" name="send" />
    <Icon v-else name="spinner" class="is-spinning" />
  </button>
</template>

<style scoped>
.send-button {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
  background: #1890ff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.send-button:hover:not(.is-disabled) {
  background: #40a9ff;
  transform: scale(1.05);
}

.send-button:active:not(.is-disabled) {
  transform: scale(0.95);
}

.send-button.is-disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

.send-button.is-spinning :deep(.icon) {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
```

---

## 四、状态管理优化

### 4.1 更新 Chat Store

```typescript
// stores/chat.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Message, DebugInfo } from '@/types'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const messages = ref<Message[]>([])
  const isStreaming = ref(false)
  const debugInfo = ref<DebugInfo[]>([])
  const currentThreadId = ref<string | null>(null)
  const wsConnectionStatus = ref<'disconnected' | 'connecting' | 'connected'>('disconnected')
  const debugPanelVisible = ref(false)
  const selectedMessageId = ref<string | null>(null)

  // 计算属性
  const lastMessage = computed(() => messages.value[messages.value.length - 1])
  const userMessages = computed(() => messages.value.filter(m => m.role === 'user'))
  const assistantMessages = computed(() => messages.value.filter(m => m.role === 'assistant'))

  // 操作
  function addMessage(message: Message) {
    messages.value.push(message)
  }

  function updateLastMessage(partialMessage: Partial<Message>) {
    if (lastMessage.value) {
      Object.assign(lastMessage.value, partialMessage)
    }
  }

  function updateMessageById(id: string, partialMessage: Partial<Message>) {
    const message = messages.value.find(m => m.id === id)
    if (message) {
      Object.assign(message, partialMessage)
    }
  }

  function removeMessage(id: string) {
    const index = messages.value.findIndex(m => m.id === id)
    if (index !== -1) {
      messages.value.splice(index, 1)
    }
  }

  function clearMessages() {
    messages.value = []
    debugInfo.value = []
    selectedMessageId.value = null
  }

  function addDebugInfo(info: DebugInfo) {
    debugInfo.value.push(info)
  }

  function toggleDebugPanel() {
    debugPanelVisible.value = !debugPanelVisible.value
  }

  function handleWSMessage(data: WSMessage) {
    switch (data.type) {
      case MessageType.AGENT_STEP:
        debugInfo.value.push({
          type: 'agent_step',
          message_type: data.message_type,
          role: getMessageRole(data.message_type),
          content: data.content,
          tool_calls: data.tool_calls,
          node: data.node,
        })
        break
      case MessageType.AGENT_COMPLETE:
        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.final_answer,
          timestamp: new Date().toISOString(),
        })
        currentThreadId.value = data.thread_id
        isStreaming.value = false
        break
      case MessageType.ERROR:
        console.error(data.message)
        isStreaming.value = false
        break
    }
  }

  function getMessageRole(messageType: string): string {
    const roleMap: Record<string, string> = {
      'HumanMessage': 'user',
      'AIMessage': 'assistant',
      'ToolMessage': 'tool',
    }
    return roleMap[messageType] || 'unknown'
  }

  return {
    // 状态
    messages,
    isStreaming,
    debugInfo,
    currentThreadId,
    wsConnectionStatus,
    debugPanelVisible,
    selectedMessageId,

    // 计算属性
    lastMessage,
    userMessages,
    assistantMessages,

    // 操作
    addMessage,
    updateLastMessage,
    updateMessageById,
    removeMessage,
    clearMessages,
    addDebugInfo,
    toggleDebugPanel,
    handleWSMessage,
  }
})
```

### 4.2 更新 Session Store

```typescript
// stores/session.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Session } from '@/types'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Session[]>([])
  const currentSession = ref<Session | null>(null)
  const userId = ref<string>('1')
  const isLoading = ref(false)

  function setUserId(id: string) {
    userId.value = id
  }

  function setCurrentSession(session: Session) {
    currentSession.value = session
  }

  function createNewThread(): string {
    const threadId = crypto.randomUUID()
    const now = new Date().toISOString()

    const newSession: Session = {
      thread_id: threadId,
      user_id: userId.value,
      title: null,
      created_at: now,
      updated_at: now,
      message_count: 0,
    }

    sessions.value.unshift(newSession)
    setCurrentSession(newSession)

    return threadId
  }

  function updateSessionTitle(threadId: string, title: string) {
    const session = sessions.value.find(s => s.thread_id === threadId)
    if (session) {
      session.title = title
      session.updated_at = new Date().toISOString()
    }
  }

  function updateSessionMessageCount(threadId: string) {
    const session = sessions.value.find(s => s.thread_id === threadId)
    if (session) {
      session.message_count += 1
      session.updated_at = new Date().toISOString()
    }
  }

  function deleteSession(threadId: string) {
    const index = sessions.value.findIndex(s => s.thread_id === threadId)
    if (index !== -1) {
      sessions.value.splice(index, 1)
      if (currentSession.value?.thread_id === threadId) {
        currentSession.value = null
      }
    }
  }

  function addOrUpdateSession(session: Session) {
    const index = sessions.value.findIndex(s => s.thread_id === session.thread_id)
    if (index !== -1) {
      sessions.value[index] = session
    } else {
      sessions.value.unshift(session)
    }
  }

  async function fetchSessions() {
    isLoading.value = true
    try {
      // 调用 API
    } finally {
      isLoading.value = false
    }
  }

  return {
    sessions,
    currentSession,
    userId,
    isLoading,
    setUserId,
    setCurrentSession,
    createNewThread,
    updateSessionTitle,
    updateSessionMessageCount,
    deleteSession,
    addOrUpdateSession,
    fetchSessions,
  }
})
```

---

## 五、后端 API 接口规范

### 5.1 新增/修改的 API 接口

#### 5.1.1 获取文件列表（已存在，需规范化）

```
GET /api/v1/files
```

**响应:**
```json
{
  "files": [
    {
      "id": "file_id",
      "filename": "document.pdf",
      "size": 1048576,
      "upload_time": "2024-01-01T00:00:00Z",
      "status": "uploaded",
      "vectorized": true,
      "chunk_count": 10
    }
  ],
  "total": 1
}
```

#### 5.1.2 获取会话历史消息（新增）

```
GET /api/v1/sessions/{thread_id}/messages
```

**参数:**
- `thread_id`: 会话ID (path)
- `limit`: 限制数量 (query, 可选, 默认50)
- `before`: 分页游标 (query, 可选)

**响应:**
```json
{
  "messages": [
    {
      "id": "msg_id",
      "role": "user",
      "content": "用户消息",
      "timestamp": "2024-01-01T00:00:00Z"
    },
    {
      "id": "msg_id_2",
      "role": "assistant",
      "content": "助手回复",
      "timestamp": "2024-01-01T00:01:00Z"
    }
  ],
  "total": 2,
  "has_more": false
}
```

#### 5.1.3 重新生成消息（新增）

```
POST /api/v1/messages/{message_id}/regenerate
```

**请求:**
```json
{
  "thread_id": "session_thread_id"
}
```

**响应:**
```json
{
  "message_id": "new_msg_id",
  "role": "assistant",
  "content": "重新生成的内容",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### 5.1.4 复制消息（新增）

```
POST /api/v1/messages/{message_id}/copy
```

**响应:**
```json
{
  "content": "消息内容",
  "copied": true
}
```

#### 5.1.5 更新向量化状态（新增）

```
PATCH /api/v1/files/{file_id}
```

**请求:**
```json
{
  "vectorized": true,
  "chunk_count": 10
}
```

**响应:**
```json
{
  "status": "success",
  "file": {
    "id": "file_id",
    "vectorized": true,
    "chunk_count": 10
  }
}
```

### 5.2 更新 Pydantic 模型

```python
# backend/app/models/chat.py

class MessageListResponse(BaseModel):
    """消息列表响应"""
    messages: List[ChatMessage]
    total: int
    has_more: bool = False


class MessagePaginationParams(BaseModel):
    """消息分页参数"""
    limit: int = Field(default=50, ge=1, le=100)
    before: Optional[str] = None


class RegenerateMessageRequest(BaseModel):
    """重新生成消息请求"""
    thread_id: str = Field(..., description="会话ID")


class RegenerateMessageResponse(BaseModel):
    """重新生成消息响应"""
    message_id: str
    role: str
    content: str
    timestamp: datetime


class CopyMessageResponse(BaseModel):
    """复制消息响应"""
    content: str
    copied: bool


class FileUpdateRequest(BaseModel):
    """文件更新请求"""
    vectorized: bool = False
    chunk_count: Optional[int] = None


class FileResponse(BaseModel):
    """文件响应"""
    id: str
    filename: str
    size: int
    upload_time: datetime
    status: str
    vectorized: bool
    chunk_count: Optional[int] = None


class FileListResponse(BaseModel):
    """文件列表响应"""
    files: List[FileResponse]
    total: int
```

---

## 六、前后端数据流设计

### 6.1 WebSocket 消息流优化

```
客户端                               服务端
  |                                    |
  |-- [1] CONNECT ------------------>  |
  |                                    |-- [2] CONNECTED
  |  <-- { type: "connected" } -------  |
  |                                    |
  |-- [3] USER_MESSAGE ------------->  |
  |  { type: "user_message" }         |
  |      content: "问题"               |
  |      thread_id: "..."             |
  |                                    |
  |                                    |-- [4] Agent执行开始
  |                                    |    stream_mode="values"
  |                                    |
  |  <-- [5] AGENT_STEP ------------  |
  |      { type: "agent_step" }       |
  |      node: "generate_query..."    |
  |      message_type: "AIMessage"    |
  |      content: "..."               |
  |      tool_calls: [...]            |
  |                                    |
  |  <-- [6] AGENT_STEP ------------  |
  |      { type: "agent_step" }       |
  |      node: "tool_node"            |
  |      message_type: "ToolMessage"  |
  |      tool_result: "..."           |
  |                                    |
  |  <-- [7] AGENT_COMPLETE ---------  |
  |      { type: "agent_complete" }   |
  |      final_answer: "答案"         |
  |      thread_id: "..."             |
  |                                    |
```

### 6.2 会话切换数据流

```
用户点击会话
    ↓
SessionStore.setCurrentSession(session)
    ↓
ChatStore.clearMessages()
    ↓
GET /api/v1/sessions/{thread_id}/messages
    ↓
ChatStore.addMessage(...) 批量添加
    ↓
切换 WebSocket 连接（可选，保持长连接）
    ↓
准备就绪，用户可发送新消息
```

### 6.3 文件上传数据流

```
用户选择文件
    ↓
显示预览
    ↓
POST /api/v1/files/upload
    ↓
上传进度显示
    ↓
POST /api/v1/files/vectorize
    ↓
向量化进度（可选）
    ↓
GET /api/v1/files 刷新列表
    ↓
更新本地状态
```

---

## 七、响应式设计规范

### 7.1 断点定义

```css
/* 断点 */
@media (max-width: 1200px) {
  /* 平板横屏 */
}

@media (max-width: 768px) {
  /* 平板竖屏 */
}

@media (max-width: 480px) {
  /* 手机 */
}
```

### 7.2 响应式侧边栏

```css
.sidebar {
  width: 280px;
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: -280px;
    z-index: 100;
    transition: left 0.3s ease;
  }

  .sidebar.is-open {
    left: 0;
  }

  .sidebar-overlay {
    display: block;
  }
}
```

### 7.3 消息气泡响应式

```css
.message-bubble {
  max-width: 85%;
}

@media (max-width: 480px) {
  .message-bubble {
    max-width: 95%;
  }

  .bubble-content {
    gap: 8px;
  }

  .bubble-inner {
    padding: 10px 12px;
  }
}
```

---

## 八、UI/UX 细节规范

### 8.1 色彩规范

```css
/* 主色调 */
--primary-color: #1890ff;
--primary-hover: #40a9ff;
--primary-active: #096dd9;

/* 消息气泡 */
--user-bubble-bg: #1890ff;
--user-bubble-text: #ffffff;
--assistant-bubble-bg: #f5f5f5;
--assistant-bubble-text: #1a1a1a;

/* 中性色 */
--border-color: #e5e5e5;
--text-primary: #1a1a1a;
--text-secondary: #666666;
--text-placeholder: #999999;

/* 背景 */
--bg-primary: #ffffff;
--bg-secondary: #fafafa;
--bg-tertiary: #f5f5f5;
```

### 8.2 阴影规范

```css
/* 阴影级别 */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-md: 0 2px 8px rgba(0, 0, 0, 0.08);
--shadow-lg: 0 4px 16px rgba(0, 0, 0, 0.12);
--shadow-xl: 0 8px 24px rgba(0, 0, 0, 0.15);
```

### 8.3 间距规范

```css
/* 间距单位 */
--spacing-xs: 4px;
--spacing-sm: 8px;
--spacing-md: 12px;
--spacing-lg: 16px;
--spacing-xl: 24px;
--spacing-2xl: 32px;
```

### 8.4 圆角规范

```css
/* 圆角 */
--radius-sm: 4px;
--radius-md: 8px;
--radius-lg: 12px;
--radius-xl: 16px;
--radius-full: 9999px;
```

---

## 九、性能优化建议

### 9.1 消息虚拟滚动

对于长会话，使用虚拟滚动减少DOM节点：

```vue
<template>
  <VirtualList
    :items="messages"
    :item-size="80"
    :buffer="5"
  >
    <template #default="{ item }">
      <MessageBubble :message="item" />
    </template>
  </VirtualList>
</template>
```

### 9.2 图片懒加载

```typescript
// 使用 Intersection Observer API
const lazyLoadImages = () => {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target as HTMLImageElement
        img.src = img.dataset.src || ''
        observer.unobserve(img)
      }
    })
  })

  document.querySelectorAll('img[data-src]').forEach(img => {
    observer.observe(img)
  })
}
```

### 9.3 Markdown 渲染优化

```typescript
// 缓存渲染结果
const markdownCache = new Map<string, string>()

function renderMarkdown(content: string): string {
  if (markdownCache.has(content)) {
    return markdownCache.get(content)!
  }

  const html = marked(content)
  markdownCache.set(content, html)

  return html
}
```

---

## 十、实施优先级

### 阶段一：基础优化（高优先级）
1. 消息气泡样式优化和对齐
2. 对话框居中布局
3. 发送按钮图标化
4. 侧边栏可收缩功能

### 阶段二：功能增强（中优先级）
1. 输入框文件上传集成
2. 消息操作（复制、重新生成）
3. 会话历史加载
4. 知识库文件管理面板

### 阶段三：高级优化（低优先级）
1. 消息虚拟滚动
2. 响应式设计完善
3. 性能优化
4. 无障碍支持

---

## 十一、测试计划

### 11.1 单元测试
- 组件渲染测试
- 状态管理测试
- 工具函数测试

### 11.2 集成测试
- WebSocket 连接测试
- API 接口测试
- 前后端交互测试

### 11.3 E2E 测试
- 完整聊天流程
- 文件上传流程
- 会话切换流程

---

## 十二、部署建议

### 12.1 环境变量

```bash
# 前端
VITE_API_BASE_URL=https://api.buddy-ai.com
VITE_WS_BASE_URL=wss://api.buddy-ai.com
VITE_APP_TITLE=Buddy-AI 智能助手

# 后端
DASHSCOPE_API_KEY=your_key
TAVILY_API_KEY=your_key
REDIS_URL=redis://redis:6379/0
POSTGRESQL_URL=postgresql://...
```

### 12.2 Docker 部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7-alpine

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 附录

### A. 文件清单

**新增文件:**
- `D:\GithubProject\buddy-ai\frontend\src\components\chat\MessageBubble.vue`
- `D:\GithubProject\buddy-ai\frontend\src\components\chat\MessageActions.vue`
- `D:\GithubProject\buddy-ai\frontend\src\components\input\SendButton.vue`
- `D:\GithubProject\buddy-ai\frontend\src\components\input\AttachmentButton.vue`
- `D:\GithubProject\buddy-ai\frontend\src\panels\KnowledgeBasePanel.vue`
- `D:\GithubProject\buddy-ai\frontend\src\composables\useLocalStorage.ts`
- `D:\GithubProject\buddy-ai\frontend\src\api\messages.ts`

**修改文件:**
- `D:\GithubProject\buddy-ai\frontend\src\stores\chat.ts`
- `D:\GithubProject\buddy-ai\frontend\src\stores\session.ts`
- `D:\GithubProject\buddy-ai\frontend\src\components\Sidebar.vue`
- `D:\GithubProject\buddy-ai\frontend\src\components\ChatInput.vue`
- `D:\GithubProject\buddy-ai\frontend\src\components\ChatMessage.vue`
- `D:\GithubProject\buddy-ai\frontend\src\views\ChatView.vue`
- `D:\GithubProject\buddy-ai\frontend\src\types\index.ts`
- `D:\GithubProject\buddy-ai\backend\app\api\v1\messages.py` (新增)
- `D:\GithubProject\buddy-ai\backend\app\models\chat.py`

### B. 参考资料
- Vue3 官方文档: https://vuejs.org/
- Pinia 官方文档: https://pinia.vuejs.org/
- FastAPI 官方文档: https://fastapi.tiangolo.com/
- LangGraph 官方文档: https://langchain-ai.github.io/langgraph/