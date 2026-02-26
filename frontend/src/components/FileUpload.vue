<template>
  <div v-if="visible" class="file-upload-modal" @click.self="handleClose">
    <div class="modal-content">
      <div class="modal-header">
        <h3>上传知识库文件</h3>
        <button class="close-button" @click="handleClose">×</button>
      </div>

      <div class="modal-body">
        <div
          class="upload-area"
          :class="{ 'drag-over': isDragOver }"
          @dragover.prevent="isDragOver = true"
          @dragleave.prevent="isDragOver = false"
          @drop.prevent="handleDrop"
        >
          <div class="upload-icon">📁</div>
          <p>拖拽文件到此处，或点击选择文件</p>
          <input
            ref="fileInput"
            type="file"
            class="file-input"
            :accept="acceptTypes"
            @change="handleFileSelect"
          />
          <button class="select-button" @click="fileInput?.click()">
            选择文件
          </button>
        </div>

        <div class="upload-info">
          <p>支持的文件类型: PDF, DOCX, TXT, MD, CSV</p>
          <p>最大文件大小: 5MB</p>
        </div>

        <div v-if="uploadedFiles.length > 0" class="uploaded-files">
          <h4>已上传文件</h4>
          <div class="file-list">
            <div v-for="file in uploadedFiles" :key="file.id" class="file-item">
              <span class="file-name">📄 {{ file.filename }}</span>
              <span class="file-status" :class="file.status">
                {{ getStatusText(file.status) }}
              </span>
              <button
                v-if="file.status === 'uploaded'"
                class="vectorize-btn"
                @click="handleVectorize(file.id)"
              >
                向量化
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'
import type { UploadedFile } from '@/types'

interface Props {
  visible: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const isDragOver = ref(false)
const fileInput = ref<HTMLInputElement>()
const uploadedFiles = ref<UploadedFile[]>([])

const acceptTypes = '.pdf,.docx,.txt,.md,.csv'

async function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (files && files.length > 0) {
    await uploadFile(files[0])
  }
}

function handleDrop(event: DragEvent) {
  isDragOver.value = false
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    uploadFile(files[0])
  }
}

async function uploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await axios.post<UploadedFile>('/api/v1/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    uploadedFiles.value.unshift(response.data)
  } catch (error) {
    console.error('上传文件失败:', error)
    alert('上传文件失败')
  }
}

async function handleVectorize(fileId: string) {
  try {
    const response = await axios.post('/api/v1/files/vectorize', {
      file_ids: [fileId],
    })

    if (response.data.status === 'success') {
      // 更新文件状态
      const file = uploadedFiles.value.find(f => f.id === fileId)
      if (file) {
        file.status = 'vectorized'
        file.vectorized = true
      }
      alert(`向量化成功！生成 ${response.data.chunk_count} 个文本块`)
    } else {
      alert(response.data.message || '向量化失败')
    }
  } catch (error) {
    console.error('向量化失败:', error)
    alert('向量化失败')
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
</script>

<style scoped>
.file-upload-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  width: 90%;
  max-width: 600px;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  border-bottom: 1px solid #e5e5e5;
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.close-button {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: #666;
  font-size: 24px;
  cursor: pointer;
  border-radius: 4px;
}

.close-button:hover {
  background: rgba(0, 0, 0, 0.04);
}

.modal-body {
  padding: 20px;
}

.upload-area {
  border: 2px dashed #d0d0d0;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover,
.upload-area.drag-over {
  border-color: #1890ff;
  background: rgba(24, 144, 255, 0.02);
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.upload-area p {
  font-size: 14px;
  color: #666;
  margin-bottom: 16px;
}

.file-input {
  display: none;
}

.select-button {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  background: #1890ff;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.select-button:hover {
  background: #40a9ff;
}

.upload-info {
  margin-top: 16px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
}

.upload-info p {
  font-size: 12px;
  color: #666;
  margin: 4px 0;
}

.uploaded-files {
  margin-top: 24px;
}

.uploaded-files h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
}

.file-name {
  flex: 1;
  font-size: 14px;
  color: #1a1a1a;
}

.file-status {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
}

.file-status.uploaded {
  background: #e6f7ff;
  color: #1890ff;
}

.file-status.vectorized {
  background: #f6ffed;
  color: #52c41a;
}

.file-status.failed {
  background: #fff1f0;
  color: #ff4d4f;
}

.vectorize-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  background: #1890ff;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}

.vectorize-btn:hover {
  background: #40a9ff;
}
</style>