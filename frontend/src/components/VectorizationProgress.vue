<template>
  <div v-if="show" class="vectorization-progress">
    <el-progress :percentage="progress" :status="status" />
    <div class="progress-info">
      <span>{{ statusText }}</span>
      <span v-if="totalChunks > 0" class="chunk-info">
        {{ processedChunks }} / {{ totalChunks }}
      </span>
    </div>
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { filesApi } from '@/api/files'

interface VectorizationStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  processed_chunks: number
  total_chunks: number
  error_message?: string
}

const props = defineProps<{
  fileId: string
}>()

const emit = defineEmits<{
  completed: [data: VectorizationStatus]
  failed: [error: string]
}>()

const progress = ref(0)
const status = ref<string>('pending')
const processedChunks = ref(0)
const totalChunks = ref(0)
const errorMessage = ref<string>('')
const show = ref(false)
let pollInterval: number | null = null

const statusText = computed(() => {
  const map: Record<string, string> = {
    pending: '等待中...',
    processing: '向量化中...',
    completed: '已完成',
    failed: '失败'
  }
  return map[status.value] || ''
})

const pollProgress = async () => {
  try {
    const data = await filesApi.getVectorizationProgress(props.fileId)
    progress.value = data.progress
    status.value = data.status
    processedChunks.value = data.processed_chunks
    totalChunks.value = data.total_chunks
    errorMessage.value = data.error_message || ''
    show.value = true

    if (status.value === 'completed') {
      emit('completed', data)
      stopPolling()
    } else if (status.value === 'failed') {
      emit('failed', errorMessage.value || '向量化失败')
      stopPolling()
    }
  } catch (e) {
    console.error('获取进度失败:', e)
    // 静默失败，不显示错误
  }
}

const startPolling = () => {
  pollProgress()
  pollInterval = window.setInterval(pollProgress, 1000)
}

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

onMounted(startPolling)
onUnmounted(stopPolling)
</script>

<style scoped>
.vectorization-progress {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 14px;
  color: #606266;
}

.chunk-info {
  color: #409eff;
}

.error-message {
  margin-top: 8px;
  color: #f56c6c;
  font-size: 13px;
}
</style>