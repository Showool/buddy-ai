<template>
  <aside class="sidebar">
    <h1 class="sidebar-title">Buddy-AI</h1>

    <SidebarSettings />

    <el-button round class="new-chat-btn" @click="createNewChat">
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
    
    <div class="kb-section">
      <div class="kb-header">
        <span class="kb-title">知识库文件</span>
        <button class="kb-refresh-btn" title="刷新" @click="fetchFiles">⟳</button>
      </div>
      <div v-if="fileLoading" class="kb-loading">加载中...</div>
      <div v-else-if="fileList.length === 0" class="kb-empty">暂无文件</div>
      <div v-else class="file-list">
        <div v-for="file in fileList" :key="file.id" class="file-item">
          <span class="file-name" :title="file.file_name">{{ file.file_name }}</span>
          <span class="file-actions">
            <button class="file-action-btn download-btn" title="下载" @click="handleDownload(file)">⤓</button>
            <button class="file-action-btn file-delete-btn" title="删除" @click="handleDeleteFile(file)">✕</button>
          </span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { nanoid } from 'nanoid'
import { getFiles, deleteFile, downloadFile } from '@/services/api'
import type { KnowledgeFile } from '@/types'
import SidebarSettings from './SidebarSettings.vue'

const router = useRouter()
const chatStore = useChatStore()
const userStore = useUserStore()

const fileList = ref<KnowledgeFile[]>([])
const fileLoading = ref(false)
const knowledgeId = 1 // 默认知识库ID

async function fetchFiles() {
  if (!userStore.userId) return
  fileLoading.value = true
  try {
    fileList.value = await getFiles(userStore.userId, knowledgeId)
  } catch (e) {
    console.error('获取文件列表失败', e)
  } finally {
    fileLoading.value = false
  }
}

async function handleDownload(file: KnowledgeFile) {
  try {
    await downloadFile(file.id, file.file_name)
  } catch (e) {
    console.error('下载失败', e)
  }
}

async function handleDeleteFile(file: KnowledgeFile) {
  if (!userStore.userId) return
  try {
    await deleteFile(userStore.userId, knowledgeId, file.id)
    fileList.value = fileList.value.filter((f) => f.id !== file.id)
  } catch (e) {
    console.error('删除文件失败', e)
  }
}

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
  if (chatStore.currentThreadId === null) {
    router.push('/')
  }
}

onMounted(() => {
  fetchFiles()
})

watch(() => userStore.userId, (val) => {
  if (val) fetchFiles()
})

watch(() => userStore.kbNeedRefresh, (val) => {
  if (val) {
    fetchFiles()
    userStore.kbNeedRefresh = false
  }
})
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
  max-height: 40%;
}

.thread-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;
  margin-bottom: 8px;
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

/* 知识库文件区域 */
.kb-section {
  border-top: 1px solid var(--el-border-color);
  margin-top: 12px;
  padding-top: 12px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.kb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.kb-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
}

.kb-refresh-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  color: var(--el-text-color-secondary);
  padding: 2px 4px;
  border-radius: 4px;
}

.kb-refresh-btn:hover {
  background-color: var(--el-fill-color-light);
  color: var(--el-color-primary);
}

.kb-loading,
.kb-empty {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  text-align: center;
  padding: 8px 0;
}

.file-list {
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 6px 8px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 6px;
  transition: background-color 0.2s;
}

.file-item:hover {
  background-color: var(--el-fill-color-light);
}

.file-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-actions {
  display: none;
  gap: 2px;
  flex-shrink: 0;
  margin-left: 4px;
}

.file-item:hover .file-actions {
  display: flex;
}

.file-action-btn {
  display: flex;
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
}

.download-btn:hover {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.file-delete-btn:hover {
  background-color: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}
</style>
