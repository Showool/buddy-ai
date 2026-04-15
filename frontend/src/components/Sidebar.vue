<template>
  <aside class="sidebar">
    <h1 class="sidebar-title">Buddy-AI</h1>

    <SidebarSettings />

    <el-button type="primary" class="new-chat-btn" @click="createNewChat">
      + 新建对话
    </el-button>

    <div class="thread-list">
      <div
        v-for="thread in chatStore.threadList"
        :key="thread.threadId"
        class="thread-item"
        :class="{ active: thread.threadId === chatStore.currentThreadId }"
        @click="navigateToThread(thread.threadId)"
      >
        <span class="thread-title">{{ thread.title || '新对话' }}</span>
        <button
          class="delete-btn"
          title="删除对话"
          @click.stop="handleDelete(thread.threadId)"
        >
          ✕
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { nanoid } from 'nanoid'
import SidebarSettings from './SidebarSettings.vue'

const router = useRouter()
const chatStore = useChatStore()

function createNewChat() {
  const threadId = nanoid()
  chatStore.createThread(threadId, '新对话')
  router.push(`/chat/${threadId}`)
}

function navigateToThread(threadId: string) {
  chatStore.switchThread(threadId)
  router.push(`/chat/${threadId}`)
}

function handleDelete(threadId: string) {
  chatStore.cancelActiveStream()
  chatStore.deleteThread(threadId)
  // 如果删除的是当前对话，回到首页
  if (chatStore.currentThreadId === null) {
    router.push('/')
  }
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
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
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

.thread-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.delete-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  font-size: 12px;
  flex-shrink: 0;
  margin-left: 4px;
}

.thread-item:hover .delete-btn {
  display: flex;
}

.delete-btn:hover {
  background-color: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}
</style>
