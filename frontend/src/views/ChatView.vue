<template>
  <div class="chat-container">
    <!-- 侧边栏 - 会话列表 -->
    <Sidebar
      class="sidebar"
      :class="{ 'mobile-open': mobileSidebarOpen }"
      @toggleSidebar="toggleMobileSidebar"
    />

    <!-- 主聊天区域 -->
    <div class="main-chat">
      <!-- 顶部标题栏 -->
      <div class="chat-header">
        <div class="header-left">
          <el-button
            circle
            :icon="Menu"
            class="menu-toggle"
            @click="toggleMobileSidebar"
          />
          <div class="header-title">
            <h1>Buddy-AI</h1>
            <span class="header-subtitle">智能助手</span>
          </div>
        </div>
      </div>

      <!-- 聊天消息区域 -->
      <div class="messages-container" ref="messagesContainer">
        <div v-if="messages.length === 0" class="empty-state">
          <transition name="fade">
            <div class="empty-icon-wrapper">
              <IconBuddy class="empty-icon" />
            </div>
          </transition>
          <h2>你好！我是 Buddy-AI</h2>
          <p>我可以帮你回答问题、检索知识库、保存记忆等</p>
        </div>

        <div v-else class="messages-list">
          <ChatMessage
            v-for="(msg, index) in messages"
            :key="`${msg.role}-${index}`"
            :message="msg"
          />
          <div v-if="isStreaming" class="streaming-indicator">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
          <div ref="messagesEndRef" class="messages-end"></div>
        </div>
      </div>

      <!-- 输入区域 -->
      <ChatInput />
    </div>

    <!-- 移动端侧边栏遮罩 -->
    <transition name="fade">
      <div
        v-if="mobileSidebarOpen"
        class="sidebar-overlay"
        @click="toggleMobileSidebar"
      ></div>
    </transition>

    <!-- 调试面板 -->
    <DebugPanel
      v-if="showDebug"
      :debug-info="debugInfo"
      class="debug-panel"
      @close="showDebug = false"
      @clear="chatStore.clearDebug()"
    />

    <!-- 文件上传模态框 -->
    <FileUpload
      :visible="showFileUploadModal"
      @close="showFileUploadModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'
import { useUserStore } from '@/stores/user'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'
import Sidebar from '@/components/Sidebar.vue'
import DebugPanel from '@/components/DebugPanel.vue'
import FileUpload from '@/components/FileUpload.vue'
import IconBuddy from '@/components/icons/IconBuddy.vue'
import {
  Menu
} from '@element-plus/icons-vue'

const chatStore = useChatStore()
const sessionStore = useSessionStore()
const userStore = useUserStore()

const showDebug = ref(false)
const showFileUploadModal = ref(false)
const mobileSidebarOpen = ref(false)
const messagesContainer = ref<HTMLElement>()
const messagesEndRef = ref<HTMLElement>()

const messages = computed(() => chatStore.messages)
const isStreaming = computed(() => chatStore.isStreaming)
const debugInfo = computed(() => chatStore.debugInfo)

// 自动滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesEndRef.value) {
      messagesEndRef.value.scrollIntoView({ behavior: 'smooth' })
    }
  })
}

// 监听消息变化，自动滚动
watch(() => messages.value.length, () => {
  scrollToBottom()
})

watch(() => isStreaming.value, (streaming) => {
  if (!streaming) {
    scrollToBottom()
  }
})

function toggleMobileSidebar() {
  mobileSidebarOpen.value = !mobileSidebarOpen.value
}

onMounted(() => {
  // 创建初始会话
  if (!sessionStore.currentSession) {
    sessionStore.createNewThread()
  }
})
</script>

<style scoped>
/* ========================================
   主容器
   ======================================== */
.chat-container {
  display: flex;
  width: 100%;
  height: 100vh;
  background: var(--el-bg-color-page);
  position: relative;
}

/* ========================================
   侧边栏
   ======================================== */
.sidebar {
  flex-shrink: 0;
  border-right: 1px solid var(--el-border-color);
  transition: transform 0.3s ease;
  z-index: 100;
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    z-index: 200;
  }

  .sidebar.mobile-open {
    transform: translateX(0);
  }

  .sidebar-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(4px);
    z-index: 199;
  }
}

/* ========================================
   主聊天区域
   ======================================== */
.main-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  background: linear-gradient(
    to bottom,
    var(--el-bg-color-page) 0%,
    var(--el-bg-color) 100%
  );
}

/* ========================================
   标题栏
   ======================================== */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color);
  background: var(--el-bg-color);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-toggle {
  flex-shrink: 0;
}

@media (min-width: 769px) {
  .menu-toggle {
    display: none;
  }
}

.header-title h1 {
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
  background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 50%, #ffd93d 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-subtitle {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-left: 8px;
}

/* ========================================
   消息容器
   ======================================== */
.messages-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 24px 16px;
  scroll-behavior: smooth;
}

.messages-list {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.messages-end {
  height: 16px;
}

/* ========================================
   空状态
   ======================================== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--el-text-color-secondary);
  text-align: center;
  padding: 32px;
}

.empty-icon-wrapper {
  position: relative;
  margin-bottom: 24px;
}

.empty-icon {
  width: 120px;
  height: 120px;
  color: #ff9a56;
  animation: float 3s ease-in-out infinite;
  filter: drop-shadow(0 0 20px rgba(255, 154, 86, 0.3));
}

.empty-state h2 {
  font-size: 32px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
}

.empty-state p {
  font-size: 18px;
  color: var(--el-text-color-secondary);
  max-width: 400px;
  line-height: 1.6;
  margin-bottom: 32px;
}

/* ========================================
   流式输入指示器
   ======================================== */
.streaming-indicator {
  display: flex;
  gap: 6px;
  padding: 12px;
  background: var(--el-bg-color);
  border-radius: 12px;
  width: fit-content;
  margin: 0 auto;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.streaming-indicator .dot {
  width: 8px;
  height: 8px;
  background: #667eea;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.streaming-indicator .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.streaming-indicator .dot:nth-child(2) {
  animation-delay: -0.16s;
}

/* ========================================
   调试面板
   ======================================== */
.debug-panel {
  width: 300px;
  flex-shrink: 0;
  border-left: 1px solid var(--el-border-color);
  background: var(--el-bg-color);
}

@media (max-width: 768px) {
  .debug-panel {
    display: none;
  }
}

/* ========================================
   响应式调整
   ======================================== */
@media (max-width: 640px) {
  .messages-container {
    padding: 16px 12px;
  }

  .messages-list {
    gap: 16px;
  }

  .chat-header {
    padding: 8px 12px;
  }

  .header-title h1 {
    font-size: 18px;
  }

  .header-subtitle {
    display: none;
  }

  .empty-icon {
    width: 80px;
    height: 80px;
  }

  .empty-state h2 {
    font-size: 24px;
  }

  .empty-state p {
    font-size: 14px;
  }
}

/* ========================================
   动画
   ======================================== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}
</style>