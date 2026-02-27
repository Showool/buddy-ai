<template>
  <transition name="message-fade" appear>
    <div class="chat-message" :class="`message-${message.role}`">
      <!-- 消息头像 -->
      <div class="message-avatar">
        <el-avatar v-if="message.role === 'user'" :size="40" class="avatar-user">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="7" r="3" fill="#ffffff" />
            <path d="M5 15C5 12.2386 7.23858 10 10 10C12.7614 10 15 12.2386 15 15" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" />
          </svg>
        </el-avatar>
        <div v-else class="avatar-ai">
          <IconBuddy />
        </div>
      </div>

      <!-- 消息内容 -->
      <div class="message-content">
        <div class="message-sender">
          {{ message.role === 'user' ? '你' : 'Buddy-AI' }}
        </div>
        <div class="message-bubble">
          <div v-if="message.file" class="file-attachment">
            <el-tag type="info" size="small" class="file-tag">
              <el-icon><Document /></el-icon>
              <span>{{ message.file.filename }}</span>
              <span class="file-size">{{ formatFileSize(message.file.size) }}</span>
            </el-tag>
          </div>
          <div class="message-text">{{ message.content }}</div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import type { Message } from '@/types'
import IconBuddy from '@/components/icons/IconBuddy.vue'
import { Document } from '@element-plus/icons-vue'

interface Props {
  message: Message
}

const props = defineProps<Props>()

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped>
/* ========================================
   消息容器
   ======================================== */
.chat-message {
  display: flex;
  width: 100%;
  gap: 12px;
  animation: messageSlideIn 0.3s ease-out;
}

@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chat-message.message-user {
  flex-direction: row-reverse;
}

.chat-message.message-user .message-content {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.chat-message.message-assistant .message-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

/* ========================================
   消息头像
   ======================================== */
.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.message-avatar:hover {
  transform: scale(1.05);
}

.chat-message.message-user .message-avatar {
  background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 100%);
  box-shadow: 0 2px 8px rgba(255, 154, 86, 0.4);
}

.chat-message.message-assistant .message-avatar {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
}

.chat-message.message-assistant .avatar-ai {
  color: #ff6b6b;
}

.chat-message.message-user :deep(.el-avatar) {
  background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 100%);
}

/* ========================================
   消息内容
   ======================================== */
.message-content {
  flex: 1;
  max-width: calc(100% - 56px);
}

/* ========================================
   发送者标签
   ======================================== */
.message-sender {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
  opacity: 1;
  height: auto;
}

.chat-message.message-user .message-sender {
  text-align: right;
}

/* ========================================
   消息气泡
   ======================================== */
.message-bubble {
  padding: 12px 16px;
  border-radius: 8px;
  transition: all 0.2s ease;
  max-width: 100%;
}

.chat-message.message-user .message-bubble {
  background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 100%);
  color: #ffffff;
  border-top-right-radius: 4px;
  box-shadow: 0 2px 8px rgba(255, 154, 86, 0.3);
}

.chat-message.message-assistant .message-bubble {
  background: var(--el-bg-color);
  color: var(--el-text-color-primary);
  border: 1px solid var(--el-border-color);
  border-top-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.chat-message.message-user:hover .message-bubble {
  box-shadow: 0 4px 12px rgba(255, 154, 86, 0.4);
  transform: translateY(-2px);
}

.chat-message.message-assistant:hover .message-bubble {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-color: var(--el-border-color-light);
  transform: translateY(-2px);
}

/* ========================================
   文件附件
   ======================================== */
.file-attachment {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.file-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}

.chat-message.message-user .file-tag {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

.chat-message.message-user .file-tag :deep(.el-tag__content) {
  color: #ffffff;
}

.file-size {
  margin-left: 4px;
  opacity: 0.8;
}

/* ========================================
   消息文本
   ======================================== */
.message-text {
  font-size: 14px;
  line-height: 1.6;
}

/* ========================================
   过渡动画
   ======================================== */
.message-fade-enter-active {
  transition: all 0.3s ease;
}

.message-fade-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.message-fade-enter-to {
  opacity: 1;
  transform: translateY(0);
}

/* ========================================
   响应式调整
   ======================================== */
@media (max-width: 768px) {
  .chat-message {
    gap: 8px;
  }

  .message-avatar {
    width: 36px;
    height: 36px;
  }

  .message-content {
    max-width: calc(100% - 52px);
  }

  .message-bubble {
    padding: 8px 12px;
  }

  .message-text {
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .message-avatar {
    width: 32px;
    height: 32px;
  }

  .message-content {
    max-width: calc(100% - 48px);
  }

  .message-bubble {
    padding: 6px 10px;
  }

  .message-sender {
    font-size: 12px;
  }
}
</style>