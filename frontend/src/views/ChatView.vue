<template>
  <div class="chat-container">
    <!-- 侧边栏 - 会话列表 -->
    <Sidebar class="sidebar" @showFileUpload="showFileUploadModal = true" />

    <!-- 主聊天区域 -->
    <div class="main-chat">
      <!-- 顶部标题栏 -->
      <div class="chat-header">
        <h1>Buddy-AI 智能助手</h1>
        <button class="new-chat-btn" @click="handleNewChat">
          <span>+</span> 新对话
        </button>
      </div>

      <!-- 聊天消息区域 -->
      <div class="messages-container">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-icon">🤖</div>
          <h2>你好！我是 Buddy-AI</h2>
          <p>我可以帮你回答问题、检索知识库、保存记忆等</p>
        </div>

        <div v-else class="messages-list">
          <ChatMessage
            v-for="(msg, index) in messages"
            :key="index"
            :message="msg"
          />
          <div v-if="isStreaming" class="streaming-indicator">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <ChatInput />
    </div>

    <!-- 调试面板 -->
    <DebugPanel
      v-if="showDebug"
      :debug-info="debugInfo"
      class="debug-panel"
      @close="showDebug = false"
      @clear="debugInfo = []"
    />

    <!-- 文件上传模态框 -->
    <FileUpload
      :visible="showFileUploadModal"
      @close="showFileUploadModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'
import { useUserStore } from '@/stores/user'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'
import Sidebar from '@/components/Sidebar.vue'
import DebugPanel from '@/components/DebugPanel.vue'
import FileUpload from '@/components/FileUpload.vue'

const chatStore = useChatStore()
const sessionStore = useSessionStore()
const userStore = useUserStore()

const showDebug = ref(false)
const showFileUploadModal = ref(false)

const messages = computed(() => chatStore.messages)
const isStreaming = computed(() => chatStore.isStreaming)
const debugInfo = computed(() => chatStore.debugInfo)

function handleNewChat() {
  chatStore.clearMessages()
  const threadId = sessionStore.createNewThread()
  console.log('创建新会话:', threadId)
}

onMounted(() => {
  // 创建初始会话
  if (!sessionStore.currentSession) {
    sessionStore.createNewThread()
  }
})
</script>

<style scoped>
.chat-container {
  display: flex;
  width: 100%;
  height: 100vh;
  background-color: #fff;
}

.sidebar {
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid #e5e5e5;
}

.main-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #e5e5e5;
}

.chat-header h1 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
  color: #666;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.new-chat-btn:hover {
  background: #f5f5f5;
  border-color: #d0d0d0;
}

.new-chat-btn span {
  font-size: 18px;
  font-weight: 300;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state h2 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1a1a1a;
}

.empty-state p {
  font-size: 14px;
  color: #666;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.streaming-indicator {
  display: flex;
  gap: 6px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 12px;
  width: fit-content;
}

.streaming-indicator .dot {
  width: 8px;
  height: 8px;
  background: #1890ff;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.streaming-indicator .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.streaming-indicator .dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%,
  80%,
  100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.debug-panel {
  width: 300px;
  flex-shrink: 0;
  border-left: 1px solid #e5e5e5;
}
</style>