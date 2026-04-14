<template>
  <div class="message-input-wrapper">
    <div class="message-input-container">
      <div class="input-box">
        <button class="icon-btn attach-btn" @click="handleAttach" title="上传文件">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
        <input
          ref="fileInputRef"
          type="file"
          style="display: none"
          @change="handleFileChange"
        />
        <textarea
          ref="textareaRef"
          v-model="inputText"
          placeholder="有问题，尽管问"
          :disabled="chatStore.isStreaming"
          rows="1"
          @keydown="handleKeydown"
          @input="autoResize"
        />
        <button
          class="icon-btn send-btn"
          :class="{ active: canSend }"
          :disabled="!canSend"
          @click="handleSend"
          title="发送"
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
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'

const emit = defineEmits<{
  (e: 'send', message: string): void
}>()

const chatStore = useChatStore()
const userStore = useUserStore()
const inputText = ref('')
const textareaRef = ref<HTMLTextAreaElement>()
const fileInputRef = ref<HTMLInputElement>()

const canSend = computed(() => {
  return inputText.value.trim().length > 0 && !chatStore.isStreaming
})

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
  if (!userStore.userId) {
    ElMessage.warning('请先在侧边栏设置中配置 User ID')
    return
  }
  const message = inputText.value.trim()
  inputText.value = ''
  nextTick(() => autoResize())
  emit('send', message)
}

function handleAttach() {
  fileInputRef.value?.click()
}

function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    ElMessage.info(`已选择文件: ${input.files[0].name}`)
    input.value = ''
  }
}

onMounted(() => autoResize())
</script>

<style scoped>
.message-input-wrapper {
  padding: 16px 16px 28px;
  background-color: var(--el-bg-color);
  flex-shrink: 0;
}

.message-input-container {
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

.send-btn.active {
  background-color: var(--el-text-color-primary);
  color: var(--el-bg-color);
}
</style>
