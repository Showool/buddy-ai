<template>
  <div class="chat-input-container">
    <div class="input-wrapper">
      <!-- 输入框 -->
      <el-input
        v-model="inputMessage"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 8 }"
        placeholder="输入您的问题... (Enter 发送, Shift+Enter 换行)"
        :disabled="isStreaming"
        @keydown="handleKeydown"
        class="chat-input"
      />

      <!-- 发送按钮 -->
      <el-button
        type="primary"
        circle
        :icon="isStreaming ? Loading : Promotion"
        :loading="isStreaming"
        :disabled="!inputMessage.trim() || isStreaming"
        class="send-button"
        @click="handleSend"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'
import { useWebSocket } from '@/composables/useWebSocket'
import { useUserStore } from '@/stores/user'
import type { Message } from '@/types'
import { Loading, Promotion } from '@element-plus/icons-vue'

const chatStore = useChatStore()
const sessionStore = useSessionStore()
const userStore = useUserStore()

const inputMessage = ref('')
const isStreaming = computed(() => chatStore.isStreaming)
const userId = computed(() => userStore.userId)

const { connect, sendMessage } = useWebSocket(userId.value)
connect()

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

  const userMessage: Message = {
    role: 'user',
    content: message,
  }

  chatStore.addMessage(userMessage)

  if (!sessionStore.currentSession?.title && sessionStore.currentSession?.thread_id) {
    sessionStore.updateSessionTitle(
      sessionStore.currentSession.thread_id,
      message.slice(0, 30) + (message.length > 30 ? '...' : '')
    )
  }
  if (sessionStore.currentSession?.thread_id) {
    sessionStore.updateSessionMessageCount(sessionStore.currentSession.thread_id)
  }

  chatStore.isStreaming = true
  sendMessage(message, sessionStore.currentSession?.thread_id)
}
</script>

<style scoped>
.chat-input-container {
  padding: 16px;
  background: var(--el-bg-color-overlay);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--el-border-color);
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 900px;
  margin: 0 auto;
  background: var(--el-bg-color);
  border-radius: 16px;
  border: 1px solid var(--el-border-color);
  padding: 4px;
}

.input-wrapper:deep(.el-textarea__inner) {
  padding-right: 12px;
  padding-left: 8px;
  padding-top: 12px;
  padding-bottom: 12px;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  min-height: 60px;
}

.send-button {
  background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 100%);
  border-color: transparent;
}

.send-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #ffaa66 0%, #ff7b7b 100%);
}
</style>