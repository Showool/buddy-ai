<template>
  <div class="chat-input-container">
    <div class="input-wrapper">
      <!-- 左侧操作按钮 -->
      <div class="input-actions">
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :show-file-list="false"
          :accept="acceptTypes"
          :on-change="handleFileSelect"
        >
          <el-button
            circle
            :icon="Upload"
            :disabled="isStreaming"
            class="action-button"
          />
        </el-upload>
      </div>

      <!-- 输入框 -->
      <el-input
        v-model="inputMessage"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 8 }"
        placeholder="输入您的问题..."
        :disabled="isStreaming"
        @keydown="handleKeydown"
        class="chat-input"
      />

      <!-- 文件附件 -->
      <div v-if="selectedFile" class="file-attachment">
        <el-icon class="file-icon"><Document /></el-icon>
        <span class="file-name">{{ selectedFile.name }}</span>
        <el-button
          :icon="Close"
          circle
          size="small"
          class="file-remove"
          @click="removeFile"
        />
      </div>

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
import { ref, computed, nextTick } from 'vue'
import type { UploadInstance, UploadUserFile } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'
import { useWebSocket } from '@/composables/useWebSocket'
import { useUserStore } from '@/stores/user'
import { filesApi } from '@/api/files'
import type { Message, UploadedFile } from '@/types'
import {
  Upload,
  Document,
  Close,
  Loading,
  Promotion
} from '@element-plus/icons-vue'

const chatStore = useChatStore()
const sessionStore = useSessionStore()
const userStore = useUserStore()

const uploadRef = ref<UploadInstance>()
const inputMessage = ref('')
const selectedFile = ref<File | null>(null)
const uploadedFile = ref<UploadedFile | null>(null)

const acceptTypes = '.pdf,.docx,.txt,.md,.csv'

const isStreaming = computed(() => chatStore.isStreaming)
const userId = computed(() => userStore.userId)

// WebSocket 连接
const { isConnected, connect, sendMessage } = useWebSocket(userId.value)

// 连接 WebSocket
connect()

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

async function handleFileSelect(file: UploadUserFile) {
  const rawFile = file.raw
  if (rawFile) {
    selectedFile.value = rawFile

    // 自动上传文件
    try {
      const uploaded = await filesApi.upload(rawFile)
      uploadedFile.value = uploaded
    } catch (error) {
      console.error('上传文件失败:', error)
      // 使用 Element Plus 的消息提示
      console.error('上传文件失败')
      selectedFile.value = null
    }
  }
}

function removeFile() {
  selectedFile.value = null
  uploadedFile.value = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

async function handleSend() {
  if (!inputMessage.value.trim() || isStreaming.value) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''

  // 添加用户消息
  const userMessage: Message = {
    role: 'user',
    content: message,
  }

  // 如果有上传的文件，添加文件信息到消息
  if (uploadedFile.value) {
    userMessage.file = uploadedFile.value
  }

  chatStore.addMessage(userMessage)

  // 更新会话标题（如果是第一条消息）
  if (!sessionStore.currentSession?.title && sessionStore.currentSession?.thread_id) {
    sessionStore.updateSessionTitle(
      sessionStore.currentSession.thread_id,
      message.slice(0, 30) + (message.length > 30 ? '...' : '')
    )
  }
  if (sessionStore.currentSession?.thread_id) {
    sessionStore.updateSessionMessageCount(sessionStore.currentSession.thread_id)
  }

  // 设置流式状态
  chatStore.isStreaming = true

  // 清除文件选择
  removeFile()

  // 发送消息到 WebSocket
  sendMessage(message, sessionStore.currentSession?.thread_id)
}
</script>

<style scoped>
/* ========================================
   输入容器
   ======================================== */
.chat-input-container {
  padding: 16px;
  background: var(--el-bg-color-overlay);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--el-border-color);
  position: relative;
}

/* ========================================
   输入框包装器
   ======================================== */
.input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 900px;
  margin: 0 auto;
  background: var(--el-bg-color);
  border-radius: 16px;
  border: 1px solid var(--el-border-color);
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
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
  line-height: 1.6;
  min-height: 60px;
}

.input-wrapper:deep(.el-textarea__inner):focus {
  box-shadow: none;
}

.input-wrapper:focus-within {
  border-color: #ff9a56;
  box-shadow: 0 0 0 2px rgba(255, 154, 86, 0.1), 0 4px 12px rgba(0, 0, 0, 0.05);
}

/* ========================================
   左侧操作按钮
   ======================================== */
.input-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.action-button {
  flex-shrink: 0;
}

/* ========================================
   文件附件
   ======================================== */
.file-attachment {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(255, 154, 86, 0.1);
  border: 1px solid #ff9a56;
  border-radius: 8px;
  font-size: 14px;
  color: #ff9a56;
}

.file-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.file-name {
  flex: 1;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #ff9a56;
  font-weight: 500;
}

.file-remove {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  padding: 0;
}

/* ========================================
   发送按钮
   ======================================== */
.send-button {
  flex-shrink: 0;
  background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 100%);
  border-color: transparent;
}

.send-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #ffaa66 0%, #ff7b7b 100%);
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(255, 154, 86, 0.4);
}

.send-button:active:not(:disabled) {
  transform: scale(0.95);
}

/* ========================================
   响应式调整
   ======================================== */
@media (max-width: 640px) {
  .chat-input-container {
    padding: 12px;
  }

  .input-wrapper {
    max-width: 100%;
    gap: 4px;
  }

  .input-wrapper:deep(.el-textarea__inner) {
    padding-right: 8px;
    padding-left: 4px;
    padding-top: 8px;
    padding-bottom: 8px;
    min-height: 52px;
  }

  .file-attachment {
    padding: 4px 8px;
  }

  .file-name {
    max-width: 120px;
  }
}
</style>