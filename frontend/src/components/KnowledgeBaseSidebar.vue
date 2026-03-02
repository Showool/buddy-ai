<template>
  <div class="kb-sidebar" :class="{ 'collapsed': isCollapsed }">
    <div class="kb-header">
      <div class="kb-title" v-if="!isCollapsed">知识库</div>
      <button class="toggle-btn" @click="toggleCollapse">
        {{ isCollapsed ? '▶' : '◀' }}
      </button>
    </div>

    <div class="kb-content" v-show="!isCollapsed">
      <!-- 上传区域 -->
      <div class="upload-section">
        <button class="upload-btn" @click="triggerUpload" :disabled="uploading">
          {{ uploading ? '上传中...' : '+ 上传文件' }}
        </button>
        <input
          ref="fileInput"
          type="file"
          @change="handleFileUpload"
          accept=".pdf,.docx,.txt,.md,.csv"
          style="display: none"
        />
      </div>

      <!-- 文件列表 -->
      <div class="file-list">
        <div class="file-list-header">
          <span>我的文档 ({{ files.length }})</span>
          <button class="refresh-btn" @click="loadFiles">↻</button>
        </div>

        <div class="file-list-content">
          <div
            v-for="file in files"
            :key="file.id"
            class="file-item"
          >
            <div class="file-icon">{{ getFileIcon(file.file_type) }}</div>
            <div class="file-info">
              <div class="file-name">{{ file.filename }}</div>
              <div class="file-meta">
                <span>{{ formatFileSize(file.file_size) }}</span>
                <span class="file-date">{{ formatDate(file.upload_time) }}</span>
              </div>
            </div>
            <button class="delete-btn" @click="deleteFile(file.id)">×</button>
          </div>

          <div v-if="files.length === 0" class="empty-state">
            暂无文档，点击上传
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { filesApi } from '@/api/files'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const isCollapsed = ref(false)
const uploading = ref(false)
const fileInput = ref<HTMLInputElement>()
const files = ref<any[]>([])

const loadFiles = async () => {
  try {
    const result = await filesApi.list(userStore.userId)
    files.value = result.files || []
  } catch (error) {
    console.error('加载文件列表失败:', error)
  }
}

const triggerUpload = () => {
  fileInput.value?.click()
}

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  uploading.value = true

  try {
    await filesApi.upload(file, userStore.userId)
    await loadFiles()
  } catch (error) {
    console.error('文件上传失败:', error)
  } finally {
    uploading.value = false
    target.value = ''
  }
}

const deleteFile = async (fileId: string) => {
  if (!confirm('确定要删除这个文件吗？')) return

  try {
    await filesApi.delete(fileId, userStore.userId)
    await loadFiles()
  } catch (error) {
    console.error('删除文件失败:', error)
  }
}

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const getFileIcon = (fileType: string) => {
  const icons: Record<string, string> = {
    pdf: '📄', docx: '📝', txt: '📃', md: '📑', csv: '📊'
  }
  return icons[fileType] || '📁'
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days} 天前`
  return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadFiles()
})
</script>

<style scoped>
.kb-sidebar {
  width: 300px;
  background: #f5f7fa;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
}

.kb-sidebar.collapsed {
  width: 40px;
}

.kb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
}

.kb-title {
  font-weight: 600;
  font-size: 16px;
  color: #1f2937;
}

.toggle-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  font-size: 14px;
  color: #6b7280;
}

.toggle-btn:hover {
  color: #3b82f6;
}

.kb-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.upload-section {
  margin-bottom: 20px;
}

.upload-btn {
  width: 100%;
  padding: 10px 16px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.upload-btn:hover:not(:disabled) {
  background: #2563eb;
}

.upload-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.file-list {
  display: flex;
  flex-direction: column;
}

.file-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.refresh-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #6b7280;
  font-size: 14px;
  padding: 4px;
}

.file-list-content {
  flex: 1;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.file-item:hover {
  background: #e5e7eb;
}

.file-icon {
  font-size: 20px;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  color: #9ca3af;
  padding: 4px;
  opacity: 0;
  transition: all 0.2s;
}

.file-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: #ef4444;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #9ca3af;
  font-size: 14px;
}
</style>