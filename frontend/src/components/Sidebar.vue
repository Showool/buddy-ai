<template>
  <div class="sidebar" :class="{ 'sidebar-collapsed': collapsed }">
    <!-- 侧边栏头部 -->
    <div class="sidebar-header">
      <div class="logo">
        <IconBuddy />
      </div>
      <transition name="fade">
        <div v-if="!collapsed" class="app-name">
          <span class="name">Buddy-AI</span>
          <span class="tag">智能助手</span>
        </div>
      </transition>
      <el-button
        circle
        :icon="collapsed ? Expand : Fold"
        class="collapse-toggle"
        @click="toggleCollapse"
      />
    </div>

    <!-- 侧边栏菜单 -->
    <div class="sidebar-content">
      <el-menu
        :collapse="collapsed"
        :default-active="defaultActive"
        class="sidebar-menu"
        @select="handleMenuSelect"
      >
        <!-- 会话列表 -->
        <template v-if="sessions.length > 0">
          <el-sub-menu
            v-for="session in sessions"
            :key="`session-${session.thread_id}`"
            :index="`session-${session.thread_id}`"
          >
            <template #title>
              <div class="session-title-wrapper">
                <el-icon class="session-icon"><ChatDotRound /></el-icon>
                <span>{{ session.title || '新对话' }}</span>
                <el-button
                  type="danger"
                  size="small"
                  text
                  :icon="Close"
                  class="session-delete"
                  @click.stop="handleDeleteSession(session.thread_id)"
                />
              </div>
            </template>
            <div class="session-meta">
              <span>{{ formatTime(session.updated_at) }}</span>
              <span>{{ session.message_count || 0 }} 条消息</span>
            </div>
          </el-sub-menu>
        </template>

        <!-- 知识库文件 -->
        <el-sub-menu v-if="knowledgeFiles.length > 0" index="files">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>知识库文件</span>
            <el-tag size="small" type="info" class="file-count">
              {{ knowledgeFiles.length }}
            </el-tag>
          </template>
          <div class="files-list">
            <div
              v-for="file in knowledgeFiles"
              :key="file.id"
              class="file-item"
            >
              <span class="file-icon">{{ getFileIcon(file.filename) }}</span>
              <span class="file-name" :title="file.filename">{{ file.filename }}</span>
              <el-tag
                size="small"
                :type="getFileStatusTagType(file.status)"
              >
                {{ getFileStatus(file.status).text }}
              </el-tag>
              <el-button
                type="danger"
                size="small"
                text
                :icon="Close"
                class="file-delete"
                @click="handleDeleteFile(file.id)"
              />
            </div>
          </div>
        </el-sub-menu>

        <!-- 新建会话 -->
        <el-menu-item index="new-session" @click="handleNewSession">
          <el-icon><Plus /></el-icon>
          <template #title>新建会话</template>
        </el-menu-item>

        <!-- 用户设置 -->
        <el-sub-menu index="settings">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>设置</span>
          </template>
          <div class="settings-content">
            <div class="setting-item">
              <label>主题模式</label>
              <el-button
                :icon="theme === 'light' ? Moon : Sunny"
                @click="toggleTheme"
              >
                {{ theme === 'light' ? '切换到深色' : '切换到浅色' }}
              </el-button>
            </div>
            <div class="setting-item">
              <label>用户 ID</label>
              <el-input
                v-model="userId"
                size="small"
                @change="handleUserIdChange"
                placeholder="输入用户 ID"
              />
            </div>
          </div>
        </el-sub-menu>
      </el-menu>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { useTheme } from '@/composables/useTheme'
import { filesApi } from '@/api/files'
import type { Session, UploadedFile } from '@/types'
import IconBuddy from '@/components/icons/IconBuddy.vue'
import {
  Expand,
  Fold,
  Plus,
  Close,
  ChatDotRound,
  Document,
  Setting,
  Sunny,
  Moon
} from '@element-plus/icons-vue'

const emit = defineEmits<{
  (e: 'showFileUpload'): void
  (e: 'toggleSidebar'): void
}>()

const sessionStore = useSessionStore()
const chatStore = useChatStore()
const userStore = useUserStore()
const { theme, toggleTheme } = useTheme()

const sessions = computed(() => sessionStore.sessions)
const currentSession = computed(() => sessionStore.currentSession)
const userId = computed({
  get: () => userStore.userId,
  set: (val) => userStore.setUserId(val),
})

const collapsed = computed(() => userStore.sidebarCollapsed)
const knowledgeFiles = ref<UploadedFile[]>([])
const defaultActive = ref('')

// 监听当前会话变化，更新菜单激活状态
watch(currentSession, (session) => {
  if (session) {
    defaultActive.value = `session-${session.thread_id}`
  }
}, { immediate: true })

// 加载知识库文件列表
async function loadKnowledgeFiles() {
  try {
    const response = await filesApi.list()
    knowledgeFiles.value = response.files
  } catch (error) {
    console.error('加载文件列表失败:', error)
  }
}

onMounted(() => {
  loadKnowledgeFiles()
  if (currentSession.value) {
    defaultActive.value = `session-${currentSession.value.thread_id}`
  }
})

function handleMenuSelect(index: string) {
  if (index === 'new-session') {
    return
  }
  const threadId = index.replace('session-', '')
  const session = sessions.value.find(s => s.thread_id === threadId)
  if (session) {
    handleSelectSession(session)
  }
}

function handleNewSession() {
  const threadId = sessionStore.createNewThread()
  defaultActive.value = `session-${threadId}`
  console.log('创建新会话:', threadId)
}

function handleSelectSession(session: Session) {
  sessionStore.setCurrentSession(session)
  // TODO: 加载会话历史消息
}

function handleDeleteSession(threadId: string) {
  if (confirm('确定要删除这个会话吗？')) {
    sessionStore.deleteSession(threadId)
    if (currentSession.value?.thread_id === threadId) {
      defaultActive.value = ''
    }
  }
}

async function handleDeleteFile(fileId: string) {
  if (confirm('确定要删除这个文件吗？')) {
    try {
      await filesApi.delete(fileId)
      knowledgeFiles.value = knowledgeFiles.value.filter(f => f.id !== fileId)
    } catch (error) {
      console.error('删除文件失败:', error)
      alert('删除文件失败')
    }
  }
}

function handleUserIdChange() {
  console.log('用户 ID 已更新:', userId.value)
}

function toggleCollapse() {
  userStore.toggleSidebar()
  emit('toggleSidebar')
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

function getFileStatus(status: string): { text: string, class: string } {
  switch (status) {
    case 'vectorized':
      return { text: '已向量化', class: 'status-vectorized' }
    case 'failed':
      return { text: '失败', class: 'status-failed' }
    default:
      return { text: '已上传', class: 'status-uploaded' }
  }
}

function getFileStatusTagType(status: string): '' | 'success' | 'danger' | 'info' | 'warning' {
  switch (status) {
    case 'vectorized':
      return 'success'
    case 'failed':
      return 'danger'
    default:
      return 'info'
  }
}

function getFileIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase()
  switch (ext) {
    case 'pdf': return '📕'
    case 'docx': return '📘'
    case 'txt': return '📄'
    case 'md': return '📝'
    case 'csv': return '📊'
    default: return '📄'
  }
}
</script>

<style scoped>
/* ========================================
   侧边栏容器
   ======================================== */
.sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  height: 100%;
  transition: width 0.3s ease;
  position: relative;
  z-index: 100;
}

.sidebar-collapsed {
  width: 64px !important;
}

/* ========================================
   侧边栏头部
   ======================================== */
.sidebar-header {
  padding: 16px 12px;
  border-bottom: 1px solid var(--el-border-color);
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 64px;
}

.sidebar-collapsed .sidebar-header {
  justify-content: center;
  padding: 12px 8px;
  gap: 0;
}

.logo {
  flex-shrink: 0;
  color: #667eea;
  filter: drop-shadow(0 0 10px rgba(102, 126, 234, 0.3));
}

.logo :deep(svg) {
  width: 32px;
  height: 32px;
}

.app-name {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.name {
  font-size: 18px;
  font-weight: 600;
  background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 50%, #ffd93d 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tag {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-weight: 400;
}

.collapse-toggle {
  flex-shrink: 0;
}

/* ========================================
   侧边栏内容
   ======================================== */
.sidebar-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-menu {
  border: none;
}

/* 会话标题样式 */
.session-title-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.session-icon {
  flex-shrink: 0;
  color: #667eea;
}

.session-title-wrapper span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-delete {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  padding: 0;
}

.session-meta {
  display: flex;
  justify-content: space-between;
  padding: 8px 16px 8px 48px;
  font-size: 12px;
  color: var(--el-text-color-tertiary);
}

/* 文件数量标签 */
.file-count {
  margin-left: 8px;
}

/* 文件列表 */
.files-list {
  padding: 8px 0;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  transition: background-color 0.2s;
}

.file-item:hover {
  background-color: var(--el-fill-color-light);
}

.file-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.file-name {
  flex: 1;
  font-size: 14px;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-delete {
  width: 24px;
  height: 24px;
  padding: 0;
  flex-shrink: 0;
}

/* 设置内容 */
.settings-content {
  padding: 12px 16px;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.setting-item label {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
}

/* ========================================
   Element Plus Menu 样式覆盖
   ======================================== */
:deep(.el-menu) {
  background-color: transparent;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  padding: 0 12px;
  height: 48px;
  line-height: 48px;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background-color: var(--el-fill-color-light);
}

:deep(.el-menu-item.is-active) {
  background-color: rgba(102, 126, 234, 0.1);
  color: #667eea;
}

:deep(.el-menu-item.is-active::before) {
  display: none;
}

:deep(.el-sub-menu .el-menu-item) {
  padding-left: 48px !important;
  background-color: transparent;
}

:deep(.el-sub-menu__icon-arrow) {
  color: var(--el-text-color-tertiary);
}

:deep(.el-icon) {
  font-size: 18px;
}

/* 收起状态的样式 */
.sidebar-collapsed :deep(.el-menu-item),
.sidebar-collapsed :deep(.el-sub-menu__title) {
  padding: 0 !important;
  justify-content: center;
}

.sidebar-collapsed :deep(.el-sub-menu .el-menu-item) {
  padding-left: 0 !important;
}

.sidebar-collapsed .session-title-wrapper span,
.sidebar-collapsed .session-delete,
.sidebar-collapsed .file-item,
.sidebar-collapsed .file-count,
.sidebar-collapsed .settings-content,
.sidebar-collapsed .session-meta {
  display: none;
}

.sidebar-collapsed :deep(.el-sub-menu__title) {
  display: flex;
  justify-content: center;
}

.sidebar-collapsed :deep(.el-sub-menu__icon-arrow) {
  display: none;
}

.sidebar-collapsed :deep(.el-icon) {
  margin-right: 0;
}

/* ========================================
   过渡动画
   ======================================== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ========================================
   响应式调整
   ======================================== */
@media (max-width: 640px) {
  .sidebar-header {
    padding: 12px 8px;
    min-height: 56px;
  }

  .logo :deep(svg) {
    width: 28px;
    height: 28px;
  }

  .name {
    font-size: 16px;
  }

  .tag {
    font-size: 11px;
  }
}
</style>