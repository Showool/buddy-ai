<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <div class="logo">🤖</div>
      <div class="app-name">Buddy-AI</div>
    </div>

    <div class="sidebar-content">
      <div class="section">
        <div class="section-title">会话列表</div>
        <div class="sessions-list">
          <div
            v-for="session in sessions"
            :key="session.thread_id"
            class="session-item"
            :class="{ active: currentSession?.thread_id === session.thread_id }"
            @click="handleSelectSession(session)"
          >
            <div class="session-icon">💬</div>
            <div class="session-info">
              <div class="session-title">
                {{ session.title || '新对话' }}
              </div>
              <div class="session-time">{{ formatTime(session.updated_at) }}</div>
            </div>
            <button
              class="session-delete"
              @click.stop="handleDeleteSession(session.thread_id)"
            >
              ✕
            </button>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">知识库管理</div>
        <button class="action-button" @click="showFileUpload = true">
          📁 上传文件
        </button>
      </div>

      <div class="section">
        <div class="section-title">用户设置</div>
        <div class="setting-item">
          <label>用户 ID</label>
          <input
            v-model="userId"
            type="text"
            class="setting-input"
            @change="handleUserIdChange"
          />
        </div>
      </div>
    </div>

    <div class="sidebar-footer">
      <button class="action-button" @click="handleClearConversation">
        🗑️ 清除对话
      </button>
      <button class="action-button" @click="showDebug = !showDebug">
        {{ showDebug ? '🔧 关闭调试' : '🔧 调试面板' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import type { Session } from '@/types'

const emit = defineEmits<{
  (e: 'clearConversation'): void
  (e: 'toggleDebug'): void
  (e: 'showFileUpload'): void
}>()

const sessionStore = useSessionStore()
const chatStore = useChatStore()
const userStore = useUserStore()

const sessions = computed(() => sessionStore.sessions)
const currentSession = computed(() => sessionStore.currentSession)
const userId = computed({
  get: () => userStore.userId,
  set: (val) => userStore.setUserId(val),
})

const showDebug = computed({
  get: () => chatStore.debugPanelVisible,
  set: (val) => emit('toggleDebug'),
})

const showFileUpload = ref(false)

function handleSelectSession(session: Session) {
  sessionStore.setCurrentSession(session)
  // TODO: 加载会话历史消息
}

function handleDeleteSession(threadId: string) {
  if (confirm('确定要删除这个会话吗？')) {
    sessionStore.deleteSession(threadId)
  }
}

function handleClearConversation() {
  if (confirm('确定要清除当前对话吗？')) {
    chatStore.clearMessages()
    emit('clearConversation')
  }
}

function handleUserIdChange() {
  console.log('用户 ID 已更新:', userId.value)
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`

  return date.toLocaleDateString()
}
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f5f5;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e5e5e5;
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo {
  font-size: 28px;
}

.app-name {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.sidebar-content {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-bottom: 8px;
}

.sessions-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.session-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

.session-item.active {
  background: rgba(24, 144, 255, 0.1);
}

.session-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 14px;
  color: #1a1a1a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-time {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

.session-delete {
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: #999;
  font-size: 12px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.session-item:hover .session-delete {
  opacity: 1;
}

.session-delete:hover {
  color: #ff4d4f;
}

.action-button {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
  color: #1a1a1a;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.action-button:hover {
  background: #fff;
  border-color: #d0d0d0;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.setting-item label {
  font-size: 12px;
  color: #666;
}

.setting-input {
  padding: 8px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 14px;
  background: #fff;
}

.setting-input:focus {
  outline: none;
  border-color: #1890ff;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #e5e5e5;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>