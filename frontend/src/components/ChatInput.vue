<template>
  <div class="chat-input-container">
    <div class="input-wrapper">
      <textarea
        v-model="inputMessage"
        class="chat-textarea"
        placeholder="输入您的问题..."
        rows="1"
        :disabled="isStreaming"
        @keydown="handleKeydown"
        @input="autoResize"
        ref="textareaRef"
      />
      <button
        class="send-button"
        :disabled="!inputMessage.trim() || isStreaming"
        @click="handleSend"
      >
        {{ isStreaming ? '⏳' : '发送' }}
      </button>
    </div>
    <div class="input-footer">
      <span class="footer-text">按 Enter 发送，Shift + Enter 换行</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'
import { useWebSocket } from '@/composables/useWebSocket'
import { useUserStore } from '@/stores/user'

const chatStore = useChatStore()
const sessionStore = useSessionStore()
const userStore = useUserStore()

const inputMessage = ref('')
const textareaRef = ref<HTMLTextAreaElement>()

const isStreaming = computed(() => chatStore.isStreaming)
const userId = computed(() => userStore.userId)

// WebSocket 连接
const { isConnected, connect, sendMessage } = useWebSocket(userId.value)

// 连接 WebSocket
connect()

function autoResize() {
  const textarea = textareaRef.value
  if (textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

async function handleSend() {
  if (!inputMessage.value.trim() || isStreaming.value) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''

  // 重置 textarea 高度
  nextTick(() => {
    autoResize()
  })

  // 添加用户消息
  chatStore.addMessage({
    role: 'user',
    content: message,
  })

  // 更新会话标题（如果是第一条消息）
  if (!sessionStore.currentSession?.title) {
    sessionStore.updateSessionTitle(
      sessionStore.currentSession.thread_id,
      message.slice(0, 30) + (message.length > 30 ? '...' : '')
    )
  }
  sessionStore.updateSessionMessageCount(sessionStore.currentSession.thread_id)

  // 设置流式状态
  chatStore.isStreaming = true

  // 发送消息到 WebSocket
  sendMessage(message, sessionStore.currentSession?.thread_id)
}
</script>

<style scoped>
.chat-input-container {
  padding: 24px;
  border-top: 1px solid #e5e5e5;
}

.input-wrapper {
  position: relative;
  max-width: 800px;
  margin: 0 auto;
}

.chat-textarea {
  width: 100%;
  min-height: 44px;
  max-height: 200px;
  padding: 12px 50px 12px 16px;
  border: 1px solid #e5e5e5;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.6;
  color: #1a1a1a;
  background: #fff;
  resize: none;
  outline: none;
  transition: all 0.2s;
  font-family: inherit;
}

.chat-textarea:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.1);
}

.chat-textarea:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.chat-textarea::placeholder {
  color: #999;
}

.send-button {
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: #1890ff;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-button:hover:not(:disabled) {
  background: #40a9ff;
}

.send-button:disabled {
  background: #d0d0d0;
  cursor: not-allowed;
}

.input-footer {
  text-align: center;
  margin-top: 8px;
}

.footer-text {
  font-size: 12px;
  color: #999;
}
</style>