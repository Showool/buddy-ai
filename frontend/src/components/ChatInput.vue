<template>
  <div class="chat-input-wrapper">
    <div class="chat-input-container">
      <div class="input-box">
        <button
          v-if="showAttach"
          class="icon-btn attach-btn"
          :disabled="disabled"
          title="上传文件（支持 .txt .docx .md）"
          @click="handleAttach"
        >
          <svg
            viewBox="0 0 24 24"
            width="20"
            height="20"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
        <input
          ref="fileInputRef"
          type="file"
          accept=".txt,.docx,.md"
          style="display: none"
          @change="handleFileChange"
        />
        <textarea
          ref="textareaRef"
          v-model="inputText"
          :placeholder="placeholder"
          :disabled="disabled"
          rows="1"
          @keydown="handleKeydown"
          @input="autoResize"
        />
        <button
          class="icon-btn send-btn"
          :disabled="!canSend"
          title="发送"
          @click="handleSend"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadFile, isFileAllowed } from '@/services/api'

interface Props {
  placeholder?: string
  disabled?: boolean
  showAttach?: boolean
  modelValue?: string
  userId?: string
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '有问题，尽管问',
  disabled: false,
  showAttach: true,
  modelValue: '',
  userId: '',
})

const emit = defineEmits<{
  send: [message: string]
  'update:modelValue': [value: string]
}>()

const inputText = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const textareaRef = ref<HTMLTextAreaElement>()
const fileInputRef = ref<HTMLInputElement>()
const uploading = ref(false)

const canSend = computed(
  () => inputText.value.trim().length > 0 && !props.disabled && !uploading.value,
)

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 150) + 'px'
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function handleSend() {
  if (!canSend.value) return
  const message = inputText.value.trim()
  inputText.value = ''
  nextTick(() => autoResize())
  emit('send', message)
}

function handleAttach() {
  if (props.disabled || uploading.value) return
  fileInputRef.value?.click()
}

async function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return

  const file = input.files[0]
  input.value = ''

  if (!props.userId) {
    ElMessage.warning('请先在侧边栏设置中配置 User ID')
    return
  }
  if (!isFileAllowed(file.name)) {
    ElMessage.error('仅支持 .txt、.docx、.md 格式的文件')
    return
  }

  uploading.value = true
  try {
    await uploadFile(file, props.userId, 1)
    ElMessage.success(`文件 ${file.name} 上传成功`)
  } catch (err) {
    const msg = err instanceof Error ? err.message : '上传失败'
    ElMessage.error(msg)
  } finally {
    uploading.value = false
  }
}

onMounted(() => autoResize())
</script>

<style scoped>
.chat-input-wrapper {
  padding: 16px 16px 28px;
  background-color: var(--el-bg-color);
  flex-shrink: 0;
}

.chat-input-container {
  max-width: 800px;
  margin: 0 auto;
}

.input-box {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--el-border-color);
  border-radius: 26px;
  padding: 8px 12px;
  background-color: var(--el-bg-color-overlay, var(--el-bg-color));
  transition: border-color 0.2s;
}

.input-box:focus-within {
  border-color: var(--el-color-primary);
}

.input-box textarea {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 15px;
  line-height: 1.5;
  resize: none;
  color: var(--el-text-color-primary);
  font-family: inherit;
  min-height: 24px;
  max-height: 150px;
  padding: 4px 0;
}

.input-box textarea::placeholder {
  color: var(--el-text-color-placeholder);
}

.input-box textarea:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
  transition: background-color 0.2s, color 0.2s;
  background: transparent;
  color: var(--el-text-color-secondary);
}

.icon-btn:hover {
  background-color: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

.icon-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.send-btn {
  background-color: var(--el-text-color-primary);
  color: var(--el-bg-color);
}

.send-btn:hover {
  opacity: 0.85;
}

.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
</style>
