<template>
  <aside class="sidebar">
    <h1 class="sidebar-title">Buddy-AI</h1>

    <SidebarSettings />

    <el-button type="primary" class="new-chat-btn" @click="createNewChat">
      + 新建对话
    </el-button>

    <div class="thread-list">
      <div
        v-for="thread in chatStore.getThreadList()"
        :key="thread.threadId"
        class="thread-item"
        :class="{ active: thread.threadId === chatStore.currentThreadId }"
        @click="navigateToThread(thread.threadId)"
      >
        {{ thread.title || '新对话' }}
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import SidebarSettings from './SidebarSettings.vue'

const router = useRouter()
const chatStore = useChatStore()

function createNewChat() {
  const threadId = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
  chatStore.createThread(threadId, '新对话')
  router.push(`/chat/${threadId}`)
}

function navigateToThread(threadId: string) {
  chatStore.switchThread(threadId)
  router.push(`/chat/${threadId}`)
}
</script>

<style scoped>
.sidebar {
  width: 260px;
  min-width: 260px;
  height: 100vh;
  border-right: 1px solid var(--el-border-color);
  display: flex;
  flex-direction: column;
  padding: 16px;
  background-color: var(--el-bg-color);
  overflow-y: auto;
}

.sidebar-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 8px;
}

.new-chat-btn {
  width: 100%;
  margin-bottom: 12px;
}

.thread-list {
  flex: 1;
  overflow-y: auto;
}

.thread-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  transition: background-color 0.2s;
}

.thread-item:hover {
  background-color: var(--el-fill-color-light);
}

.thread-item.active {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 500;
}
</style>
