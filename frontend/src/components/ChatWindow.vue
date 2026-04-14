<template>
  <div class="chat-window-scroll" ref="chatWindowRef">
    <div class="chat-window-inner">
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message-row"
        :class="msg.role"
      >
        <div
          class="message-bubble"
          :class="[msg.role, { error: msg.content.startsWith('❌') }]"
        >
          {{ msg.content }}
        </div>
      </div>

      <div v-if="showTyping" class="typing-row">
        <div class="typing-indicator">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>

      <div ref="scrollAnchorRef"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, nextTick, ref } from 'vue'
import { useChatStore } from '@/stores/chat'

const props = defineProps<{
  threadId: string
}>()

const chatStore = useChatStore()
const chatWindowRef = ref<HTMLDivElement>()
const scrollAnchorRef = ref<HTMLDivElement>()

const messages = computed(() => {
  const thread = chatStore.threads.get(props.threadId)
  return thread ? thread.messages : []
})

const showTyping = computed(() => {
  if (!chatStore.isStreaming) return false
  const msgs = messages.value
  if (msgs.length === 0) return true
  const last = msgs[msgs.length - 1]
  return last.role !== 'assistant' || !last.content
})

function scrollToBottom() {
  nextTick(() => {
    scrollAnchorRef.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

watch(
  () => messages.value.length,
  () => scrollToBottom()
)

watch(
  () => {
    const msgs = messages.value
    if (msgs.length === 0) return ''
    const last = msgs[msgs.length - 1]
    return last.content
  },
  () => scrollToBottom()
)
</script>

<style scoped>
.chat-window-scroll {
  flex: 1;
  overflow-y: auto;
  width: 100%;
}

.chat-window-inner {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-row {
  display: flex;
  width: 100%;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.typing-row {
  display: flex;
  justify-content: center;
  width: 100%;
}

.message-bubble {
  max-width: 90%;
  padding: 10px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}

.message-bubble.user {
  background-color: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  border-radius: 20px;
  padding: 14px 20px;
  font-size: 16px;
}

.message-bubble.assistant {
  background-color: transparent;
  color: var(--el-text-color-primary);
  border: none;
  border-radius: 0;
  padding: 10px 0;
}

.message-bubble.error {
  background-color: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
  border: 1px solid var(--el-color-danger-light-5);
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px 16px;
  background-color: var(--el-fill-color);
  border-radius: 12px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--el-text-color-secondary);
  animation: typing 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
  animation-delay: 0s;
}

.dot:nth-child(2) {
  animation-delay: 0.2s;
}

.dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
