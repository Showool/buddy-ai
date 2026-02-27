<template>
  <el-dialog
    v-model="dialogVisible"
    title="上传知识库文件"
    width="600px"
    @close="handleClose"
  >
    <div class="modal-body">
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :show-file-list="false"
        :accept="acceptTypes"
        :on-change="handleFileSelect"
      >
        <el-icon class="upload-icon"><Upload /></el-icon>
        <div class="upload-text">拖拽文件到此处，或点击选择文件</div>
      </el-upload>

      <div class="upload-info">
        <p>支持的文件类型: PDF, DOCX, TXT, MD, CSV</p>
        <p>最大文件大小: 5MB</p>
      </div>

      <div v-if="uploadedFiles.length > 0" class="uploaded-files">
        <h4>已上传文件</h4>
        <div class="file-list">
          <div v-for="file in uploadedFiles" :key="file.id" class="file-item">
            <span class="file-icon">📄</span>
            <span class="file-name">{{ file.filename }}</span>
            <el-tag
              size="small"
              :type="getStatusTagType(file.status)"
            >
              {{ getStatusText(file.status) }}
            </el-tag>
            <el-button
              v-if="file.status === 'uploaded'"
              type="success"
              size="small"
              @click="handleVectorize(file.id)"
            >
              向量化
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { UploadInstance, UploadUserFile } from 'element-plus'
import { filesApi } from '@/api/files'
import type { UploadedFile } from '@/types'
import { Upload } from '@element-plus/icons-vue'

interface Props {
  visible: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const uploadRef = ref<UploadInstance>()
const uploadedFiles = ref<UploadedFile[]>([])

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => {
    if (!val) emit('close')
  }
})

const acceptTypes = '.pdf,.docx,.txt,.md,.csv'

async function handleFileSelect(file: UploadUserFile) {
  const rawFile = file.raw
  if (rawFile) {
    try {
      const uploaded = await filesApi.upload(rawFile)
      uploadedFiles.value.unshift(uploaded)
      // 清空上传组件的文件列表
      uploadRef.value?.clearFiles()
    } catch (error) {
      console.error('上传文件失败:', error)
      // 使用 Element Plus 的消息提示会更好，但这里简单处理
      console.error('上传文件失败')
    }
  }
}

async function handleVectorize(fileId: string) {
  try {
    const response = await filesApi.vectorize([fileId])

    if (response.status === 'success') {
      // 更新文件状态
      const file = uploadedFiles.value.find(f => f.id === fileId)
      if (file) {
        file.status = 'vectorized'
        file.vectorized = true
      }
      console.log(`向量化成功！生成 ${response.chunk_count} 个文本块`)
    } else {
      console.error(response.message || '向量化失败')
    }
  } catch (error) {
    console.error('向量化失败:', error)
  }
}

function handleClose() {
  emit('close')
}

function getStatusText(status: string): string {
  switch (status) {
    case 'uploaded':
      return '已上传'
    case 'vectorized':
      return '已向量化'
    case 'failed':
      return '失败'
    default:
      return status
  }
}

function getStatusTagType(status: string): '' | 'success' | 'danger' | 'info' | 'warning' {
  switch (status) {
    case 'vectorized':
      return 'success'
    case 'failed':
      return 'danger'
    default:
      return 'info'
  }
}
</script>

<style scoped>
.modal-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 16px;
  color: var(--el-text-color-secondary);
}

.upload-text {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

:deep(.el-upload-dragger) {
  padding: 40px 20px;
}

.upload-info {
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.upload-info p {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 4px 0;
}

.uploaded-files h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.file-icon {
  font-size: 20px;
}

.file-name {
  flex: 1;
  font-size: 14px;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>