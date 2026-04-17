<template>
  <div class="chat-page">
    <ChatWindow :threadId="threadId" />
    <ChatInput
      v-model="inputText"
      :disabled="chatStore.isStreaming"
      :show-attach="true"
      :user-id="userStore.userId"
      placeholder="有问题，尽管问"
      @send="handleSend"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { createSSEConnection } from '@/services/sse'
import ChatWindow from '@/components/ChatWindow.vue'
import ChatInput from '@/components/ChatInput.vue'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const userStore = useUserStore()

const inputText = ref('')

const rawId = route.params.threadId
const threadId = Array.isArray(rawId) ? rawId[0] : rawId

// 校验 thread 是否存在，不存在则重定向
const isValid = !!(threadId && chatStore.threads.has(threadId))
if (!isValid) {
  router.replace('/')
}

if (isValid) {
  chatStore.switchThread(threadId)
}

function sendToSSE(content: string) {
  if (!isValid) return
  chatStore.setStreaming(true)

  const controller = createSSEConnection(
    userStore.userId,
    threadId,
    content,
    {
      onWorkflowNode(data) {
        chatStore.appendToLastAIMessage(threadId, data.content)
      },
      onFinalAnswer(data) {
        chatStore.setFinalAnswer(threadId, data.content)
      },
      onError(error) {
        chatStore.appendToLastAIMessage(threadId, '❌ ' + error)
      },
      onComplete() {
        chatStore.setStreaming(false)
      },
    },
  )

  chatStore.setActiveController(controller)
}

function handleSend(message: string) {
  chatStore.addUserMessage(threadId, message)
  sendToSSE(message)
}

onMounted(() => {
  if (!isValid) return

  if (chatStore.pendingSend) {
    chatStore.pendingSend = false

    const thread = chatStore.threads.get(threadId)
    if (thread && thread.messages.length > 0) {
      const lastUserMsg = thread.messages.findLast((m) => m.role === 'user')
      if (lastUserMsg) {
        sendToSSE(lastUserMsg.content)
      }
    }
  }
})

onUnmounted(() => {
  chatStore.cancelActiveStream()
})
</script>

<style scoped>
.chat-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
</style>
